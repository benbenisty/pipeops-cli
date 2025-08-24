import datetime
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from Core.GitLabHandler import GitLabHandler
from Utiles.logger import logger


class PipelineGenerator:
    """
    Simple pipeline generator for DevOps teams.
    Creates pipeline files from templates and commits them to GitLab.
    """

    def __init__(self, token: str, project_url: str):
        self.gitlab = GitLabHandler(token, project_url)

    def _render_template(self, template_str: str, context: Dict[str, Any]) -> str:
        """
        Simple template rendering - replace {{variable}} with values
        """
        rendered_str = template_str

        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in rendered_str:
                rendered_str = rendered_str.replace(placeholder, str(value))
                #logger.debug(f"Replaced {placeholder} with {value}")

        return rendered_str

    def _load_template_file(self, template_path: str) -> str:
        """
        Load template file content
        """
        template_file = Path(template_path)

        if not template_file.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")

        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()

            #logger.info(f"Loaded template: {template_path}")
            return content

        except Exception as e:
            #logger.error(f"Failed to read template {template_path}: {e}")
            raise

    def _prepare_context(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare variables for template rendering
        """
        context = {
            "creation_date": datetime.date.today().strftime("%Y-%m-%d"),
            "creation_year": datetime.date.today().year,
            "project_name": project_data.get('name', 'unknown'),
            "language": project_data.get('language', 'unknown'),
            "pipeline_type": project_data.get('type', 'unknown')
        }

        # Split pipeline type back to components for compatibility
        if '_' in context["pipeline_type"]:
            parts = context["pipeline_type"].split('_')
            context["original_language"] = parts[0]
            context["original_type"] = parts[1]

        return context

    def _check_file_exists_in_branch(self, branch_name: str, file_path: str) -> bool:
        """
        Check if a file exists in the specified branch
        """
        try:
            files_in_branch = self.gitlab.get_file_list(ref=branch_name)
            exists = file_path in files_in_branch
            #logger.debug(f"File '{file_path}' {'exists' if exists else 'does not exist'} in branch '{branch_name}'")
            return exists
        except Exception as e:
            ##logger.warning(f"Could not check file existence in branch '{branch_name}': {e}")
            return False

    def _create_pipeline_files(self, project_data: Dict[str, Any], config: Dict[str, Any], source_branch: str) -> List[
        Dict[str, Any]]:
        """
        Create list of files to commit - uses correct action type based on file existence in source branch
        """
        pipeline_type = project_data['type']

        if pipeline_type not in config['pipelines']:
            raise ValueError(f"Pipeline type '{pipeline_type}' not found in configuration")

        pipeline_config = config['pipelines'][pipeline_type]
        template_path = Path(pipeline_config['template_path'])
        files_to_create = pipeline_config['files_to_create']

        # Prepare rendering context
        context = self._prepare_context(project_data)

        actions = []

        for file_name in files_to_create:
            template_file_path = template_path / file_name

            try:
                # Load and render template
                template_content = self._load_template_file(str(template_file_path))
                file_content = self._render_template(template_content, context)

                # Check if file exists in source branch to determine action
                file_exists = self._check_file_exists_in_branch(source_branch, file_name)
                action_type = "update" if file_exists else "create"

                actions.append({
                    "action": action_type,
                    "file_path": file_name,
                    "content": file_content
                })

                #logger.info(f"Prepared {action_type} action for: {file_name}")

            except Exception as e:
                #logger.error(f"Failed to process template {file_name}: {e}")
                raise

        return actions

    def _get_branch_names(self, config: Dict[str, Any]) -> Dict[str, str]:
        """
        Get branch names from Config or use defaults
        """
        global_config = config.get('global', {})
        branch_config = global_config.get('default_branches', {})

        return {
            'source': branch_config.get('source', 'main'),
            'target': branch_config.get('target', 'dev'),
            'feature': branch_config.get('feature_prefix', 'feature/pipeops')
        }

    def _get_best_target_branch(self, project_data: Dict[str, Any]) -> str:
        """
        Get the best target branch for the MR based on what was analyzed
        """
        available_branches = project_data.get("available_branches", [])
        analysis_branch = project_data.get("analysis_branch")
        default_branch = project_data.get("default_branch", "main")

        # If we analyzed develop/dev, target should be develop/dev
        if analysis_branch in ["develop", "dev"]:
            #logger.info(f"Using analysis branch as MR target: {analysis_branch}")
            return analysis_branch

        # Otherwise, prefer develop/dev if they exist
        priority_targets = ["develop", "dev", default_branch]

        for target in priority_targets:
            if target in available_branches:
                #logger.info(f"Selected MR target branch: {target}")
                return target

        # Final fallback
        #logger.info(f"Falling back to default branch as target: {default_branch}")
        return default_branch

    def _get_best_source_branch(self, project_data: Dict[str, Any], config: Dict[str, Any]) -> str:
        """
        Get the best source branch - prefer dev/develop if they exist, otherwise use default
        """
        available_branches = project_data.get("available_branches", [])
        default_branch = project_data.get("default_branch", "main")
        analysis_branch = project_data.get("analysis_branch", default_branch)

        # Priority: use the branch that was analyzed (likely dev/develop), then default
        if analysis_branch and analysis_branch in available_branches:
            #logger.info(f"Using analysis branch as source: {analysis_branch}")
            return analysis_branch
        elif default_branch in available_branches:
            #logger.info(f"Using default branch as source: {default_branch}")
            return default_branch
        else:
            #logger.info(f"Falling back to first available branch")
            return available_branches[0] if available_branches else "main"

    def generate_and_commit(self, project_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Main function: generate pipeline and commit to GitLab
        """
        try:
            #logger.info(f"Starting pipeline generation for: {project_data['name']}")

            # Get branch names and determine best source and target
            branches = self._get_branch_names(config)
            new_branch = branches['feature']
            source_branch = self._get_best_source_branch(project_data, config)
            target_branch = self._get_best_target_branch(project_data)  # Smart target selection

            #logger.info(f"Branch strategy: {source_branch} → {new_branch} → {target_branch}")

            # Step 1: Create branch from best source (likely dev/develop)
            #logger.info(f"Creating new branch from '{source_branch}'...")
            if not self.gitlab.create_branch(new_branch, ref=source_branch):
                #logger.error("Failed to create branch")
                return None

            # Step 2: Prepare files (check against source branch for action type)
            #logger.info("Preparing pipeline files...")
            actions = self._create_pipeline_files(project_data, config, source_branch)

            if not actions:
                #logger.error("No files to create")
                return None

            # Step 3: Commit files
            #logger.info(f"Committing {len(actions)} files...")
            pipeline_type = project_data['type']
            action_word = "Update" if project_data.get('has_pipeline') else "Add"
            commit_message = f"{action_word} pipeline configuration for {pipeline_type}\n\nGenerated by PipeOps CLI\nBased on: {source_branch}"

            commit_result = self.gitlab.commit_files(new_branch, commit_message, actions)
            if not commit_result:
                #logger.error("Failed to commit files")
                return None

            # Step 3.5: Check if pipeline trigger is needed (skip for now to avoid empty pipeline error)
            pipeline_triggered = False
            if project_data.get('has_pipeline') and action_word == "Update":
                #logger.info("Pipeline will be triggered automatically after MR merge")
                pipeline_triggered = False  # Don't trigger manually to avoid empty pipeline issues

            # Step 4: Create Merge Request
            #logger.info(f"Creating merge request: {new_branch} → {target_branch}...")
            mr_title = f"PipeOps: {action_word} pipeline for {pipeline_type}"
            mr_description = self._create_mr_description(project_data, config, actions, source_branch)

            mr_result = self.gitlab.create_merge_request(
                title=mr_title,
                source_branch=new_branch,
                target_branch=target_branch,  # Use our smart target selection
                description=mr_description
            )

            # Prepare result
            result = {
                "success": True,
                "branch_name": new_branch,
                "source_branch": source_branch,
                "target_branch": target_branch,
                "commit": commit_result,
                "merge_request": mr_result,
                "files_created": len(actions),
                "pipeline_type": pipeline_type,
                "pipeline_triggered": pipeline_triggered
            }

            #logger.info("Pipeline generation completed successfully!")
            return result

        except Exception as e:
            #logger.error(f"Pipeline generation failed: {e}")
            return None

    def _create_mr_description(self, project_data: Dict[str, Any], config: Dict[str, Any],
                               actions: List[Dict[str, Any]], source_branch: str) -> str:
        """
        Create description for merge request
        """
        pipeline_type = project_data['type']
        pipeline_config = config['pipelines'][pipeline_type]

        description = f"""## PipeOps: Automated Pipeline Setup

### Project Information
- **Project**: `{project_data['name']}`
- **Pipeline Type**: `{pipeline_type}`
- **Source Branch**: `{source_branch}` (used as base for new pipeline)
- **Generated**: {datetime.date.today().strftime('%Y-%m-%d')}

### Branch Flow
```
{source_branch} → feature/pipeops → (target branch)
```

### Files Modified
"""

        for action in actions:
            emoji = "📝" if action['action'] == 'update' else "✨"
            description += f"- {emoji} `{action['file_path']}` ({action['action']}d)\n"

        description += f"""
### Required Environment Variables
"""

        for var in pipeline_config.get('required_env', []):
            description += f"- `{var}`\n"

        description += f"""
### Next Steps
1. Review the pipeline configuration files
2. Ensure all required environment variables are configured
3. Merge this MR to activate the pipeline
4. Monitor the first pipeline run

---
*Generated by PipeOps CLI from `{source_branch}` branch*
"""

        return description