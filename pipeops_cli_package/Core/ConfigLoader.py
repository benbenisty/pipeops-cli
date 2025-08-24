import yaml
from pathlib import Path
from typing import Dict, List, Any
from Utiles.logger import logger


class ConfigLoader:
    """
    Simple configuration loader for DevOps teams.
    Loads and validates pipeline configuration with basic checks.
    """

    def __init__(self, path="Config/pipeline_definitions.yml"):
        self.path = Path(path)

    def load(self) -> Dict[str, Any]:
        """
        Load configuration file with basic validation
        """
        logger.info(f"Loading configuration from {self.path}")

        if not self.path.exists():
            logger.error(f"Configuration file not found: {self.path}")
            raise FileNotFoundError(f"Configuration file not found: {self.path}")

        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)

            if config_data is None:
                raise ValueError("Configuration file is empty")

            # Basic validation
            self._validate_config(config_data)

            logger.info("Configuration loaded successfully")
            return config_data

        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML: {e}")
            raise ValueError(f"Invalid YAML configuration: {e}")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    def _validate_config(self, config: Dict[str, Any]) -> None:
        """
        Basic configuration validation - essential checks only
        """
        logger.info("Validating configuration...")

        # Check for pipelines section
        if 'pipelines' not in config:
            raise ValueError("Configuration missing 'pipelines' section")

        pipelines = config['pipelines']
        if not pipelines or not isinstance(pipelines, dict):
            raise ValueError("'pipelines' section must be a non-empty dictionary")

        # Check each pipeline
        for pipeline_name, pipeline_config in pipelines.items():
            # Required fields
            required_fields = ['template_path', 'required_env', 'files_to_create']

            for field in required_fields:
                if field not in pipeline_config:
                    raise ValueError(f"Pipeline '{pipeline_name}' missing required field '{field}'")

            # Basic type checking
            if not isinstance(pipeline_config['required_env'], list):
                raise ValueError(f"Pipeline '{pipeline_name}': required_env must be a list")

            if not isinstance(pipeline_config['files_to_create'], list):
                raise ValueError(f"Pipeline '{pipeline_name}': files_to_create must be a list")

        # Check template directories exist (warning only, not error)
        self._check_template_paths(config)

        logger.info(f"Configuration validated - found {len(pipelines)} pipeline types")

    def _check_template_paths(self, config: Dict[str, Any]) -> None:
        """
        Check if template directories exist - log warnings for missing ones
        """
        for pipeline_name, pipeline_config in config['pipelines'].items():
            template_path = Path(pipeline_config['template_path'])

            if not template_path.exists():
                logger.warning(f"Template directory missing: {template_path} (for {pipeline_name})")
                continue

            # Check template files
            missing_files = []
            for file_name in pipeline_config['files_to_create']:
                file_path = template_path / file_name
                if not file_path.exists():
                    missing_files.append(file_name)

            if missing_files:
                logger.warning(f"Missing template files in {pipeline_name}: {', '.join(missing_files)}")

    def get_pipeline_config(self, config: Dict[str, Any], pipeline_type: str) -> Dict[str, Any]:
        """
        Get configuration for specific pipeline type
        """
        if 'pipelines' not in config:
            raise ValueError("Configuration missing pipelines section")

        if pipeline_type not in config['pipelines']:
            available = list(config['pipelines'].keys())
            raise ValueError(f"Pipeline type '{pipeline_type}' not found. Available: {', '.join(available)}")

        return config['pipelines'][pipeline_type]

    def get_supported_pipeline_types(self, config: Dict[str, Any]) -> List[str]:
        """
        Get list of all supported pipeline types
        """
        return list(config.get('pipelines', {}).keys())

    def get_global_config(self, config: Dict[str, Any], section: str = None) -> Dict[str, Any]:
        """
        Get global configuration section
        """
        global_config = config.get('global', {})

        if section:
            return global_config.get(section, {})

        return global_config