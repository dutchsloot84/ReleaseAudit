# src/config_loader.py
import json
import logging
from pathlib import Path
from typing import Dict

try:
    from dotenv import load_dotenv
except ImportError:
    import subprocess
    import sys
    print("Missing dependencies. Installing from requirements.txt...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        from dotenv import load_dotenv
    except Exception as exc:
        raise ImportError(
            "python-dotenv is required. Automatic installation failed. Please run 'pip install -r requirements.txt'"
        ) from exc

logger = logging.getLogger(__name__)

# Minimal default configuration created if config.json is missing
DEFAULT_CONFIG = {
    "repos": {},
    "bitbucket_base_url": "https://bitbucket.example.com/rest/api/1.0",
    "fix_version": "",
    "release_branch": "release",
    "develop_branch": "develop",
    "commit_fetch_limit": 100,
}

# Default environment content created if .env is missing
DEFAULT_ENV = "BITBUCKET_EMAIL=\nBITBUCKET_TOKEN=\n"


def ensure_env_file(env_path: Path) -> None:
    """Create a default .env file if it does not exist."""
    if not env_path.exists():
        try:
            env_path.write_text(DEFAULT_ENV)
            logger.info("Created default .env at %s", env_path)
        except OSError as exc:
            logger.error("Failed to create .env file: %s", exc)


def ensure_default_config(config_path: Path) -> None:
    """Create a default config file if it does not exist."""
    if not config_path.exists():
        try:
            config_path.write_text(json.dumps(DEFAULT_CONFIG, indent=4))
            logger.info("Created default configuration at %s", config_path)
        except OSError as exc:
            logger.error("Failed to create default config: %s", exc)

def load_config(config_file: str) -> Dict[str, object]:
    """Load configuration from JSON file and .env variables.

    If the config file does not exist a minimal default config is created.
    """
    config_path = Path(config_file)
    # Load .env from same directory if present
    env_path = config_path.resolve().parent / ".env"
    ensure_env_file(env_path)
    load_dotenv(env_path)

    ensure_default_config(config_path)

    try:
        with config_path.open("r", encoding="utf-8") as f:
            config = json.load(f)
            logger.debug("Loaded configuration from %s", config_path)
            return config
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON in config file %s: %s", config_path, exc)
        raise ValueError(f"Invalid JSON in config file: {exc}")
    except FileNotFoundError:
        # ensure_default_config already attempted creation, but if we still
        # cannot open the file, give an empty config
        logger.error("Config file %s missing and could not be created", config_path)
        return {}
