import requests
import urllib.parse
from Utiles.logger import logger
from Core.GitLabHandler import GitLabHandler


class ProjectAnalyzer:
    """
    Simple project analyzer - focuses on Python and Node.js only
    """

    def __init__(self, token, project_url):
        self.gitlab = GitLabHandler(token, project_url)
        self.project_path_encoded = urllib.parse.quote_plus(urllib.parse.urlparse(project_url).path.strip('/'))
        self.api_base_url = self._get_api_base_url(project_url)

    def _get_api_base_url(self, url):
        parts = urllib.parse.urlparse(url)
        return f"{parts.scheme}://{parts.netloc}/api/v4"

    def _get_headers(self):
        return {"PRIVATE-TOKEN": self.gitlab.token, "Content-Type": "application/json"}

    def _get_default_branch(self):
        try:
            project_url = f"{self.api_base_url}/projects/{self.project_path_encoded}"
            res = requests.get(project_url, headers=self._get_headers())
            res.raise_for_status()
            project_info = res.json()
            default_branch = project_info.get('default_branch', 'main')
            logger.info(f"Default branch detected: {default_branch}")
            return default_branch
        except Exception as e:
            logger.warning(f"Could not get default branch: {e}, using 'main'")
            return 'main'

    def _get_available_branches(self):
        try:
            branches_url = f"{self.api_base_url}/projects/{self.project_path_encoded}/repository/branches"
            res = requests.get(branches_url, headers=self._get_headers())
            res.raise_for_status()
            branches = res.json()
            branch_names = [branch['name'] for branch in branches]
            logger.info(f"Available branches: {', '.join(branch_names)}")
            return branch_names
        except Exception as e:
            logger.warning(f"Could not get branches: {e}")
            return []

    def _get_primary_branch_for_analysis(self, project_data):
        """Get the primary branch to use for analysis - prefer dev/develop over default"""
        available_branches = project_data.get("available_branches", [])
        default_branch = project_data.get("default_branch", "main")

        # Priority order: dev/develop branches first, then default branch
        priority_branches = ["develop", "dev", default_branch, "main", "master"]

        for branch in priority_branches:
            if branch in available_branches:
                logger.info(f"Selected '{branch}' as primary analysis branch")
                return branch

        # Fallback to default branch even if not in available list
        logger.info(f"Falling back to default branch: {default_branch}")
        return default_branch

    def _get_analysis_files(self, project_data):
        """Get files for analysis - prioritize dev/develop branches"""
        primary_branch = self._get_primary_branch_for_analysis(project_data)

        try:
            files = self.gitlab.get_file_list(ref=primary_branch)
            logger.info(f"Got {len(files)} files from primary branch '{primary_branch}'")
            return files, primary_branch
        except Exception as e:
            logger.warning(f"Could not get files from '{primary_branch}': {e}")

            # Fallback to default branch if primary fails
            default_branch = project_data.get("default_branch", "main")
            if primary_branch != default_branch:
                try:
                    files = self.gitlab.get_file_list(ref=default_branch)
                    logger.info(f"Fallback: got {len(files)} files from '{default_branch}'")
                    return files, default_branch
                except Exception as e2:
                    logger.error(f"Fallback also failed: {e2}")

            return [], primary_branch

    def _check_for_pipeline(self, project_data):
        """Check for existing pipeline in priority order"""
        branches_to_check = ["develop", "dev", project_data.get("default_branch", "main"), "main", "master"]

        for branch in branches_to_check:
            if branch in project_data.get("available_branches", []):
                try:
                    files = self.gitlab.get_file_list(ref=branch)
                    if '.gitlab-ci.yml' in [f.lower() for f in files]:
                        logger.info(f"Found existing pipeline in branch: {branch}")
                        return True
                except Exception:
                    continue

        logger.info("No existing pipeline found")
        return False

    def _detect_language(self, files):
        """Simple language detection - Python or Node.js"""
        files_lower = [f.lower() for f in files]

        # Check for Python files
        python_indicators = [
            'app.py', 'main.py', 'server.py', 'manage.py', 'wsgi.py', 'asgi.py',
            'requirements.txt', 'setup.py', 'pyproject.toml', '__init__.py'
        ]

        # Check for Node.js files
        nodejs_indicators = [
            'package.json', 'server.js', 'app.js', 'index.js',
            'yarn.lock', 'package-lock.json'
        ]

        # Count Python files
        python_count = 0
        for indicator in python_indicators:
            if indicator in files_lower:
                python_count += 1
                logger.info(f"Found Python indicator: {indicator}")

        # Count .py files
        py_files = [f for f in files_lower if f.endswith('.py')]
        if py_files:
            python_count += len(py_files)
            logger.info(f"Found {len(py_files)} .py files")

        # Count Node.js files
        nodejs_count = 0
        for indicator in nodejs_indicators:
            if indicator in files_lower:
                nodejs_count += 1
                logger.info(f"Found Node.js indicator: {indicator}")

        # Count .js files
        js_files = [f for f in files_lower if f.endswith('.js')]
        if js_files:
            nodejs_count += len(js_files)
            logger.info(f"Found {len(js_files)} .js files")

        # Simple decision
        if python_count > nodejs_count:
            logger.info(f"Detected Python (score: {python_count} vs {nodejs_count})")
            return 'python'
        elif nodejs_count > python_count:
            logger.info(f"Detected Node.js (score: {nodejs_count} vs {python_count})")
            return 'javascript'
        elif python_count > 0:  # Tie goes to Python
            logger.info(f"Tie - choosing Python (score: {python_count})")
            return 'python'
        else:
            logger.info("No clear language detected")
            return 'unknown'

    def _detect_type(self, files, language):
        """Simple type detection - service or package"""
        files_lower = [f.lower() for f in files]

        # Service indicators (strong)
        service_indicators = [
            'dockerfile', 'docker-compose.yml', 'app.py', 'server.py',
            'server.js', 'manage.py', 'wsgi.py', 'asgi.py'
        ]

        # Package indicators (strong)
        package_indicators = [
            'setup.py', 'pyproject.toml', 'package.json'
        ]

        # Check for service indicators
        has_service_indicator = any(indicator in files_lower for indicator in service_indicators)

        # Check for package indicators
        has_package_indicator = any(indicator in files_lower for indicator in package_indicators)

        if has_service_indicator and has_package_indicator:
            # Both - prefer service if has Dockerfile
            if 'dockerfile' in files_lower:
                logger.info("Has both service and package indicators, choosing service (has Dockerfile)")
                return 'service'
            else:
                logger.info("Has both service and package indicators, choosing service (has app files)")
                return 'service'
        elif has_service_indicator:
            logger.info("Detected as service")
            return 'service'
        elif has_package_indicator:
            logger.info("Detected as package")
            return 'package'
        else:
            logger.info("No clear type indicators")
            return 'unknown'

    def analyze(self):
        """Main analysis function - prioritizes dev/develop branches"""
        project_data = {
            "name": urllib.parse.unquote(self.project_path_encoded.split('%2F')[-1]),
            "language": "unknown",
            "type": "unknown",
            "has_pipeline": False,
            "files": [],
            "default_branch": "main",
            "available_branches": [],
            "analysis_branch": "main"  # Track which branch was used for analysis
        }

        try:
            # Get basic project info
            project_data["default_branch"] = self._get_default_branch()
            project_data["available_branches"] = self._get_available_branches()

            # Check for existing pipeline (in priority order)
            project_data["has_pipeline"] = self._check_for_pipeline(project_data)

            # Get files from primary branch (dev/develop preferred)
            files, analysis_branch = self._get_analysis_files(project_data)
            project_data["files"] = files
            project_data["analysis_branch"] = analysis_branch

            # Detect language (Python or Node.js)
            detected_language = self._detect_language(files)
            project_data["language"] = detected_language

            # Detect type (service or package)
            detected_type = self._detect_type(files, detected_language)
            project_data["type"] = detected_type

            logger.info(f"Analysis complete from branch '{analysis_branch}': {detected_language}_{detected_type}")

        except Exception as e:
            logger.error(f"Analysis failed: {e}")

        return project_data