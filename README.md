<div align="center">

  <img src="https://avatars.githubusercontent.com/u/174224856?s=200&v=4" alt="Project Banner">
<h1>Cortensor Watcher Bot</h1>

This project is an enhanced and feature-rich automated monitoring tool, originally inspired by the work of **scerb**. It is designed to ensure the health, performance, and uptime of a fleet of Cortensor nodes running in Docker. This version adds features like a professional project structure, Telegram-based remote control, and enhanced stagnation alerts.

<p>
    <a href="https://github.com/your-username/cortensor-watcher-bot/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
    <a href="#"><img src="https://img.shields.io/badge/status-active-success.svg" alt="Status"></a>
    <a href="#"><img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python Version"></a>
    <a href="#"><img src="https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white" alt="Docker"></a>
  </p>
  
  </div>

## Key Features

- **Majority Logic Monitoring**: Automatically detects and restarts nodes that lag behind the network majority state, ensuring your fleet stays in sync.
- **Advanced Lag Detection**: Uses a two-tiered system to differentiate between minor state deviations (short grace period) and major session ID lags (longer grace period).
- **Proactive Error Detection**: Instantly restarts nodes upon detecting critical errors in logs, such as Python `Traceback`s or repeated network `Ping Failures`.
- **Network Stagnation Alerts**: Notifies you if the *entire* network of monitored nodes appears to be stuck, which could indicate an external issue (e.g., with an Oracle or RPC).
- **Remote Control via Telegram**:
    - Enable or disable stagnation alerts on the fly.
    - Configure the stagnation timer remotely.
    - Get a real-time status report of the watcher's configuration.
- **Secure Configuration**: Keeps sensitive data like API tokens and RPC URLs separate and secure using a `.env` file.
- **Automated Logging**: Saves the last 500 lines of a node's logs before every restart for easy diagnostics.

## Prerequisites

Before you begin, ensure you have the following installed on your system:
- [Git](https://git-scm.com/downloads)
- [Python](https://www.python.org/downloads/) (Version 3.8 or newer)
- [Docker](https://www.docker.com/products/docker-desktop/) and Docker Compose
- A Telegram account and a bot created via [@BotFather](https://t.me/BotFather) to get your **Bot Token**.
- Your personal **Chat ID** from a bot like [@userinfobot](https://t.me/userinfobot).

## Installation & Setup

Follow these steps to get the bot up and running.

### 1. Clone the Repository

Open your terminal and clone the repository to your local machine.

```bash
# Replace with the actual URL to your repository
git clone https://github.com/beranalpa/cortensor-watcher-bot.git
cd cortensor-watcher-bot
```

### 2. Create a Python Virtual Environment

It is highly recommended to use a virtual environment to isolate project dependencies.

```bash
# Create the virtual environment
python3 -m venv venv

# Activate it
# On Linux:
source venv/bin/activate
```
You will see `(venv)` at the beginning of your terminal prompt.

### 3. Install Dependencies

Install the required Python libraries using the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

## Configuration

The bot's configuration is split into two files for security and ease of use.

### A. Secret Configuration (`.env` file)

This file stores all your sensitive information and **must not** be shared.

1.  Create a file named `.env` in the root directory of the project.
2.  Copy the content below into the file and fill it with your actual credentials.

```env
# Environment variables for the Cortensor Watcher Bot

TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID="YOUR_TELEGRAM_CHAT_ID_HERE"
RPC_URL="YOUR_RPC_PROVIDER"
```

### B. Operational Configuration (`config.json` file)

This file controls which nodes to monitor and other operational settings.

1.  Open the `config.json` file.
2.  List all the Docker container names and their corresponding node addresses that you wish to monitor. The bot is designed to be scalable and will automatically monitor all entries you provide.

> **IMPORTANT: Removing Comments from `config.json`**
>
> The example below uses `//` comments for explanation. The standard JSON format **does not support comments**. You must remove all comment lines (`// ...`) for the bot to work correctly.

**Example `config.json` Template (with comments for guidance):**
```json
{
  "containers": [
    "cortensor-1",
    "cortensor-2",
    "cortensor-3",
    // ... Continue this pattern for all your nodes (e.g., up to "cortensor-25")
    "cortensor-25"
  ],
  "node_addresses": {
    "cortensor-1": "0xYOUR_NODE_ADDRESS_1",
    "cortensor-2": "0xYOUR_NODE_ADDRESS_2",
    "cortensor-3": "0xYOUR_NODE_ADDRESS_3",
    // ... Ensure every container above has a corresponding node address here ...
    "cortensor-25": "0xYOUR_NODE_ADDRESS_25"
  },
  "tail_lines": 500,
  "check_interval_seconds": 2.5,
  "grace_period_seconds": 30,
  "stats_api_url": "[https://lb-be-5.cortensor.network/network-stats-tasks](https://lb-be-5.cortensor.network/network-stats-tasks)",
  "watch_tx_for_containers": [
    "cortensor-1",
    "cortensor-2",
    "cortensor-3",
    // ... Also list all containers whose transactions you want to monitor ...
    "cortensor-25"
  ],
  "tx_timeout_seconds": 45,
  "stagnation_alert_enabled": true,
  "stagnation_threshold_minutes": 30
}
```

**Valid `config.json` (after removing comments):**
```json
{
  "containers": [
    "cortensor-1",
    "cortensor-2"
  ],
  "node_addresses": {
    "cortensor-1": "0xYOUR_NODE_ADDRESS_1",
    "cortensor-2": "0xYOUR_NODE_ADDRESS_2"
  },
  "tail_lines": 500,
  "check_interval_seconds": 2.5,
  "grace_period_seconds": 30,
  "stats_api_url": "[https://lb-be-5.cortensor.network/network-stats-tasks](https://lb-be-5.cortensor.network/network-stats-tasks)",
  "watch_tx_for_containers": [
    "cortensor-1",
    "cortensor-2"
  ],
  "tx_timeout_seconds": 45,
  "stagnation_alert_enabled": true,
  "stagnation_threshold_minutes": 30
}
```


## Usage

### Running the Bot
Once configured, run the bot from the project's root directory:
```bash
python3 main.py
```
The bot will start, send a confirmation message to your Telegram, and begin monitoring your nodes.

### Stopping the Bot
To stop the bot gracefully, press `Ctrl+C` in the terminal where it is running. It will send a final "Stopped" message to your Telegram.

### Telegram Commands
You can interact with the bot directly from your Telegram chat.

- <b>/help</b>
  Displays a list of all available commands.
- <b>/status</b>
  Shows the current operational status, including how many containers are being monitored and the stagnation alert settings.
- <b>/stagnation on</b>
  Enables the network stagnation alert.
- <b>/stagnation off</b>
  Disables the network stagnation alert.
- <b>/stagnation_timer &lt;minutes&gt;</b>
  Sets how long the majority state must be unchanged before a stagnation alert is triggered.
  _Example: /stagnation_timer 60
  sets the timer to one hour._

## Acknowledgements

This project was heavily inspired by the original work on node monitoring scripts by **scerb**. A big thank you for providing the foundational concepts and logic that made this enhanced version possible.

- You can find the project that inspired this one here: **[scerb/node_watch](https://github.com/scerb/node_watch/)**

## License
This project is licensed under the MIT License. See the `LICENSE` file for details.
