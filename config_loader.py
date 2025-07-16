# src/config_loader.py
import json
import logging

logger = logging.getLogger(__name__)

def load_config(config_file):
    try:
        with open(config_file, "r") as f:
            config = json.load(f)
            logger.debug(f"Loaded configuration from {config_file}")
            return config
    except FileNotFoundError:
        logger.debug(f"Config file {config_file} not found. Relying on environment variables.")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file {config_file}: {str(e)}")
        raise ValueError(f"Invalid JSON in config file: {str(e)}")
