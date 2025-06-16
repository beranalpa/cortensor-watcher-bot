import logging
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

from app.config import load_and_validate_config
from app.watcher.monitor import NodeMonitor

# Load environment variables from .env file at the very beginning
load_dotenv()

# --- Configuration ---
CONFIG_FILE_PATH = Path("config.json")

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(module)s.%(funcName)s] - %(message)s",
    stream=sys.stdout,
)


def validate_telegram_token(token: str) -> None:
    """Checks if the Telegram Bot Token is valid by calling the getMe API."""
    if not token:
        # This case is already handled by the missing secrets check, but as a safeguard:
        logging.critical("Telegram Bot Token not found in environment variables.")
        sys.exit(1)

    logging.info("Validating Telegram Bot Token...")
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 401:
            logging.critical("Invalid Telegram Bot Token. Please check the 'TELEGRAM_BOT_TOKEN' value in your .env file.")
            sys.exit(1)
        # Raise an exception for other HTTP errors (like 404, 500, etc.)
        response.raise_for_status()
        
        bot_info = response.json().get("result", {})
        bot_username = bot_info.get("username", "Unknown")
        logging.info(f"Telegram Bot Token is valid. Bot Name: @{bot_username}")

    except requests.RequestException as e:
        logging.error(f"Could not connect to Telegram API to validate token. Please check your network connection. Error: {e}")
        # We will not exit here, allowing the bot to run without notifications
        # if it's just a temporary network issue.

def main():
    """Main function to initialize and run the node monitor."""
    logging.info("Starting Cortensor Watcher Bot...")
    
    config = load_and_validate_config(CONFIG_FILE_PATH)
    
    # Perform validation checks before starting the main loop
    validate_telegram_token(config.get("telegram_bot_token", ""))
    
    monitor = NodeMonitor(config)
    
    try:
        monitor.run()
    except KeyboardInterrupt:
        logging.info("Shutdown initiated by user (Ctrl+C).")
        # The finally block will handle the rest
    except Exception as e:
        logging.critical("A fatal exception occurred in the main thread.", exc_info=True)
        if monitor and monitor.notifier:
            monitor.notifier.send_watcher_error_message(e)
    finally:
        logging.info("Shutting down...")
        if 'monitor' in locals() and monitor.notifier:
            monitor.notifier.stop_listener()
            monitor.notifier.send_watcher_stop_message()
        logging.info("Cortensor Watcher Bot has been shut down.")
        sys.exit(0)


if __name__ == "__main__":
    main()
