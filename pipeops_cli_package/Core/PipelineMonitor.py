import time
from typing import Optional, Dict
from Core.GitLabHandler import GitLabHandler
from Core.OpenShiftCleaner import cleanup_openshift_resources
from Utiles.logger import logger


class PipelineMonitor:
    """
    Simple pipeline monitor for DevOps teams.
    Monitors GitLab pipelines and handles deploy failures with OpenShift cleanup.
    """

    def __init__(self, gitlab_handler: GitLabHandler, check_interval: int = 30):
        """
        Initialize pipeline monitor
        :param gitlab_handler: GitLab API handler
        :param check_interval: Time between status checks in seconds
        """
        self.gitlab = gitlab_handler
        self.check_interval = check_interval

    def monitor_pipeline(self, pipeline_id: int, max_wait_time: int = 1800) -> Dict[str, any]:
        """
        Monitor a pipeline until completion
        :param pipeline_id: ID of pipeline to monitor
        :param max_wait_time: Maximum time to wait in seconds (default 30 minutes)
        :return: Dictionary with monitoring results
        """
        logger.info(f"Starting pipeline monitoring for pipeline: {pipeline_id}")

        start_time = time.time()
        checks = 0

        while time.time() - start_time < max_wait_time:
            checks += 1

            # Get pipeline status
            pipeline_info = self.gitlab.get_pipeline_by_id(pipeline_id)
            if not pipeline_info:
                logger.error(f"Could not get pipeline {pipeline_id} information")
                return {"status": "error", "error": "Could not retrieve pipeline info"}

            current_status = pipeline_info.get('status', 'unknown')
            elapsed = time.time() - start_time

            logger.info(f"Pipeline {pipeline_id} status: {current_status} (check #{checks}, {elapsed:.0f}s elapsed)")

            # Check if finished
            if current_status in ('success', 'failed', 'canceled', 'skipped'):
                result = {
                    "status": current_status,
                    "pipeline_id": pipeline_id,
                    "duration": elapsed,
                    "checks": checks
                }

                if current_status == 'failed':
                    logger.warning(f"Pipeline {pipeline_id} failed - analyzing...")
                    result["failure_analysis"] = self._analyze_failure(pipeline_id)

                return result

            # Wait before next check
            time.sleep(self.check_interval)

        # Timeout
        logger.warning(f"Pipeline monitoring timed out after {max_wait_time}s")
        return {
            "status": "timeout",
            "pipeline_id": pipeline_id,
            "duration": max_wait_time,
            "checks": checks
        }

    def _analyze_failure(self, pipeline_id: int) -> Dict[str, any]:
        """
        Analyze failed pipeline and identify failed jobs
        :param pipeline_id: Failed pipeline ID
        :return: Analysis results
        """
        try:
            jobs = self.gitlab.get_pipeline_jobs(pipeline_id)
            if not jobs:
                return {"error": "Could not retrieve pipeline jobs"}

            failed_jobs = []
            for job in jobs:
                if job.get('status') == 'failed':
                    failed_jobs.append({
                        "name": job.get('name'),
                        "id": job.get('id'),
                        "stage": job.get('stage')
                    })

            logger.info(f"Found {len(failed_jobs)} failed jobs")

            return {
                "failed_jobs": failed_jobs,
                "total_jobs": len(jobs)
            }

        except Exception as e:
            logger.error(f"Failed to analyze pipeline failure: {e}")
            return {"error": str(e)}

    def handle_deploy_failure(self, pipeline_id: int, oc_url: str, oc_token: str,
                              service_name: str, route_name: str = None) -> bool:
        """
        Handle deployment failure by cleaning OpenShift resources and retrying
        :param pipeline_id: Failed pipeline ID
        :param oc_url: OpenShift cluster URL
        :param oc_token: OpenShift token
        :param service_name: Service name to clean
        :param route_name: Route name to clean
        :return: True if handled successfully
        """
        logger.info(f"Handling deploy failure for pipeline {pipeline_id}")

        try:
            # Get failed jobs
            jobs = self.gitlab.get_pipeline_jobs(pipeline_id)
            deploy_job = None

            for job in jobs:
                if job.get('name') == 'deploy' and job.get('status') == 'failed':
                    deploy_job = job
                    break

            if not deploy_job:
                logger.info("No failed deploy job found")
                return False

            logger.info(f"Found failed deploy job: {deploy_job['id']}")

            # Clean up OpenShift resources
            logger.info("Cleaning up OpenShift resources...")
            cleanup_success = cleanup_openshift_resources(oc_url, oc_token, service_name, route_name)

            if cleanup_success:
                logger.info("✅ OpenShift cleanup successful")
            else:
                logger.warning("⚠️  OpenShift cleanup had issues, but continuing...")

            # Retry the deploy job
            logger.info("Retrying deploy job...")
            retry_success = self.gitlab.retry_job(deploy_job['id'])

            if retry_success:
                logger.info("✅ Deploy job retry initiated successfully")
                return True
            else:
                logger.error("❌ Failed to retry deploy job")
                return False

        except Exception as e:
            logger.error(f"Error handling deploy failure: {e}")
            return False

    def wait_for_job_completion(self, pipeline_id: int, job_name: str, timeout: int = 600) -> Dict[str, any]:
        """
        Wait for a specific job to complete
        :param pipeline_id: Pipeline ID
        :param job_name: Job name to wait for
        :param timeout: Timeout in seconds
        :return: Job completion results
        """
        logger.info(f"Waiting for job '{job_name}' in pipeline {pipeline_id}")

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                jobs = self.gitlab.get_pipeline_jobs(pipeline_id)
                target_job = None

                for job in jobs:
                    if job.get('name') == job_name:
                        target_job = job
                        break

                if not target_job:
                    return {"error": f"Job '{job_name}' not found"}

                job_status = target_job.get('status', 'unknown')

                if job_status in ('success', 'failed', 'canceled', 'skipped'):
                    duration = time.time() - start_time
                    logger.info(f"Job '{job_name}' completed with status: {job_status}")

                    return {
                        "job_name": job_name,
                        "status": job_status,
                        "duration": duration,
                        "job_info": target_job
                    }

                logger.info(f"Job '{job_name}' status: {job_status}")
                time.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"Error waiting for job: {e}")
                time.sleep(self.check_interval)

        return {
            "job_name": job_name,
            "status": "timeout",
            "duration": timeout
        }


# Simple function for quick deploy failure handling
def handle_failed_deploy(gitlab_handler: GitLabHandler, pipeline_id: int,
                         oc_url: str, oc_token: str, service_name: str) -> bool:
    """
    Quick function to handle a failed deploy job
    :param gitlab_handler: GitLab API handler
    :param pipeline_id: Failed pipeline ID
    :param oc_url: OpenShift URL
    :param oc_token: OpenShift token
    :param service_name: Service name
    :return: True if handled successfully
    """
    monitor = PipelineMonitor(gitlab_handler)
    return monitor.handle_deploy_failure(pipeline_id, oc_url, oc_token, service_name)
