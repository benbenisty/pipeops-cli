import requests
import urllib.parse
from Utiles.logger import logger


class EnvChecker:
    """
    Class Purpose: To manage environment variables in a GitLab project.
    It identifies existing variables, supplements missing ones, and ensures the project is ready to run a pipeline.
    """

    def __init__(self, token, project_url):
        """
        Initializes the class with a token and the project URL.
        :param token: A personal token for connecting to the GitLab API.
        :param project_url: The URL of the project.
        """
        self.token = token
        self.project_url = project_url
        self.api_base, self.project_path = self._extract_gitlab_parts()
        logger.info(f"Initialized EnvChecker for project {self.project_path}")

    def _extract_gitlab_parts(self):
        """
        Extracts the API base and the full project path from the URL.
        For example: from `https://gitlab.com/devops/tools/pipeops` it extracts `https://gitlab.com/api/v4`
        and `devops/tools/pipeops`.
        :return: A tuple of (api_base, project_path).
        """
        parts = urllib.parse.urlparse(self.project_url)
        scheme = parts.scheme
        netloc = parts.netloc
        path = parts.path.strip('/')
        api_base = f"{scheme}://{netloc}/api/v4"
        project_path = path
        return api_base, project_path

    def _headers(self):
        """
        Returns a dictionary of HTTP headers that includes the token, for use in API calls.
        """
        return {"PRIVATE-TOKEN": self.token, "Content-Type": "application/json"}

    def _get_project_id(self):
        """
        Encodes the project path to be compatible with the GitLab API as an ID.
        For example: "devops/tools/pipeops" -> "devops%2Ftools%2Fpipeops".
        """
        return urllib.parse.quote_plus(self.project_path)

    def _get_group_hierarchy(self):
        """
        Calculates all parent groups of the project from the deepest to the top.
        :return: A list of encoded group paths.
        """
        path_parts = self.project_path.split('/')
        if len(path_parts) <= 1:
            return []  # No parent groups

        groups = []
        current_path_list = path_parts[:-1]
        while current_path_list:
            path_str = '/'.join(current_path_list)
            groups.append(urllib.parse.quote_plus(path_str))
            current_path_list.pop()

        return groups

    def _get_project_variables(self):
        """
        Makes a call to the GitLab API to retrieve the environment variables defined in the project.
        :return: A dictionary of {KEY: VALUE} of the variables.
        """
        project_id = self._get_project_id()
        url = f"{self.api_base}/projects/{project_id}/variables"
        try:
            res = requests.get(url, headers=self._headers())
            res.raise_for_status()
            vars_list = res.json()
            return {var['key']: var['value'] for var in vars_list}
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get project variables: {e}")
            return {}

    def _get_group_variables(self):
        """
        Iterates over all parent groups and retrieves variables from them.
        Variables from deeper groups will take precedence.
        :return: A combined dictionary of group variables.
        """
        group_vars = {}
        for group_id in self._get_group_hierarchy():
            url = f"{self.api_base}/groups/{group_id}/variables"
            try:
                res = requests.get(url, headers=self._headers())
                res.raise_for_status()
                vars_list = res.json()
                # Adds only variables that have not yet been defined (maintains hierarchy)
                for var in vars_list:
                    if var['key'] not in group_vars:
                        group_vars[var['key']] = var['value']
            except requests.exceptions.RequestException as e:
                logger.warning(f"Failed to get variables for group {group_id}: {e}")
        return group_vars

    def find_missing(self, required_vars: list):
        """
        Receives a list of required variables and finds which ones are missing from the project and its parent groups.
        :param required_vars: A list of required variable names.
        :return: A list of the names of the missing variables.
        """
        all_vars = self._get_group_variables()
        project_vars = self._get_project_variables()
        # Combine project variables, they override group variables
        all_vars.update(project_vars)

        missing = [var for var in required_vars if var not in all_vars]

        if missing:
            logger.warning(f"The following variables are missing: {', '.join(missing)}")
        else:
            logger.info("All required variables are present.")

        return missing

    def add_vars(self, vars_dict: dict):
        """
        Adds new variables to the project using the GitLab API.
        :param vars_dict: A dictionary of variables to add: {KEY: VALUE, ...}.
        """
        project_id = self._get_project_id()
        url = f"{self.api_base}/projects/{project_id}/variables"

        for key, value in vars_dict.items():
            payload = {
                "key": key,
                "value": value,
                "protected": False,  # The variables are not protected.
                "masked": False  # The variables are not masked.
            }
            try:
                res = requests.post(url, headers=self._headers(), json=payload)
                res.raise_for_status()
                logger.info(f"Variable '{key}' added successfully.")
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to add variable '{key}': {e}")