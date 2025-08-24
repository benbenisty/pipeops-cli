import requests
import urllib.parse
import time
from Utiles.logger import logger


class GitLabHandler:
    """
    Enhanced GitLab API handler for enterprise environments.
    Better branch handling and error recovery.
    """

    def __init__(self, token, project_url, timeout=30, max_retries=3):
        self.token = token
        self.project_url = project_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.api_url = self._build_api_url(project_url)
        self.headers = self._build_headers()
        self._project_info = None
        self._default_branch = None

    def _build_api_url(self, url):
        """Build API URL from project URL"""
        parts = urllib.parse.urlparse(url)
        project_path_encoded = urllib.parse.quote_plus(parts.path.strip('/'))
        return f"{parts.scheme}://{parts.netloc}/api/v4/projects/{project_path_encoded}"

    def _build_headers(self):
        """Build request headers"""
        return {
            "PRIVATE-TOKEN": self.token,
            "Content-Type": "application/json"
        }

    def _simple_retry(self, func, *args, **kwargs):
        """Simple retry logic without external dependencies"""
        last_error = None

        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = (attempt + 1) * 2  # Simple backoff: 2, 4, 6 seconds
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {self.max_retries} attempts failed")

        raise last_error

    def _make_request(self, method, url, **kwargs):
        """Make HTTP request with simple error handling"""
        kwargs.setdefault('timeout', self.timeout)
        kwargs.setdefault('headers', self.headers)

        response = requests.request(method, url, **kwargs)

        # Simple error handling
        if response.status_code >= 400:
            error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            logger.error(f"{method} {url} failed - {error_msg}")
            response.raise_for_status()

        return response

    def get_project(self):
        """Get project information with caching"""
        if self._project_info is None:
            try:
                response = self._simple_retry(self._make_request, 'GET', self.api_url)
                self._project_info = response.json()
                logger.info("Successfully retrieved project information")
            except Exception as e:
                logger.error(f"Failed to get project info: {e}")
                return None

        return self._project_info

    def get_default_branch(self):
        """Get the project's default branch"""
        if self._default_branch is None:
            project_info = self.get_project()
            if project_info:
                self._default_branch = project_info.get('default_branch', 'main')
                logger.info(f"Default branch: {self._default_branch}")
            else:
                self._default_branch = 'main'
                logger.warning("Could not determine default branch, using 'main'")

        return self._default_branch

    def get_available_branches(self):
        """Get list of available branches"""
        url = f"{self.api_url}/repository/branches"

        try:
            response = self._simple_retry(self._make_request, 'GET', url)
            branches_data = response.json()
            branches = [branch['name'] for branch in branches_data]
            logger.info(f"Found {len(branches)} branches: {', '.join(branches[:5])}")
            if len(branches) > 5:
                logger.info(f"... and {len(branches) - 5} more")
            return branches
        except Exception as e:
            logger.error(f"Failed to get branches: {e}")
            return [self.get_default_branch()]  # Return at least the default branch

    def get_file_list(self, ref=None):
        """Get list of files in project with smart branch fallback"""
        if ref is None:
            ref = self.get_default_branch()

        url = f"{self.api_url}/repository/tree"
        params = {'ref': ref, 'recursive': 'true', 'per_page': 100}

        try:
            response = self._simple_retry(self._make_request, 'GET', url, params=params)
            files = [file['path'] for file in response.json() if file['type'] == 'blob']
            logger.info(f"Retrieved {len(files)} files from branch '{ref}'")
            return files
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                # Branch doesn't exist, try default branch if we weren't already using it
                default_branch = self.get_default_branch()
                if ref != default_branch:
                    logger.warning(f"Branch '{ref}' not found, trying '{default_branch}'")
                    return self.get_file_list(ref=default_branch)
                else:
                    # Even default branch failed - try common branch names
                    common_branches = ['main', 'master', 'develop']
                    available_branches = self.get_available_branches()

                    for branch in common_branches:
                        if branch in available_branches and branch != ref:
                            logger.warning(f"Trying branch '{branch}'")
                            try:
                                params['ref'] = branch
                                response = self._simple_retry(self._make_request, 'GET', url, params=params)
                                files = [file['path'] for file in response.json() if file['type'] == 'blob']
                                logger.info(f"Retrieved {len(files)} files from branch '{branch}'")
                                return files
                            except:
                                continue

                    logger.error(f"Could not retrieve files from any branch")
                    return []
            else:
                logger.error(f"Failed to get file list: {e}")
                return []
        except Exception as e:
            logger.error(f"Failed to get file list: {e}")
            return []

    def branch_exists(self, branch_name):
        """Check if branch exists"""
        try:
            url = f"{self.api_url}/repository/branches/{urllib.parse.quote(branch_name, safe='')}"
            response = self._simple_retry(self._make_request, 'GET', url)
            logger.info(f"Branch '{branch_name}' exists")
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.info(f"Branch '{branch_name}' does not exist")
                return False
            else:
                logger.error(f"Error checking branch '{branch_name}': {e}")
                return False
        except Exception as e:
            logger.error(f"Error checking branch '{branch_name}': {e}")
            return False

    def delete_branch(self, branch_name):
        """Delete a branch"""
        try:
            url = f"{self.api_url}/repository/branches/{urllib.parse.quote(branch_name, safe='')}"
            response = self._simple_retry(self._make_request, 'DELETE', url)
            logger.info(f"Branch '{branch_name}' deleted successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to delete branch '{branch_name}': {e}")
            return False

    def get_branch_info(self, branch_name):
        """Get detailed information about a branch"""
        try:
            url = f"{self.api_url}/repository/branches/{urllib.parse.quote(branch_name, safe='')}"
            response = self._simple_retry(self._make_request, 'GET', url)
            branch_info = response.json()
            logger.info(f"Retrieved info for branch '{branch_name}'")
            return branch_info
        except Exception as e:
            logger.error(f"Failed to get branch info for '{branch_name}': {e}")
            return None

    def create_branch(self, branch_name, ref=None):
        """Create new branch with existence check and user confirmation"""
        if ref is None:
            ref = self.get_default_branch()

        # Check if branch already exists
        if self.branch_exists(branch_name):
            logger.warning(f"Branch '{branch_name}' already exists")

            # Get branch info to show to user
            branch_info = self.get_branch_info(branch_name)
            if branch_info:
                last_commit = branch_info.get('commit', {})
                commit_message = last_commit.get('message', 'Unknown')[:50]
                commit_date = last_commit.get('created_at', 'Unknown')

                print(f"\n⚠️  Branch '{branch_name}' already exists!")
                print(f"   Last commit: {commit_message}")
                print(f"   Date: {commit_date}")
                print("\nThis might contain previous PipeOps changes.")
                print("Options:")
                print("  1. Delete existing branch and create fresh (recommended)")
                print("  2. Stop and do nothing")

                while True:
                    choice = input("\nWhat would you like to do? [1/2]: ").strip()

                    if choice == '1' or choice == '':
                        print("🗑️  Deleting existing branch...")
                        if self.delete_branch(branch_name):
                            print("✅ Branch deleted successfully")
                            break
                        else:
                            print("❌ Failed to delete branch")
                            return False
                    elif choice == '2':
                        print("⏹️  Operation cancelled")
                        return False
                    else:
                        print("Please choose 1 or 2")
            else:
                # Couldn't get branch info, ask user what to do
                print(f"\n⚠️  Branch '{branch_name}' already exists!")
                confirm = input("Delete it and create fresh? [y/N]: ").strip().lower()
                if confirm in ['y', 'yes']:
                    if not self.delete_branch(branch_name):
                        print("❌ Failed to delete existing branch")
                        return False
                else:
                    print("⏹️  Operation cancelled")
                    return False

        # Now create the branch
        url = f"{self.api_url}/repository/branches"
        payload = {"branch": branch_name, "ref": ref}

        try:
            response = self._simple_retry(self._make_request, 'POST', url, json=payload)
            logger.info(f"Branch '{branch_name}' created successfully from '{ref}'")
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:  # Bad reference
                # Try with default branch if we weren't using it
                default_branch = self.get_default_branch()
                if ref != default_branch:
                    logger.warning(f"Reference '{ref}' invalid, trying '{default_branch}'")
                    return self.create_branch(branch_name, ref=default_branch)

            logger.error(f"Failed to create branch '{branch_name}': {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to create branch '{branch_name}': {e}")
            return False

    def commit_files(self, branch_name, commit_message, actions):
        """Commit files to branch"""
        url = f"{self.api_url}/repository/commits"
        payload = {
            "branch": branch_name,
            "commit_message": commit_message,
            "actions": actions
        }

        try:
            response = self._simple_retry(self._make_request, 'POST', url, json=payload)
            commit_data = response.json()
            logger.info(f"Commit '{commit_message}' succeeded. SHA: {commit_data.get('id', 'unknown')}")
            return commit_data
        except Exception as e:
            logger.error(f"Failed to commit files: {e}")
            return None

    def create_merge_request(self, title, source_branch, target_branch=None, description=None):
        """Create merge request with smart target branch handling and conflict resolution"""
        if target_branch is None:
            # Get available branches to make smart decision
            available_branches = self.get_available_branches()
            default_branch = self.get_default_branch()

            # Priority order: dev/develop branches first, then default branch
            preferred_targets = ["develop", "dev", default_branch]

            target_branch = None
            for preferred in preferred_targets:
                if preferred in available_branches:
                    target_branch = preferred
                    break

            # Final fallback
            if target_branch is None:
                target_branch = default_branch

            logger.info(f"Auto-selected target branch: {target_branch}")

        url = f"{self.api_url}/merge_requests"
        payload = {
            "source_branch": source_branch,
            "target_branch": target_branch,
            "title": title,
            "remove_source_branch": True
        }

        if description:
            payload["description"] = description

        try:
            response = self._simple_retry(self._make_request, 'POST', url, json=payload)
            mr_data = response.json()
            mr_url = mr_data.get('web_url', 'unknown')
            logger.info(f"Merge Request created successfully: {mr_url}")
            logger.info(f"MR: {source_branch} → {target_branch}")
            return mr_data
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 409:
                # Handle existing MR conflict
                logger.warning(f"MR conflict detected - checking existing MRs for branch: {source_branch}")
                existing_mr = self._find_existing_mr(source_branch)
                if existing_mr:
                    logger.info(f"Found existing MR: {existing_mr.get('web_url')}")
                    print(f"ℹ️  Using existing Merge Request: {existing_mr.get('web_url')}")
                    return existing_mr
                else:
                    logger.error(f"409 conflict but no existing MR found for {source_branch}")
                    raise
            else:
                logger.error(f"Failed to create Merge Request: {e}")
                raise
        except Exception as e:
            logger.error(f"Failed to create Merge Request: {e}")
            return None

    def _find_existing_mr(self, source_branch):
        """Find existing merge request for source branch"""
        try:
            url = f"{self.api_url}/merge_requests"
            params = {
                "source_branch": source_branch,
                "state": "opened",
                "per_page": 1
            }

            response = self._simple_retry(self._make_request, 'GET', url, params=params)
            mrs = response.json()

            if mrs:
                mr = mrs[0]
                logger.info(f"Found existing MR #{mr.get('iid')} for branch {source_branch}")
                return mr
            else:
                logger.warning(f"No existing MR found for branch {source_branch}")
                return None

        except Exception as e:
            logger.error(f"Error finding existing MR: {e}")
            return None

    def get_latest_pipeline_status(self, ref=None):
        """Get status of latest pipeline"""
        if ref is None:
            ref = self.get_default_branch()

        url = f"{self.api_url}/pipelines"
        params = {"ref": ref, "per_page": 1, "order_by": "id", "sort": "desc"}

        try:
            response = self._simple_retry(self._make_request, 'GET', url, params=params)
            pipelines = response.json()
            if pipelines:
                status = pipelines[0]['status']
                logger.info(f"Latest pipeline status for '{ref}': {status}")
                return status
            else:
                logger.warning(f"No pipelines found for branch '{ref}'")
                return 'unknown'
        except Exception as e:
            logger.error(f"Failed to get pipeline status: {e}")
            return 'unknown'

    def get_latest_pipeline_with_id(self, ref='main'):
        """Get latest pipeline with full details including ID"""
        url = f"{self.api_url}/pipelines"
        params = {"ref": ref, "per_page": 1, "order_by": "id", "sort": "desc"}

        try:
            response = self._simple_retry(self._make_request, 'GET', url, params=params)
            pipelines = response.json()
            if pipelines:
                pipeline = pipelines[0]
                logger.info(f"Latest pipeline for '{ref}': ID={pipeline['id']}, status={pipeline['status']}")
                return pipeline
            else:
                logger.warning(f"No pipelines found for branch '{ref}'")
                return None
        except Exception as e:
            logger.error(f"Failed to get pipeline details: {e}")
            return None

    def trigger_pipeline(self, ref='main', variables=None):
        """Trigger a pipeline manually"""
        url = f"{self.api_url}/pipeline"
        payload = {"ref": ref}

        if variables:
            payload["variables"] = variables

        try:
            response = self._simple_retry(self._make_request, 'POST', url, json=payload)
            pipeline_data = response.json()
            pipeline_id = pipeline_data.get('id')
            logger.info(f"Pipeline triggered successfully: ID={pipeline_id}")
            return pipeline_data
        except Exception as e:
            logger.error(f"Failed to trigger pipeline: {e}")
            return None

    def get_pipeline_by_id(self, pipeline_id):
        """Get specific pipeline information"""
        url = f"{self.api_url}/pipelines/{pipeline_id}"

        try:
            response = self._simple_retry(self._make_request, 'GET', url)
            pipeline_data = response.json()
            logger.info(f"Retrieved pipeline {pipeline_id} info")
            return pipeline_data
        except Exception as e:
            logger.error(f"Failed to get pipeline {pipeline_id}: {e}")
            return None

    def get_pipeline_jobs(self, pipeline_id):
        """Get jobs for a specific pipeline"""
        url = f"{self.api_url}/pipelines/{pipeline_id}/jobs"

        try:
            response = self._simple_retry(self._make_request, 'GET', url)
            jobs = response.json()
            logger.info(f"Retrieved {len(jobs)} jobs for pipeline {pipeline_id}")
            return jobs
        except Exception as e:
            logger.error(f"Failed to get pipeline jobs: {e}")
            return []

    def retry_job(self, job_id):
        """Retry a failed job"""
        url = f"{self.api_url}/jobs/{job_id}/retry"

        try:
            response = self._simple_retry(self._make_request, 'POST', url)
            logger.info(f"Job {job_id} retried successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to retry job {job_id}: {e}")
            return False