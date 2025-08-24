import logging
import sys
from pathlib import Path
from datetime import datetime


# Simple logger configuration for DevOps teams
# No external dependencies, just Python standard library

def setup_logger(name='PipeOps-CLI', level='INFO', log_file=None):
    """
    Simple logger setup without external dependencies
    """
    logger = logging.getLogger(name)

    # Clear existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Set level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    # Console formatter - simple and readable
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    # File formatter - more detailed
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (if requested)
    if log_file:
        try:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

        except Exception as e:
            logger.warning(f"Could not create log file {log_file}: {e}")

    return logger


# Create default logger
logger = setup_logger()


def configure_logging(level='INFO', enable_file_logging=False, log_file=None):
    """
    Reconfigure logging at runtime
    """
    global logger

    if enable_file_logging and not log_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"pipeops_{timestamp}.log"

    logger = setup_logger(
        name='PipeOps-CLI',
        level=level,
        log_file=log_file if enable_file_logging else None
    )

    if enable_file_logging:
        logger.info(f"Logging to file: {log_file}")


# Simple helper functions for structured logging
def log_step(step_num, total_steps, description):
    """Log a step in the process"""
    logger.info(f"[{step_num}/{total_steps}] {description}")


def log_success(message):
    """Log success message"""
    logger.info(f"✅ {message}")


def log_warning(message):
    """Log warning message"""
    logger.warning(f"⚠️  {message}")


def log_error(message):
    """Log error message"""
    logger.error(f"❌ {message}")


def log_debug(message):
    """Log debug message"""
    logger.debug(f"🔍 {message}")


# Export the main logger and helper functions
__all__ = [
    'logger',
    'configure_logging',
    'log_step',
    'log_success',
    'log_warning',
    'log_error',
    'log_debug'
]