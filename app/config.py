import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict


def load_and_validate_config(path: Path) -> Dict[str, Any]:
    """
    Loads configuration from a JSON file and merges it with secrets from
    environment variables loaded from a .env file.
    """
    logging.info(f"Loading base configuration from '{path}'.")
    if not path.is_file():
        logging.critical(f"Config file not found at '{path}'. Please create it.")
        sys.exit(1)

    # Load base config from JSON
    try:
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        logging.critical(f"Failed to parse config file '{path}': {e}")
        sys.exit(1)

    # Load secrets from environment variables
    logging.info("Loading secrets from environment variables.")
    secrets = {
        "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN"),
        "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID"),
        "rpc_url": os.getenv("RPC_URL"),
    }

    # Validate that secrets are present
    missing_secrets = [key for key, value in secrets.items() if not value]
    if missing_secrets:
        logging.critical(
            f"Missing required environment variables: {', '.join(key.upper() for key in missing_secrets)}. "
            "Please define them in your .env file."
        )
        sys.exit(1)

    # Merge secrets into the main config dictionary
    config.update(secrets)

    logging.info("Configuration loaded and validated successfully.")
    return config
