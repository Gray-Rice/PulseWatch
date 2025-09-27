#!/usr/bin/env python3
import os
import json
import uuid
import time
import yaml
import subprocess
from datetime import datetime, timezone
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from threading import Thread

# === Paths & Config ===
CONFIG_FILE = "agent.yaml"
EVENT_DIR = "events"
os.makedirs(EVENT_DIR, exist_ok=True)

FILE_EVENTS_JSON = os.path.join(EVENT_DIR, "file_events.json")
NETWORK_EVENTS_JSON = os.path.join(EVENT_DIR, "network_events.json")

with open(CONFIG_FILE) as f:
    config = yaml.safe_load(f)

DEVICE_ID = config.get("device_id", "agent-123")
FILE_PATHS = config.get("file_monitor", {}).get("paths", [])
FILE_MONITOR_ENABLED = config.get("file_monitor", {}).get("enabled", False)
NETWORK_MONITOR_ENABLED = config.get("network_monitor", {}).get("enabled", False)

# === Helpers ===
def utc_timestamp() -> str:
    """Return current UTC time in ISO 8601 format with timezone info."""
    return datetime.now(timezone.utc).isoformat()

def save_event_locally(event_json: dict, is_file_event: bool):
    """Append JSON event to the correct local file."""
    filename = FILE_EVENTS_JSON if is_file_event else NETWORK_EVENTS_JSON
    with open(filename, "a") as f:
        f.write(json.dumps(event_json) + "\n")

# === File Monitoring ===
class FileEventHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        if event.is_directory:
            return
        if FILE_PATHS and not any(event.src_path.startswith(p) for p in FILE_PATHS):
            return

        event_json = {
            "id": str(uuid.uuid4()),
            "device_id": DEVICE_ID,
            "type": "file_event",
            "details": {
                "path": event.src_path,
                "action": event.event_type,
                "process": "unknown"
            },
            "timestamp": utc_timestamp()
        }
        save_event_locally(event_json, is_file_event=True)

# === Network Monitoring via C Program ===
def monitor_network_c(c_program_path: str = "./net_mon.bin"):
    """Launch the C network monitor and persist JSON events to file."""
    if not os.path.isfile(c_program_path):
        print(f"[ERROR] C network monitor not found at {c_program_path}")
        return

    proc = subprocess.Popen(
        [c_program_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1  # line-buffered
    )

    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue
        try:
            event_json = json.loads(line)
            event_json.update({
                "id": str(uuid.uuid4()),
                "device_id": DEVICE_ID,
                "type": "network_event",
                "timestamp": utc_timestamp()
            })
            save_event_locally(event_json, is_file_event=False)
        except json.JSONDecodeError:
            print(f"[WARNING] Could not decode JSON from C monitor: {line}")

# === Main Daemon ===
def main():
    print("Daemon started (file + network monitoring).")

    # File monitoring setup
    observers = []
    if FILE_MONITOR_ENABLED and FILE_PATHS:
        for path in FILE_PATHS:
            if not os.path.exists(path):
                print(f"[WARNING] File path does not exist: {path}")
                continue
            observer = Observer()
            observer.schedule(FileEventHandler(), path=path, recursive=True)
            observer.start()
            observers.append(observer)

    # Network monitoring setup
    if NETWORK_MONITOR_ENABLED:
        Thread(target=monitor_network_c, args=("./net_mon.bin",), daemon=True).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Daemon stopped.")
        for obs in observers:
            obs.stop()
            obs.join()

if __name__ == "__main__":
    main()
