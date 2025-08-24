from typing import Dict, List, Any
from Utiles.logger import logger


class UserInteractor:
    """
    Simple user interaction class for DevOps teams.
    No external dependencies - just basic console input/output with better UX.
    """

    def __init__(self):
        pass

    def display_project_analysis(self, project_data: Dict[str, Any]) -> None:
        """Display concise project analysis results"""
        print("\n" + "=" * 50)
        print("        PROJECT ANALYSIS")
        print("=" * 50)
        print(f"📁 Project:     {project_data.get('name', 'Unknown')}")
        print(f"🔤 Language:    {project_data.get('language', 'Unknown')}")
        print(f"📦 Type:        {project_data.get('type', 'Unknown')}")

        # Show analyzed branch if different from default
        analysis_branch = project_data.get('analysis_branch')
        default_branch = project_data.get('default_branch')
        if analysis_branch and analysis_branch != default_branch:
            print(f"🔍 Branch:      {analysis_branch} (dev branch used)")

        # Pipeline status
        has_pipeline = project_data.get('has_pipeline', False)
        print(f"🚀 Pipeline:    {'✅ Exists' if has_pipeline else '❌ Missing'}")

        # Show key files found
        files = project_data.get('files', [])
        key_files = self._identify_key_files(files)

        important_files = []
        if key_files['service']:
            important_files.extend(key_files['service'][:2])
        if key_files['config']:
            important_files.extend(key_files['config'][:2])

        if important_files:
            print(f"📄 Key files:   {', '.join(important_files[:4])}")

        print("=" * 50)

    def _identify_key_files(self, files: List[str]) -> Dict[str, List[str]]:
        """Categorize files into different types"""
        key_files = {
            'service': [],
            'package': [],
            'config': [],
            'other': []
        }

        service_patterns = ['app.py', 'main.py', 'server.py', 'api.py', 'wsgi.py', 'asgi.py',
                            'server.js', 'app.js', 'index.js', 'manage.py']
        package_patterns = ['setup.py', 'pyproject.toml', 'package.json', 'pom.xml',
                            'build.gradle', 'cargo.toml', '__init__.py']
        config_patterns = ['dockerfile', 'docker-compose.yml', 'requirements.txt',
                           '.gitlab-ci.yml', 'makefile', 'webpack.config.js']

        for file in files:
            file_lower = file.lower()
            categorized = False

            for pattern in service_patterns:
                if pattern in file_lower:
                    key_files['service'].append(file)
                    categorized = True
                    break

            if not categorized:
                for pattern in package_patterns:
                    if pattern in file_lower:
                        key_files['package'].append(file)
                        categorized = True
                        break

            if not categorized:
                for pattern in config_patterns:
                    if pattern in file_lower:
                        key_files['config'].append(file)
                        break

        return key_files

    def _calculate_analysis_confidence(self, project_data: Dict[str, Any]) -> int:
        """Calculate confidence level of the analysis"""
        confidence = 50  # Base confidence

        # Language detection confidence
        if project_data.get('language', 'unknown') != 'unknown':
            confidence += 20

        # Type detection confidence
        if project_data.get('type', 'unknown') != 'unknown':
            confidence += 20

        # File count (more files = more confidence)
        file_count = len(project_data.get('files', []))
        if file_count > 20:
            confidence += 10
        elif file_count > 5:
            confidence += 5

        # Specific indicators boost confidence
        files = project_data.get('files', [])
        files_lower = [f.lower() for f in files]

        strong_indicators = ['dockerfile', 'app.py', 'setup.py', 'package.json', 'pom.xml']
        for indicator in strong_indicators:
            if any(indicator in f for f in files_lower):
                confidence += 5

        return min(confidence, 100)

    def confirm_or_edit(self, project_data: Dict[str, Any], available_types: List[str] = None) -> Dict[str, Any]:
        """Simple confirmation with 3 clear options"""

        self.display_project_analysis(project_data)

        # Show warning if pipeline already exists
        if project_data.get('has_pipeline', False):
            print("\n⚠️  This project already has a pipeline - will be updated")

        # Show what will be created
        pipeline_type = f"{project_data['language']}_{project_data['type']}"
        print(f"\n🎯 Will create: {pipeline_type.replace('_', ' → ').title()}")

        # Simple 3 options
        print("\nWhat would you like to do?")
        print("  1️⃣  Continue with these settings")
        print("  2️⃣  Edit settings")
        print("  3️⃣  Exit")

        while True:
            choice = input("\nChoice [1]: ").strip() or "1"

            if choice in ['1', '']:
                print("✅ Proceeding with detected settings")
                break
            elif choice == '2':
                project_data = self._simple_edit(project_data, available_types)
                break
            elif choice == '3':
                print("👋 Goodbye!")
                exit(0)
            else:
                print("❌ Please choose 1, 2, or 3")

        # Validate and set final pipeline type
        original_language = project_data['language']
        original_type = project_data['type']
        pipeline_type = f"{original_language}_{original_type}"

        # Quick validation
        if available_types and pipeline_type not in available_types:
            print(f"\n⚠️  '{pipeline_type}' not available. Available options:")
            for i, ptype in enumerate(available_types, 1):
                clean_name = ptype.replace('_', ' → ').title()
                print(f"  {i}. {clean_name}")

            while True:
                try:
                    choice = input(f"\nChoose (1-{len(available_types)}): ").strip()
                    index = int(choice) - 1
                    if 0 <= index < len(available_types):
                        pipeline_type = available_types[index]
                        break
                    else:
                        print(f"Please choose 1-{len(available_types)}")
                except ValueError:
                    print("Please enter a number")

        project_data['type'] = pipeline_type

        print(f"\n🚀 Final selection: {pipeline_type.replace('_', ' → ').title()}")
        return project_data

    def _simple_edit(self, project_data: Dict[str, Any], available_types: List[str] = None) -> Dict[str, Any]:
        """Simple editing interface"""
        print("\n" + "=" * 30)
        print("     EDIT SETTINGS")
        print("=" * 30)

        # Edit language
        current_language = project_data.get('language', 'unknown')
        print(f"Current language: {current_language}")
        new_language = input("New language (python/javascript) or Enter to keep: ").strip().lower()
        if new_language and new_language in ['python', 'javascript', 'js', 'node']:
            if new_language in ['js', 'node']:
                new_language = 'javascript'
            project_data['language'] = new_language
            print(f"✅ Language: {new_language}")

        # Edit type
        current_type = project_data.get('type', 'unknown')
        print(f"\nCurrent type: {current_type}")
        new_type = input("New type (service/package) or Enter to keep: ").strip().lower()
        if new_type and new_type in ['service', 'package']:
            project_data['type'] = new_type
            print(f"✅ Type: {new_type}")

        return project_data

    def ask_for_env_vars(self, missing_vars: List[str]) -> Dict[str, str]:
        """Ask user for missing environment variables with better guidance"""
        if not missing_vars:
            print("✅ All required environment variables are present.")
            return {}

        print("\n" + "=" * 60)
        print("       MISSING ENVIRONMENT VARIABLES")
        print("=" * 60)
        print("The following variables are required for this pipeline:")
        for i, var in enumerate(missing_vars, 1):
            hint = self._get_var_hint(var)
            if hint:
                print(f"  {i}. {var}")
                print(f"     💡 {hint}")
            else:
                print(f"  {i}. {var}")
        print("=" * 60)

        print("\n🔧 You can set these variables in GitLab:")
        print("   Project Settings → CI/CD → Variables")
        print("   Or Group Settings → CI/CD → Variables (for multiple projects)")

        vars_dict = {}

        skip_all = False
        if len(missing_vars) > 2:
            skip_choice = input(f"\nWould you like to skip adding variables now? [y/N]: ").strip().lower()
            if skip_choice in ['y', 'yes']:
                print("⏭️  Skipping variable setup - you can add them manually later")
                return {}

        for i, var in enumerate(missing_vars, 1):
            print(f"\n📝 Variable {i}/{len(missing_vars)}: {var}")

            # Provide hints for common variables
            hint = self._get_var_hint(var)
            if hint:
                print(f"💡 {hint}")

            # Handle sensitive variables
            is_sensitive = any(keyword in var.lower() for keyword in ['token', 'password', 'secret', 'key'])

            # Option to skip this variable
            if is_sensitive:
                print("⚠️  This looks like a sensitive value")
                skip = input("Skip this variable for now? [y/N]: ").strip().lower()
                if skip in ['y', 'yes']:
                    print(f"⏭️  Skipped {var}")
                    continue

            while True:
                value = input(f"Enter value for '{var}' (or 'skip' to skip): ").strip()

                if value.lower() == 'skip':
                    print(f"⏭️  Skipped {var}")
                    break
                elif value:
                    vars_dict[var] = value
                    print(f"✅ {var} configured")
                    break
                else:
                    print("❌ Value cannot be empty. Please try again or type 'skip'.")

        if vars_dict:
            print(f"\n✅ Successfully configured {len(vars_dict)} environment variables.")
        else:
            print(f"\n⏭️  No variables configured - you can add them manually in GitLab later.")

        return vars_dict

    def _get_var_hint(self, var_name: str) -> str:
        """Get helpful hints for environment variables"""
        hints = {
            'CI_REGISTRY_URL': 'GitLab Container Registry URL (e.g., registry.gitlab.com)',
            'GITHUB_TOKEN': 'GitHub Personal Access Token for accessing repositories',
            'PYPI_TOKEN': 'PyPI API token for publishing Python packages',
            'DOCKER_REGISTRY': 'Docker registry URL (e.g., docker-registry.company.com)',
            'OPENSHIFT_SERVER': 'OpenShift cluster API server URL (e.g., https://api.openshift.company.com)',
            'OPENSHIFT_TOKEN': 'OpenShift authentication token (oc whoami -t)',
            'NPM_TOKEN': 'npm registry authentication token for publishing packages',
            'TWINE_USERNAME': 'Username for PyPI (usually __token__)',
            'TWINE_PASSWORD': 'PyPI token (same as PYPI_TOKEN)'
        }
        return hints.get(var_name, '')

    def display_success_message(self, mr_url: str = None, branch_name: str = None, result: dict = None):
        """Display concise success message"""
        print("\n🎉 SUCCESS!")
        print("=" * 30)

        if result:
            source_branch = result.get('source_branch')
            target_branch = result.get('target_branch')

            print(f"🔀 {source_branch} → {branch_name} → {target_branch}")

        if mr_url:
            print(f"🔗 MR: {mr_url}")

        print("✅ Pipeline setup complete!")
        print("💡 Merge the MR to activate")
        print("=" * 30)

    def display_error(self, error_message: str, details: str = None):
        """Display enhanced error message"""
        print("\n" + "❌" * 20)
        print("           ERROR")
        print("❌" * 20)
        print(f"💥 {error_message}")

        if details:
            print(f"\n🔍 Details: {details}")

        print(f"\n💡 Troubleshooting tips:")
        print("  • Check your GitLab token permissions")
        print("  • Verify the project URL is correct")
        print("  • Ensure you have access to the project")

        print("❌" * 20)

    # NEW METHODS - Added for failure display
    def display_enhanced_failure_details(self, failure_analysis: dict, recovery_actions: list):
        """Display enhanced failure details in a user-friendly format"""

        print("\n" + "=" * 60)
        print("           DETAILED FAILURE ANALYSIS")
        print("=" * 60)

        # Severity and overview
        severity = failure_analysis.get('severity', 'unknown')
        failed_stages = failure_analysis.get('failed_stages', [])
        total_jobs = failure_analysis.get('total_jobs', 0)
        failed_jobs = failure_analysis.get('failed_jobs', [])

        print(f"🚨 Severity Level: {severity.upper()}")
        print(f"📊 Overview: {len(failed_jobs)}/{total_jobs} jobs failed")
        print(f"🎯 Failed Stages: {', '.join(failed_stages) if failed_stages else 'None'}")

        # Critical failures
        critical_failures = failure_analysis.get('critical_failures', [])
        if critical_failures:
            print(f"\n💥 Critical Failures:")
            for failure in critical_failures:
                job_name = failure.get('job_name', 'unknown')
                stage = failure.get('stage', 'unknown')
                failure_type = failure.get('type', 'unknown')
                icon = "🚚" if failure_type == "deploy" else "⚠️"
                print(f"   {icon} {job_name} ({stage} stage)")

        # Stage summary
        stage_summary = failure_analysis.get('stage_summary', {})
        if stage_summary:
            print(f"\n📈 Stage Breakdown:")
            for stage, stats in stage_summary.items():
                total = stats.get('total', 0)
                failed = stats.get('failed', 0)
                success = stats.get('success', 0)

                if failed > 0:
                    status_icon = "❌"
                    status_text = f"{failed} failed, {success} passed"
                else:
                    status_icon = "✅"
                    status_text = f"All {success} jobs passed"

                print(f"   {status_icon} {stage}: {status_text}")

        print("=" * 60)

    def display_basic_failure_details(self, failed_jobs: list):
        """Display basic failure details for non-deploy failures"""

        print("\n" + "=" * 50)
        print("           PIPELINE FAILURE DETAILS")
        print("=" * 50)

        print(f"💥 {len(failed_jobs)} job(s) failed:")

        for job in failed_jobs:
            job_name = job.get('name', 'unknown')
            job_stage = job.get('stage', 'unknown')
            job_id = job.get('id', 'unknown')
            web_url = job.get('web_url', '')

            stage_icon = {
                'build': '🔨',
                'test': '🧪',
                'deploy': '🚚',
                'release': '📦'
            }.get(job_stage, '⚠️')

            print(f"\n   {stage_icon} {job_name}")
            print(f"      Stage: {job_stage}")
            print(f"      Job ID: {job_id}")
            if web_url:
                print(f"      URL: {web_url}")

        print("=" * 50)

    def confirm_branch_replacement(self, branch_name: str, branch_info: dict = None) -> bool:
        """
        Ask user about replacing existing branch
        :param branch_name: Name of the existing branch
        :param branch_info: Branch information from GitLab API
        :return: True if user wants to replace, False otherwise
        """
        print(f"\n⚠️  Branch '{branch_name}' already exists!")
        print("=" * 50)

        if branch_info:
            last_commit = branch_info.get('commit', {})
            commit_message = last_commit.get('message', 'Unknown')[:60]
            commit_author = last_commit.get('author_name', 'Unknown')
            commit_date = last_commit.get('created_at', 'Unknown')

            if commit_date != 'Unknown':
                # Try to format the date nicely
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(commit_date.replace('Z', '+00:00'))
                    commit_date = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    pass  # Keep original format if parsing fails

            print(f"📝 Last commit: {commit_message}")
            print(f"👤 Author: {commit_author}")
            print(f"📅 Date: {commit_date}")

            # Check if it looks like a PipeOps commit
            if 'pipeops' in commit_message.lower() or 'pipeline' in commit_message.lower():
                print("🤖 This looks like a previous PipeOps run")
        else:
            print("📝 Could not retrieve branch details")

        print("=" * 50)
        print("This branch might contain previous pipeline setup attempts.")
        print("\n🤔 What would you like to do?")
        print("  1. 🗑️  Delete existing branch and create fresh (recommended)")
        print("  2. ⏹️  Stop and exit - don't make any changes")
        print("  3. 📋 Show more details about the branch")

        while True:
            choice = input("\nChoice [1]: ").strip() or "1"

            if choice == '1':
                print("\n✅ Will delete existing branch and create fresh")
                return True
            elif choice == '2':
                print("\n⏹️  Operation cancelled - no changes made")
                return False
            elif choice == '3':
                self._show_branch_details(branch_name, branch_info)
                print("\n🤔 What would you like to do?")
                print("  1. 🗑️  Delete existing branch and create fresh")
                print("  2. ⏹️  Stop and exit")
                continue
            else:
                print("❌ Please choose 1, 2, or 3")

    def _show_branch_details(self, branch_name: str, branch_info: dict):
        """Show detailed information about a branch"""
        print(f"\n🔍 Detailed information for branch '{branch_name}':")
        print("-" * 50)

        if not branch_info:
            print("❌ No branch information available")
            return

        # Branch basic info
        print(f"🌿 Branch name: {branch_info.get('name', 'Unknown')}")
        print(f"🔒 Protected: {'Yes' if branch_info.get('protected', False) else 'No'}")
        print(f"🔀 Can push: {'Yes' if branch_info.get('can_push', False) else 'No'}")

        # Commit information
        commit = branch_info.get('commit', {})
        if commit:
            print(f"\n📝 Last commit:")
            print(f"   ID: {commit.get('id', 'Unknown')[:12]}")
            print(f"   Message: {commit.get('message', 'Unknown')[:80]}")
            print(f"   Author: {commit.get('author_name', 'Unknown')} <{commit.get('author_email', '')}>")
            print(f"   Date: {commit.get('created_at', 'Unknown')}")

        print("-" * 50)

    def confirm_action(self, message: str, default: bool = True) -> bool:
        """Ask user to confirm an action with better formatting"""
        default_text = "Y/n" if default else "y/N"
        response = input(f"🤔 {message} [{default_text}]: ").strip().lower()

        if not response:
            return default

        return response in ['y', 'yes']

    def show_file_preview(self, files_to_create: List[str], template_path: str):
        """Show preview of files that will be created"""
        print(f"\n📁 Files that will be created from template '{template_path}':")
        for file_name in files_to_create:
            print(f"  ✨ {file_name}")
        print()