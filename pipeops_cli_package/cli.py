#!/usr/bin/env python3
"""
PipeOps CLI - Simple GitLab Pipeline Automation for DevOps Teams
Enhanced version with pipeline monitoring
"""

import sys
import click
from pathlib import Path
from typing import Optional
import time

from Utiles.logger import logger
from Core.ConfigLoader import ConfigLoader
from Core.ProjectAnalyzer import ProjectAnalyzer
from Core.UserInteractor import UserInteractor
from Core.EnvChecker import EnvChecker
from Core.PipelineGenerator import PipelineGenerator
from Core.GitLabHandler import GitLabHandler

# Try to import optional modules
try:
    from Core.PipelineMonitor import PipelineMonitor

    HAS_MONITOR = True
except ImportError:
    HAS_MONITOR = False

try:
    from Core.EnhancedPipelineMonitor import EnhancedPipelineMonitor

    HAS_ENHANCED_MONITOR = True
except ImportError:
    HAS_ENHANCED_MONITOR = False

try:
    from Core.OpenshiftCleaner import cleanup_openshift_resources

    HAS_OPENSHIFT = True
except ImportError:
    HAS_OPENSHIFT = False


def validate_inputs(project_url: str, token: str) -> None:
    """Simple input validation"""
    if not project_url.startswith(('http://', 'https://')):
        raise click.BadParameter("Project URL must start with http:// or https://")

    if len(token) < 10:
        raise click.BadParameter("Token appears to be too short")


@click.group(invoke_without_command=True)
@click.option('--version', is_flag=True, help='Show version')
@click.pass_context
def cli(ctx, version):
    """
    PipeOps CLI - GitLab Pipeline Automation Tool
    Simple tool for DevOps teams in enterprise environments
    """
    if version:
        print("PipeOps CLI v1.3.0")
        print("GitLab Pipeline Automation Tool with Enhanced Monitoring")
        return

    if ctx.invoked_subcommand is None:
        print(ctx.get_help())


@cli.command('init')
@click.option('--project-url', '-p', required=True,
              help='GitLab project URL', type=str)
@click.option('--token', '-t', required=True,
              help='GitLab API token', type=str)
@click.option('--config', '-c',
              help='Path to configuration file',
              type=click.Path(exists=True),
              default='Config/pipeline_definitions.yml')
@click.option('--dry-run', is_flag=True,
              help='Show what would be done without making changes')
@click.option('--auto-confirm', is_flag=True,
              help='Skip user confirmation prompts')
@click.option('--no-monitor', is_flag=True,
              help='Skip pipeline monitoring (monitoring is enabled by default)')
@click.option('--basic-monitor', is_flag=True,
              help='Use basic monitoring instead of enhanced monitoring')
def init(project_url: str, token: str, config: str, dry_run: bool, auto_confirm: bool,
         no_monitor: bool, basic_monitor: bool):
    """Initialize GitLab CI/CD pipeline for a project with automatic monitoring"""

    print("=" * 60)
    print("          PIPEOPS CLI - PIPELINE SETUP")
    print("=" * 60)

    # Monitor pipeline by default (unless disabled or dry-run)
    monitor_pipeline = not no_monitor and not dry_run and HAS_MONITOR
    use_enhanced = not basic_monitor and HAS_ENHANCED_MONITOR

    if dry_run:
        print("🧪 DRY RUN MODE - No changes will be made")
    elif monitor_pipeline:
        if use_enhanced:
            print("🔍 ENHANCED PIPELINE MONITORING ENABLED")
        else:
            print("🔍 BASIC PIPELINE MONITORING ENABLED")
    else:
        print("⏭️  PIPELINE MONITORING DISABLED")
    print("-" * 60)

    try:
        # Validate inputs
        validate_inputs(project_url, token)

        # Step 1: Load configuration
        print("[1/6] Loading configuration...")
        config_loader = ConfigLoader(config)
        config_data = config_loader.load()
        print("✅ Configuration loaded")

        # Step 2: Analyze project
        print("\n[2/6] Analyzing project...")
        analyzer = ProjectAnalyzer(token, project_url)
        project_data = analyzer.analyze()

        if not project_data:
            raise click.ClickException("Failed to analyze project")

        print("✅ Project analyzed")

        # Step 3: User interaction
        print("\n[3/6] Configuration...")
        interactor = UserInteractor()

        if auto_confirm:
            print("⚡ Auto-confirm mode - using detected settings")
            pipeline_type = f"{project_data['language']}_{project_data['type']}"
            project_data['type'] = pipeline_type
        else:
            available_types = list(config_data.get('pipelines', {}).keys())
            project_data = interactor.confirm_or_edit(project_data, available_types)

        print("✅ Configuration confirmed")

        # Validate pipeline type exists
        pipeline_type = project_data['type']
        if pipeline_type not in config_data.get('pipelines', {}):
            available = list(config_data.get('pipelines', {}).keys())
            raise click.ClickException(f"Pipeline type '{pipeline_type}' not found. Available: {', '.join(available)}")

        # Step 4: Check environment variables
        print("\n[4/6] Checking environment variables...")
        pipeline_config = config_data['pipelines'][pipeline_type]
        required_vars = pipeline_config.get('required_env', [])

        env_checker = EnvChecker(token, project_url)
        missing_vars = env_checker.find_missing(required_vars)

        if missing_vars:
            if dry_run:
                print(f"⚠️  Would need to add {len(missing_vars)} variables: {', '.join(missing_vars)}")
            else:
                vars_to_add = interactor.ask_for_env_vars(missing_vars)
                if vars_to_add:
                    env_checker.add_vars(vars_to_add)

        print("✅ Environment variables checked")

        # Step 5: Generate pipeline
        print("\n[5/6] Generating pipeline...")
        generator = PipelineGenerator(token, project_url)

        if dry_run:
            print("🧪 DRY RUN: Would create the following files:")
            files_to_create = pipeline_config.get('files_to_create', [])
            for file_name in files_to_create:
                print(f"  - {file_name}")
            print(f"📁 From template: {pipeline_config.get('template_path')}")
            result = {"success": True, "dry_run": True}
        else:
            result = generator.generate_and_commit(project_data, config_data)

        if not result or not result.get("success"):
            raise click.ClickException("Failed to generate pipeline")

        print("✅ Pipeline generated")

        # Step 6: Success and optional monitoring
        print("\n[6/6] Complete!")

        if not dry_run and result:
            mr_data = result.get('merge_request', {})
            mr_url = mr_data.get('web_url') if mr_data else None
            branch_name = result.get('branch_name')
            interactor.display_success_message(mr_url, branch_name, result)

            # Automatic pipeline monitoring (enabled by default)
            if monitor_pipeline and mr_url:
                if use_enhanced:
                    print(f"\n🔍 Starting enhanced pipeline monitoring...")
                    monitor_merge_request_pipeline(token, project_url, mr_data, env_checker, enhanced=True)
                else:
                    print(f"\n🔍 Starting basic pipeline monitoring...")
                    monitor_merge_request_pipeline(token, project_url, mr_data, env_checker, enhanced=False)
            elif not monitor_pipeline:
                print(f"\n💡 To monitor pipeline: use without --no-monitor flag")

        elif dry_run:
            print("\n🎉 DRY RUN COMPLETED SUCCESSFULLY")
            print("Run without --dry-run to make actual changes")

    except click.ClickException:
        raise
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        raise click.ClickException(f"Configuration error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\n❌ ERROR: {e}")
        print("Check the logs for more details")
        sys.exit(1)


def monitor_merge_request_pipeline(token: str, project_url: str, mr_data: dict, env_checker: EnvChecker,
                                   enhanced: bool = False):
    """Monitor pipeline - unified function for both basic and enhanced"""

    gitlab_handler = GitLabHandler(token, project_url)

    if enhanced and HAS_ENHANCED_MONITOR:
        monitor = EnhancedPipelineMonitor(gitlab_handler)
    elif HAS_MONITOR:
        monitor = PipelineMonitor(gitlab_handler)
    else:
        print("⚠️  No monitoring available")
        return

    try:
        # Wait for pipeline to start
        print("⏳ Waiting for pipeline to start...")
        time.sleep(10)

        # Get branch from MR
        source_branch = mr_data.get('source_branch')

        # Get latest pipeline for the branch
        pipeline = gitlab_handler.get_latest_pipeline_with_id(ref=source_branch)

        if not pipeline:
            print("⚠️  No pipeline found - it may start soon")
            print(f"💡 Check manually: {mr_data.get('web_url', '')}")
            return

        pipeline_id = pipeline['id']
        current_status = pipeline['status']

        print(f"📊 Pipeline {pipeline_id}: {current_status}")

        # Monitor based on status
        if current_status in ['pending', 'running']:
            print("🏃 Monitoring...")
            result = monitor.monitor_pipeline(pipeline_id, max_wait_time=1800)
        else:
            # Already completed - analyze
            if current_status == 'failed':
                print("💥 Pipeline failed - analyzing...")
                if enhanced and hasattr(monitor, '_enhanced_failure_analysis'):
                    analysis = monitor._enhanced_failure_analysis(pipeline_id)
                else:
                    analysis = monitor._analyze_failure(pipeline_id)
                result = {"status": "failed", "failure_analysis": analysis}
            else:
                result = {"status": current_status}

        # Handle results
        if result.get('status') == 'failed':
            duration = result.get('duration', 0)
            print(f"💥 Pipeline failed ({duration:.0f}s)" if duration > 0 else "💥 Pipeline failed")

            failure_analysis = result.get('failure_analysis', {})

            if enhanced and HAS_ENHANCED_MONITOR:
                # Enhanced failure handling
                critical_failures = failure_analysis.get('critical_failures', [])
                deploy_failures = [f for f in critical_failures if f.get('type') == 'deploy']

                if deploy_failures and HAS_OPENSHIFT:
                    print(f"\n🚨 Found {len(deploy_failures)} deploy job failures")
                    handle_deploy_failure_enhanced(gitlab_handler, pipeline_id, env_checker, failure_analysis)
                else:
                    # Use UserInteractor to display
                    interactor = UserInteractor()
                    if hasattr(interactor, 'display_enhanced_failure_details'):
                        recovery_actions = []
                        if hasattr(monitor, '_suggest_recovery_actions'):
                            recovery_actions = monitor._suggest_recovery_actions(failure_analysis)
                        interactor.display_enhanced_failure_details(failure_analysis, recovery_actions)

            else:
                # Basic failure handling
                failed_jobs = failure_analysis.get('failed_jobs', [])
                deploy_job_failed = any(job.get('name') == 'deploy' for job in failed_jobs)

                if deploy_job_failed and HAS_OPENSHIFT:
                    print("🚨 Deploy failed - offering cleanup")
                    handle_deploy_failure_basic(gitlab_handler, pipeline_id, env_checker)
                else:
                    # Use UserInteractor to display
                    interactor = UserInteractor()
                    if hasattr(interactor, 'display_basic_failure_details'):
                        interactor.display_basic_failure_details(failed_jobs)

        elif result.get('status') == 'success':
            duration = result.get('duration', 0)
            print(f"🎉 Pipeline succeeded! ({duration:.0f}s)" if duration > 0 else "🎉 Pipeline succeeded!")
        else:
            print(f"📊 Pipeline: {result.get('status', 'unknown')}")

    except KeyboardInterrupt:
        print("\n⏹️  Monitoring stopped")
    except Exception as e:
        print(f"❌ Monitoring error: {e}")
        logger.error(f"Monitoring error: {e}")


def handle_deploy_failure_enhanced(gitlab_handler: GitLabHandler, pipeline_id: int, env_checker: EnvChecker,
                                   failure_analysis: dict):
    """Handle enhanced deploy failure - simplified"""

    print("\n🔧 ENHANCED DEPLOY FAILURE RECOVERY")
    print("=" * 50)

    try:
        deploy_failures = [f for f in failure_analysis.get('critical_failures', []) if f.get('type') == 'deploy']

        print(f"🎯 Deploy jobs that failed:")
        for failure in deploy_failures:
            job_name = failure.get('job_name', 'unknown')
            stage = failure.get('stage', 'unknown')
            print(f"   • {job_name} (stage: {stage})")

        # Get environment variables for OpenShift
        all_vars = {}
        try:
            group_vars = env_checker._get_group_variables()
            project_vars = env_checker._get_project_variables()
            all_vars.update(group_vars)
            all_vars.update(project_vars)
        except Exception as e:
            print(f"⚠️  Could not retrieve environment variables: {e}")

        openshift_server = all_vars.get('OPENSHIFT_SERVER')
        openshift_token = all_vars.get('OPENSHIFT_TOKEN')

        if not openshift_server or not openshift_token:
            print("❌ Missing OpenShift credentials (OPENSHIFT_SERVER/OPENSHIFT_TOKEN)")
            return

        # Get project name for service cleanup
        project_name = env_checker.project_path.split('/')[-1]
        service_name = f"{project_name}-service"
        route_name = f"{project_name}-route"

        print(f"🎯 Target resources: {service_name}, {route_name}")
        print(f"🏢 OpenShift cluster: {openshift_server}")

        confirm = input(f"\n🤔 Proceed with enhanced recovery? [Y/n]: ").strip().lower()

        if confirm and confirm not in ['y', 'yes', '']:
            print("⏹️  Enhanced recovery cancelled")
            return

        print("🧹 Cleaning up...")
        cleanup_success = cleanup_openshift_resources(openshift_server, openshift_token, service_name, route_name)

        if cleanup_success:
            print("✅ Cleanup successful")

            # Retry deploy jobs
            jobs = gitlab_handler.get_pipeline_jobs(pipeline_id)
            success_count = 0

            for failure in deploy_failures:
                job_name = failure.get('job_name')
                for job in jobs:
                    if job.get('name') == job_name and job.get('status') == 'failed':
                        if gitlab_handler.retry_job(job['id']):
                            success_count += 1
                            print(f"✅ Successfully retried {job_name}")
                        break

            if success_count > 0:
                print("🔍 Monitor pipeline progress in GitLab")
        else:
            print("❌ Cleanup failed")

    except Exception as e:
        print(f"❌ Recovery error: {e}")


def handle_deploy_failure_basic(gitlab_handler: GitLabHandler, pipeline_id: int, env_checker: EnvChecker):
    """Handle basic deploy failure - unchanged"""

    print("\n🔧 DEPLOY FAILURE RECOVERY")
    print("=" * 40)

    try:
        # Get environment variables for OpenShift
        all_vars = {}
        try:
            group_vars = env_checker._get_group_variables()
            project_vars = env_checker._get_project_variables()
            all_vars.update(group_vars)
            all_vars.update(project_vars)
        except Exception as e:
            print(f"⚠️  Could not retrieve environment variables: {e}")

        openshift_server = all_vars.get('OPENSHIFT_SERVER')
        openshift_token = all_vars.get('OPENSHIFT_TOKEN')

        if not openshift_server or not openshift_token:
            print("❌ Missing OpenShift credentials")
            return

        # Get project name for service cleanup
        project_name = env_checker.project_path.split('/')[-1]
        service_name = f"{project_name}-service"
        route_name = f"{project_name}-route"

        print(f"🎯 Target: {service_name}, {route_name}")

        # Ask user for confirmation
        confirm = input(f"🤔 Clean up OpenShift and retry? [Y/n]: ").strip().lower()

        if confirm and confirm not in ['y', 'yes', '']:
            print("⏹️  Skipping cleanup")
            return

        print("🧹 Cleaning up...")

        cleanup_success = cleanup_openshift_resources(
            openshift_server,
            openshift_token,
            service_name,
            route_name
        )

        if cleanup_success:
            print("✅ Cleanup successful")

            # Retry deploy job
            jobs = gitlab_handler.get_pipeline_jobs(pipeline_id)
            deploy_job = None

            for job in jobs:
                if job.get('name') == 'deploy' and job.get('status') == 'failed':
                    deploy_job = job
                    break

            if deploy_job:
                retry_success = gitlab_handler.retry_job(deploy_job['id'])

                if retry_success:
                    print("✅ Deploy job retried")
                    print("🔍 Check GitLab for results")
                else:
                    print("❌ Failed to retry job")
            else:
                print("⚠️  No failed deploy job found")
        else:
            print("❌ Cleanup failed")

    except Exception as e:
        print(f"❌ Error: {e}")


@cli.command('validate')
@click.option('--config', '-c',
              help='Configuration file to validate',
              type=click.Path(exists=True),
              default='Config/pipeline_definitions.yml')
def validate_config(config: str):
    """Validate pipeline configuration file"""
    print("=" * 50)
    print("    CONFIGURATION VALIDATION")
    print("=" * 50)

    try:
        config_loader = ConfigLoader(config)
        config_data = config_loader.load()

        pipelines = config_data.get('pipelines', {})
        print(f"✅ Configuration is valid")
        print(f"📊 Found {len(pipelines)} pipeline types:")

        for pipeline_name, pipeline_config in pipelines.items():
            template_path = Path(pipeline_config.get('template_path', ''))
            status = "✅" if template_path.exists() else "❌"
            print(f"   {status} {pipeline_name}")

        print("=" * 50)

    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        sys.exit(1)


@cli.command('list')
@click.option('--config', '-c',
              help='Configuration file',
              type=click.Path(exists=True),
              default='Config/pipeline_definitions.yml')
def list_templates(config: str):
    """List available pipeline templates"""
    print("=" * 50)
    print("    AVAILABLE TEMPLATES")
    print("=" * 50)

    try:
        config_loader = ConfigLoader(config)
        config_data = config_loader.load()
        pipelines = config_data.get('pipelines', {})

        for pipeline_name, pipeline_config in pipelines.items():
            print(f"\n🔧 {pipeline_name}")
            if 'description' in pipeline_config:
                print(f"   {pipeline_config['description']}")
            print(f"   Template: {pipeline_config.get('template_path', 'N/A')}")

        print("=" * 50)

    except Exception as e:
        print(f"❌ Failed to list templates: {e}")
        sys.exit(1)


if __name__ == '__main__':
    cli()