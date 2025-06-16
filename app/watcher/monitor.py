import logging
import os
import sys
import threading
import time
from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, Tuple

import docker
import requests
from docker.models.containers import Container

from app.bot.notifier import TelegramNotifier
from app.constants import (LOG_DIR, MSG_CMD_ERROR, MSG_CMD_HELP,
                           MSG_CMD_UNKNOWN, PATTERN_PING_FAIL,
                           PATTERN_TRACEBACK, RE_LOG_STATE, WARMUP_SECONDS,
                           WATCHER_LOG_FILE)

class NodeMonitor:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client = self._connect_to_docker()
        self.start_time = datetime.now(timezone.utc)
        self.notifier = TelegramNotifier(
            token=self.config.get("telegram_bot_token"),
            chat_id=self.config.get("telegram_chat_id")
        )
        self.notifier.start_update_listener(self._handle_telegram_command)
        self.container_states: Dict[str, Dict[str, Any]] = {
            cid: {
                "state_deviation_start_time": None,
                "id_lag_start_time": None,
                "warmed_up": False,
                "reputation_cooldown_until": None
            }
            for cid in self.config["containers"]
        }
        self.last_seen_majority_pair: Optional[Tuple[int, int]] = None
        self.majority_stagnation_start_time: Optional[datetime] = None
        self.alert_sent_for_stagnant_pair: Optional[Tuple[int, int]] = None
        LOG_DIR.mkdir(exist_ok=True)
        if not WATCHER_LOG_FILE.exists():
            WATCHER_LOG_FILE.touch()

    def _connect_to_docker(self) -> docker.DockerClient:
        try:
            client = docker.from_env()
            client.ping()
            logging.info("Successfully connected to Docker daemon.")
            return client
        except Exception as e:
            logging.critical(f"Cannot connect to Docker daemon: {e}")
            sys.exit(1)

    def _restart_container(self, container: Container, reason: str, details: str = "") -> None:
        cid = container.name
        now_utc = datetime.now(timezone.utc)
        timestamp_str = now_utc.strftime("%Y%m%dT%H%M%S")
        logging.warning(f"Restarting container '{cid}'. Reason: {reason}. {details}")
        log_filename = f"{cid}_{reason.lower().replace(' ', '_')}_{timestamp_str}.log"
        log_path = LOG_DIR / log_filename
        try:
            log_content = container.logs(tail=500).decode("utf-8", errors="ignore")
            log_path.write_text(log_content, encoding="utf-8")
        except Exception as e:
            logging.error(f"Failed to write restart log for '{cid}': {e}")
        event_log_entry = (
            f"{now_utc.isoformat()} | RESTART | Container: {cid} | Reason: {reason} | "
            f"Details: {details} | Logfile: {log_path.name}\n"
        )
        with WATCHER_LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(event_log_entry)
        self.notifier.send_restart_alert(
            cid=cid, reason=reason, details=details,
            timestamp=now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')
        )
        
        if cid in self.container_states:
            state_info = self.container_states[cid]
            state_info["state_deviation_start_time"] = None
            state_info["id_lag_start_time"] = None
            if reason == "Reputation Failure":
                cooldown_minutes = self.config.get("reputation_restart_cooldown_minutes", 30)
                cooldown_end_time = now_utc + timedelta(minutes=cooldown_minutes)
                state_info["reputation_cooldown_until"] = cooldown_end_time
                logging.info(f"DEBUG: Setting cooldown for '{cid}' until {cooldown_end_time.isoformat()}")
        try:
            container.restart(timeout=30)
            logging.info(f"Restart command sent successfully to '{cid}'.")
        except Exception as e:
            logging.error(f"Failed to restart container '{cid}': {e}")
            self.notifier.send_restart_failure_alert(cid)
            
    def _check_reputation(self) -> None:
        if not self.config.get("reputation_check_enabled"): return
        logging.info("Performing Reputation Health Check...")
        base_url = self.config.get("reputation_api_base_url", "").rstrip('/')
        window = self.config.get("reputation_check_window", 20)
        threshold = self.config.get("reputation_failure_threshold", 5)
        node_addresses = self.config.get("node_addresses", {})
        now = datetime.now(timezone.utc)
        for cid, address in node_addresses.items():
            state_info = self.container_states.get(cid)
            if not state_info: continue
            cooldown_until = state_info.get("reputation_cooldown_until")
            if cooldown_until:
                is_in_cooldown = now < cooldown_until
                logging.info(f"DEBUG: Checking cooldown for '{cid}'. Now: {now.isoformat()}. Cooldown until: {cooldown_until.isoformat()}. In cooldown: {is_in_cooldown}")
            if cooldown_until and now < cooldown_until:
                logging.info(f"Skipping reputation check for '{cid}', it is in cooldown.")
                continue
            api_url = f"{base_url}/{address}"
            try:
                container = self.client.containers.get(cid)
                if not state_info.get("warmed_up", False): continue
                response = requests.get(api_url, timeout=10)
                if response.status_code == 404:
                    logging.warning(f"Reputation API for '{cid}' returned 404. URL: {api_url}")
                    continue
                response.raise_for_status()
                data = response.json()
                for stage in ["precommit", "commit"]:
                    stage_data = data.get(stage, {})
                    all_ts, success_ts = stage_data.get("all_timestamps", []), stage_data.get("success_timestamps", [])
                    if not all_ts: continue
                    recent, successful = set(all_ts[-window:]), set(success_ts)
                    failed_count = len(recent - successful)
                    if failed_count > 0:
                        logging.info(f"Reputation Check for '{cid}' ({stage}): Found {failed_count} failed tasks in last {len(recent)}.")
                    if failed_count >= threshold:
                        details = f"Node had {failed_count} failed {stage} tasks in the last {len(recent)} attempts."
                        self._restart_container(container, "Reputation Failure", details)
                        break
            except Exception as e:
                logging.error(f"Error during reputation check for '{cid}': {e}")

    def run(self) -> None:
        self.notifier.send_watcher_start_message()
        while True:
            try:
                os.system("clear || cls")
                now_utc = datetime.now(timezone.utc)
                self._print_status_header(now_utc)
                is_warmed_up = (now_utc - self.start_time).total_seconds() >= WARMUP_SECONDS
                for state in self.container_states.values():
                    state["warmed_up"] = is_warmed_up
                if self.config.get("reputation_check_enabled"): self._check_reputation()
                all_statuses = self._get_all_container_statuses()
                running_nodes = {cid: status for cid, status in all_statuses.items() if status.get("is_running") and "session_id" in status}
                if len(running_nodes) < 2:
                    logging.warning("Not enough nodes reporting status to determine a majority.")
                else:
                    id_state_pairs = [(v["session_id"], v["state"]) for v in running_nodes.values()]
                    majority_pair, count = Counter(id_state_pairs).most_common(1)[0]
                    logging.info(f"Network Majority (ID, State): {majority_pair} ({count}/{len(running_nodes)} nodes)")
                    self._check_for_majority_stagnation(now_utc, majority_pair)
                    print()
                    self._evaluate_all_nodes(all_statuses, majority_pair)
                time.sleep(self.config["check_interval_seconds"])
            except KeyboardInterrupt:
                break
            except Exception as e:
                logging.critical(f"An unhandled error in the main loop: {e}", exc_info=True)
                self.notifier.send_watcher_error_message(e)
                time.sleep(10)

    def _get_all_container_statuses(self) -> Dict[str, Dict[str, Any]]:
        statuses = {}
        for cid in self.config["containers"]:
            try:
                container = self.client.containers.get(cid)
                status_data = {"container": container, "is_running": container.status == "running", "docker_status": container.status}
                if not status_data["is_running"]: statuses[cid] = status_data; continue
                log_lines = container.logs(tail=self.config["tail_lines"]).decode("utf-8", "ignore").splitlines()
                if self.container_states[cid]["warmed_up"]:
                    if any(PATTERN_TRACEBACK in ln for ln in log_lines):
                        self._restart_container(container, "Python Traceback", "A Python 'Traceback' was detected.")
                        continue
                    ping_failures = sum(1 for ln in log_lines[-52:] if PATTERN_PING_FAIL in ln)
                    if ping_failures >= 2:
                        self._restart_container(container, "Ping Failure", f"{ping_failures} instances of '{PATTERN_PING_FAIL}' found.")
                        continue
                for ln in reversed(log_lines):
                    m = RE_LOG_STATE.search(ln)
                    if m: status_data["session_id"], status_data["state"] = int(m.group(1)), int(m.group(2)); break
                statuses[cid] = status_data
            except docker.errors.NotFound:
                logging.error(f"Container '{cid}' not found.")
                statuses[cid] = {"is_running": False, "container": None}
            except Exception as e:
                logging.error(f"Error processing container '{cid}': {e}")
                statuses[cid] = {"is_running": False, "container": None}
        return statuses

    def _evaluate_all_nodes(self, all_statuses: Dict[str, Any], majority_pair: Tuple[int, int]) -> None:
        grace_period, id_lag_threshold, now = timedelta(seconds=self.config["grace_period_seconds"]), timedelta(minutes=2), datetime.now(timezone.utc)
        majority_id, majority_state = majority_pair
        for cid, status in all_statuses.items():
            container, docker_status = status.get("container"), status.get("docker_status", "unknown")
            if not status.get("is_running") or container is None:
                logging.warning(f"Container '{cid}' is not running (Status: {docker_status}).")
                if majority_state == 6 and container:
                    self._restart_container(container, "Inactive Node", f"Node status was '{docker_status}' while majority concluded session.")
                continue
            if "session_id" not in status:
                logging.warning(f"Could not parse state for running container '{cid}'."); continue
            current_id, current_state = status["session_id"], status["state"]
            state_info = self.container_states[cid]
            if (current_id, current_state) == majority_pair:
                if state_info["state_deviation_start_time"] or state_info["id_lag_start_time"]:
                    logging.info(f"'{cid}' has re-synced with the majority at {majority_pair}.")
                state_info["state_deviation_start_time"], state_info["id_lag_start_time"] = None, None
                print(f"  - [{cid}]: OK. In sync with majority at state {(current_id, current_state)}."); continue
            if current_state != majority_state:
                if state_info["state_deviation_start_time"] is None:
                    state_info["state_deviation_start_time"] = now
                    logging.warning(f"'{cid}' state ({current_state}) deviates from majority ({majority_state}). Starting grace period timer.")
                else:
                    elapsed = now - state_info["state_deviation_start_time"]
                    if elapsed >= grace_period:
                        if state_info["warmed_up"]:
                            details = f"Node state was {current_state} at ID {current_id}, but majority is at state {majority_state} (ID: {majority_id}). Lagged for {int(elapsed.total_seconds())}s."
                            self._restart_container(container, "State Deviation", details)
                        else: logging.warning(f"'{cid}' state deviation detected but not restarting (still in warm-up).")
                    else: logging.info(f"'{cid}' deviating for {int(elapsed.total_seconds())}s of {int(grace_period.total_seconds())}s grace period.")
                continue
            elif current_id < majority_id:
                if state_info["id_lag_start_time"] is None:
                    state_info["id_lag_start_time"] = now
                    logging.warning(f"'{cid}' ID ({current_id}) lags behind majority ({majority_id}). Starting 2-minute timer.")
                else:
                    elapsed = now - state_info["id_lag_start_time"]
                    if elapsed >= id_lag_threshold:
                        if state_info["warmed_up"]:
                            details = f"Node was stuck at ID {current_id} while majority progressed to ID {majority_id}. Lagged for over 2 minutes."
                            self._restart_container(container, "Session ID Lag", details)
                        else: logging.warning(f"'{cid}' ID lag detected but not restarting (still in warm-up).")
                    else: logging.info(f"'{cid}' ID lagging for {int(elapsed.total_seconds())}s of {int(id_lag_threshold.total_seconds())}s.")
    
    def _print_status_header(self, now: datetime) -> None:
        uptime, is_warmed_up = timedelta(seconds=int((now - self.start_time).total_seconds())), (now - self.start_time).total_seconds() >= WARMUP_SECONDS
        warmup_status = "ACTIVE" if is_warmed_up else f"WARMING UP ({int(uptime.total_seconds())}/{WARMUP_SECONDS}s)"
        header = f"\n--- Cortensor Watcher Status | {now.strftime('%Y-%m-%d %H:%M:%S UTC')} ---\nUptime: {uptime} | Monitoring Status: {warmup_status}"
        print(header)

    def _handle_telegram_command(self, message: Dict) -> None:
        text, parts = message.get("text", "").strip(), message.get("text", "").strip().split()
        command = parts[0].lower()
        logging.info(f"Received command from Telegram: {text}")
        if command in ["/start", "/stop", "/restart", "/logs"]:
            if len(parts) < 2: self.notifier.send_command_response(f"Error: Missing container name.\nUsage: <code>{command} &lt;container_name&gt;</code>"); return
            cid = parts[1]
            try:
                container = self.client.containers.get(cid)
                if command == "/start": container.start(); self.notifier.send_command_response(f"Container <code>{cid}</code> started.")
                elif command == "/stop": container.stop(); self.notifier.send_command_response(f"Container <code>{cid}</code> stopped.")
                elif command == "/restart": container.restart(); self.notifier.send_command_response(f"Container <code>{cid}</code> restarted.")
                elif command == "/logs":
                    num_lines_str = parts[2] if len(parts) > 2 else "20"
                    if not num_lines_str.isdigit(): self.notifier.send_command_response("Error: Line count must be a number."); return
                    logs = container.logs(tail=int(num_lines_str)).decode("utf-8", "ignore")
                    if len(logs) > 4000: logs = "...\n" + logs[-4000:]
                    self.notifier.send_command_response(f"Last {int(num_lines_str)} lines of logs for <code>{cid}</code>:\n<pre>{logs}</pre>")
            except docker.errors.NotFound: self.notifier.send_command_response(f"Error: Container <code>{cid}</code> not found.")
            except Exception as e: self.notifier.send_command_response(MSG_CMD_ERROR.format(error=str(e)))
            return
        response = ""
        if command == "/stagnation":
            if len(parts) > 1:
                sub_cmd = parts[1].lower()
                if sub_cmd == "on": self.config["stagnation_alert_enabled"] = True; response = "Stagnation alerts have been ENABLED."
                elif sub_cmd == "off": self.config["stagnation_alert_enabled"] = False; response = "Stagnation alerts have been DISABLED."
                else: response = f"Unknown sub-command '<code>{sub_cmd}</code>'. Use 'on' or 'off'."
            else: response = "Missing sub-command. Use '<code>/stagnation on</code>' or '<code>/stagnation off</code>'."
        elif command == "/stagnation_timer":
            if len(parts) > 1:
                try:
                    minutes = int(parts[1])
                    if minutes > 0: self.config["stagnation_threshold_minutes"] = minutes; response = f"Stagnation timer set to {minutes} minutes."
                    else: response = "Please provide a positive number of minutes."
                except ValueError: response = "Invalid number. Please provide an integer for minutes."
            else: response = "Missing argument. Usage: <code>/stagnation_timer &lt;minutes&gt;</code>"
        elif command == "/status":
            stagnation_status, stagnation_time, num_containers = "ENABLED" if self.config.get("stagnation_alert_enabled") else "DISABLED", self.config.get("stagnation_threshold_minutes"), len(self.config.get("containers", []))
            response = (f"<b>Watcher Status</b>\n- Monitoring {num_containers} containers.\n- Stagnation Alerts: <b>{stagnation_status}</b>\n- Stagnation Threshold: <b>{stagnation_time} minutes</b>")
        elif command == "/help": self.notifier.send_help_response(); return
        else:
            self.notifier.send_unknown_command_response(); return
        self.notifier.send_command_response(response)
    
    def _check_for_majority_stagnation(self, now: datetime, majority_pair: Tuple[int, int]) -> None:
        if not self.config.get("stagnation_alert_enabled", False): return
        if self.last_seen_majority_pair != majority_pair:
            logging.info(f"Majority has progressed to {majority_pair}. Resetting stagnation timer.")
            self.last_seen_majority_pair, self.majority_stagnation_start_time, self.alert_sent_for_stagnant_pair = majority_pair, None, None
            return
        if self.majority_stagnation_start_time is None:
            self.majority_stagnation_start_time = now
            logging.info(f"Stagnation timer started for majority state {majority_pair} at {now.isoformat()}")
        else:
            threshold_minutes = self.config.get("stagnation_threshold_minutes", 30)
            elapsed = now - self.majority_stagnation_start_time
            if elapsed >= timedelta(minutes=threshold_minutes) and self.alert_sent_for_stagnant_pair != majority_pair:
                logging.warning(f"Network stagnation detected! Majority state {majority_pair} stuck for over {threshold_minutes} minutes.")
                self.notifier.send_stagnation_alert(majority_pair, threshold_minutes)
                self.alert_sent_for_stagnant_pair = majority_pair
            else:
                if self.alert_sent_for_stagnant_pair != majority_pair:
                    logging.info(f"Majority state {majority_pair} has been stable for {int(elapsed.total_seconds() / 60)} minutes.")
