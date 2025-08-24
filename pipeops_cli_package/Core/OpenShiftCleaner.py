import subprocess
import time
from typing import Dict, List, Optional
from Utiles.logger import logger


class OpenShiftCleaner:
    """
    Simple OpenShift resource cleanup tool for DevOps teams.
    Handles login and resource deletion when deploy jobs fail.
    """

    def __init__(self, oc_url: str, oc_token: str):
        """
        Initialize with OpenShift cluster details
        :param oc_url: OpenShift cluster URL
        :param oc_token: Authentication token
        """
        self.oc_url = oc_url
        self.oc_token = oc_token
        self.logged_in = False

    def login(self) -> bool:
        """
        Login to OpenShift cluster
        :return: True if successful, False otherwise
        """
        logger.info(f"Logging in to OpenShift cluster: {self.oc_url}")

        try:
            # Check if oc command exists
            subprocess.run(['oc', 'version', '--client'],
                           check=True, capture_output=True, text=True, timeout=10)

            # Login command
            login_cmd = [
                'oc', 'login', self.oc_url,
                f'--token={self.oc_token}',
                '--insecure-skip-tls-verify=true'
            ]

            result = subprocess.run(login_cmd, check=True, capture_output=True, text=True, timeout=30)

            self.logged_in = True
            logger.info("✅ OpenShift login successful")
            return True

        except subprocess.TimeoutExpired:
            logger.error("❌ OpenShift login timed out")
            return False
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if e.stderr else str(e)
            logger.error(f"❌ OpenShift login failed: {error_msg}")
            return False
        except FileNotFoundError:
            logger.error("❌ OpenShift CLI ('oc') not found. Please install oc command")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error during login: {e}")
            return False

    def cleanup_service_and_route(self, service_name: str, route_name: str = None) -> Dict[str, bool]:
        """
        Clean up OpenShift service and route
        :param service_name: Name of the service to delete
        :param route_name: Name of the route to delete (defaults to service_name-route)
        :return: Dictionary with cleanup results
        """
        if not self.logged_in:
            logger.error("❌ Not logged in to OpenShift. Run login() first.")
            return {"service": False, "route": False, "logged_in": False}

        if not route_name:
            route_name = f"{service_name}-route"

        logger.info(f"Starting cleanup for service: {service_name}, route: {route_name}")

        results = {"logged_in": True}

        # Clean up route
        logger.info(f"Deleting route: {route_name}")
        results["route"] = self._delete_resource("route", route_name)

        # Clean up service
        logger.info(f"Deleting service: {service_name}")
        results["service"] = self._delete_resource("service", service_name)

        # Additional cleanup - deployment and pods
        logger.info(f"Cleaning up deployment for: {service_name}")
        results["deployment"] = self._delete_resource("deployment", service_name)

        logger.info(f"Cleaning up pods for: {service_name}")
        results["pods"] = self._delete_pods_by_label(service_name)

        # Summary
        successful_cleanups = sum(1 for v in results.values() if v is True)
        total_cleanups = len([k for k in results.keys() if k != "logged_in"])

        logger.info(f"Cleanup completed: {successful_cleanups}/{total_cleanups} resources cleaned")

        return results

    def _delete_resource(self, resource_type: str, resource_name: str) -> bool:
        """
        Delete a specific OpenShift resource
        :param resource_type: Type of resource (service, route, deployment, etc.)
        :param resource_name: Name of the resource
        :return: True if successful or resource not found, False if error
        """
        try:
            cmd = ['oc', 'delete', resource_type, resource_name, '--ignore-not-found=true']

            result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=60)

            if "deleted" in result.stdout or "not found" in result.stderr:
                logger.info(f"✅ {resource_type} '{resource_name}' cleaned up successfully")
                return True
            else:
                logger.warning(f"⚠️  Unexpected output for {resource_type} '{resource_name}': {result.stdout}")
                return True  # Assume success if no error

        except subprocess.TimeoutExpired:
            logger.error(f"❌ Timeout deleting {resource_type} '{resource_name}'")
            return False
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if e.stderr else str(e)
            logger.warning(f"⚠️  Could not delete {resource_type} '{resource_name}': {error_msg}")
            return False  # Return False for actual errors, but don't fail the whole process
        except Exception as e:
            logger.error(f"❌ Unexpected error deleting {resource_type} '{resource_name}': {e}")
            return False

    def _delete_pods_by_label(self, app_name: str) -> bool:
        """
        Delete pods by app label
        :param app_name: App name to use as label selector
        :return: True if successful
        """
        try:
            cmd = ['oc', 'delete', 'pods', '-l', f'app={app_name}', '--ignore-not-found=true']

            result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=60)

            logger.info(f"✅ Pods for app '{app_name}' cleaned up")
            return True

        except Exception as e:
            logger.warning(f"⚠️  Could not delete pods for app '{app_name}': {e}")
            return False

    def verify_cleanup(self, service_name: str, route_name: str = None) -> Dict[str, bool]:
        """
        Verify that resources were actually deleted
        :param service_name: Service name to check
        :param route_name: Route name to check
        :return: Dictionary showing which resources still exist
        """
        if not route_name:
            route_name = f"{service_name}-route"

        logger.info("Verifying cleanup...")

        results = {}

        # Check service
        results["service_exists"] = self._resource_exists("service", service_name)

        # Check route
        results["route_exists"] = self._resource_exists("route", route_name)

        # Check deployment
        results["deployment_exists"] = self._resource_exists("deployment", service_name)

        # Summary
        still_exist = [k for k, v in results.items() if v]
        if still_exist:
            logger.warning(f"⚠️  Some resources still exist: {', '.join(still_exist)}")
        else:
            logger.info("✅ All resources successfully cleaned up")

        return results

    def _resource_exists(self, resource_type: str, resource_name: str) -> bool:
        """
        Check if a resource still exists
        :param resource_type: Type of resource
        :param resource_name: Name of resource
        :return: True if resource exists, False if not found
        """
        try:
            cmd = ['oc', 'get', resource_type, resource_name]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            return result.returncode == 0

        except Exception:
            return False  # If we can't check, assume it doesn't exist

    def get_current_project(self) -> Optional[str]:
        """
        Get current OpenShift project/namespace
        :return: Project name or None if not available
        """
        try:
            cmd = ['oc', 'project', '-q']
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=10)

            project = result.stdout.strip()
            logger.info(f"Current OpenShift project: {project}")
            return project

        except Exception as e:
            logger.warning(f"Could not get current project: {e}")
            return None


# Standalone function for easy use
def cleanup_openshift_resources(oc_url: str, oc_token: str, service_name: str, route_name: str = None) -> bool:
    """
    Simple function to clean up OpenShift resources
    :param oc_url: OpenShift cluster URL
    :param oc_token: Authentication token
    :param service_name: Service name
    :param route_name: Route name (optional)
    :return: True if cleanup was mostly successful
    """
    cleaner = OpenShiftCleaner(oc_url, oc_token)

    # Login
    if not cleaner.login():
        logger.error("Failed to login to OpenShift")
        return False

    # Cleanup
    results = cleaner.cleanup_service_and_route(service_name, route_name)

    # Verify
    verification = cleaner.verify_cleanup(service_name, route_name)

    # Consider success if at least service and route were handled
    success = results.get("service", False) and results.get("route", False)

    return success