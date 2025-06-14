import logging
import sys
from pathlib import Path

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


def main():
    """Main function to initialize and run the node monitor."""
    logging.info("Starting Cortensor Watcher Bot...")
    config = load_and_validate_config(CONFIG_FILE_PATH)
    monitor = NodeMonitor(config)
    
    try:
        monitor.run()
    except KeyboardInterrupt:
        logging.info("Shutdown initiated by user.")
        monitor.notifier.stop_listener()
        monitor.notifier.send_watcher_stop_message()
    except Exception as e:
        logging.critical("A fatal exception occurred in the main thread.", exc_info=True)
        monitor.notifier.send_watcher_error_message(e)
    finally:
        logging.info("Cortensor Watcher Bot has been shut down.")
        sys.exit(0)


if __name__ == "__main__":
    main()
