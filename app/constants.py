# app/constants.py

import re
from pathlib import Path

# --- Filesystem Constants ---
LOG_DIR = Path("restart_logs")
WATCHER_LOG_FILE = Path("watcher.log")

# --- Timing Constants ---
WARMUP_SECONDS = 180  # 3 minutes

# --- Regex Constants ---
RE_LOG_STATE = re.compile(r"Latest ID:\s*(\d+)\s*/\s*Latest State:\s*(\d+)")
RE_ASSIGNED_MINERS = re.compile(r"Assigned Miners:\s*(.*)")
RE_TX_HASH = re.compile(r"TX:\s*(0x[0-9a-fA-F]+)")
RE_LOG_EVENT = re.compile(r"\* Event:\s*(\S+)")

# --- String Pattern Constants ---
PATTERN_PING_FAIL = "Pinging network..."
PATTERN_TRACEBACK = "Traceback (most recent call last):"

# --- Notification Message Templates (using HTML) ---
MSG_RESTART = "🚨 <b>Node Watcher Alert</b> 🚨\n\nRestarting container: <code>{cid}</code>\n<b>Reason</b>: {reason}\n<b>Details</b>: {details}\n<b>Timestamp</b>: {timestamp}"
MSG_RESTART_FAILED = "🔥 <b>CRITICAL</b> 🔥\nFailed to restart container <code>{cid}</code>.\nManual intervention may be required."
MSG_WATCHER_STARTED = "✅ <b>Cortensor Watcher Started</b>\nMonitoring service is now online. Send /help for commands."
MSG_WATCHER_STOPPED = "⏹️ <b>Cortensor Watcher Stopped</b>\nService was shut down manually."
MSG_WATCHER_ERROR = "🔥 <b>WATCHER CRITICAL ERROR</b> 🔥\nThe monitoring script has crashed: {error}\nManual intervention required."

# --- Stagnation & Command Messages (using HTML) ---
MSG_STAGNATION_ALERT = "⚠️ <b>Network Stagnation Alert</b> ⚠️\n\nMajority state <code>{pair}</code> has not changed for over {duration} minutes.\nThis might indicate an issue with the Oracle or RPC."
MSG_CMD_RESPONSE = "✅ <b>Command Executed</b>\n\n{response}"
MSG_CMD_UNKNOWN = "❓ <b>Unknown Command</b>\n\nI didn't recognize that command. Send /help to see available commands."
MSG_CMD_HELP = """<b>Cortensor Watcher Bot Commands</b>

<code>/status</code>
View the current monitoring status and settings.

<code>/stagnation on</code>
Enable the network stagnation alert.

<code>/stagnation off</code>
Disable the network stagnation alert.

<code>/stagnation_timer &lt;minutes&gt;</code>
Set the stagnation alert threshold.
<i>Example: /stagnation_timer 60</i>
"""
