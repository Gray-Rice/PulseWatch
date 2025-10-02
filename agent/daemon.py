import os
import json
import uuid
import time
import yaml
import subprocess
import queue
from datetime import datetime, timezone
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from threading import Thread
from pathlib import Path
from helper import send_event

# === Paths & Config ===
SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "agent.yaml"
EVENT_DIR = SCRIPT_DIR / "events"
NET_MON = SCRIPT_DIR / "net_mon.bin"
os.makedirs(EVENT_DIR, exist_ok=True)

FILE_EVENTS_JSON = EVENT_DIR / "file_events.json"
NETWORK_EVENTS_JSON = EVENT_DIR / "network_events.json"

with open(CONFIG_FILE) as f:
    config = yaml.safe_load(f)

DEVICE_ID = config.get("device_id", "agent-123")
DEVICE_NAME = config.get("device_name", DEVICE_ID)
FILE_PATHS = [Path(p) for p in config.get("file_monitor", {}).get("paths", [])]
FILE_MONITOR_ENABLED = config.get("file_monitor", {}).get("enabled", False)
NETWORK_MONITOR_ENABLED = config.get("network_monitor", {}).get("enabled", False)
HUB_BASE_URL = config.get("hub_url", "http://127.0.0.1:5000")
EVENT_URL = HUB_BASE_URL + "/api/events/"

API_KEY = config.get("api_key", "")
if not API_KEY:
    from client import fetch_api_key
    API_KEY = fetch_api_key(DEVICE_ID, DEVICE_NAME, HUB_BASE_URL, secret_token="super-secret-token")

EVENT_QUEUE = queue.Queue()

# === Helpers ===
def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()

def save_event_locally(event_json: dict, is_file_event: bool):
    filename = FILE_EVENTS_JSON if is_file_event else NETWORK_EVENTS_JSON
    with filename.open("a") as f:
        f.write(json.dumps(event_json) + "\n")
    print(f"[{'FILE' if is_file_event else 'NETWORK'} EVENT] {json.dumps(event_json)}")
    EVENT_QUEUE.put(event_json)

def event_sender_worker():
    while True:
        event_json = EVENT_QUEUE.get()
        try:
            resp = send_event(
                hub_url=EVENT_URL,
                device_id=DEVICE_ID,
                api_key=API_KEY,
                payload_dict=event_json
            )
            if resp:
                print(f"[HUB] Event delivered, status={resp.status_code}")
            else:
                print("[HUB] Send failed, requeueing event")
                EVENT_QUEUE.put(event_json)
                time.sleep(5)
        except Exception as e:
            print(f"[ERROR] Unexpected in sender worker: {e}")
            EVENT_QUEUE.put(event_json)
            time.sleep(5)
        finally:
            EVENT_QUEUE.task_done()

# === File Monitoring ===
class FileEventHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        if event.is_directory:
            return
        if FILE_PATHS and not any(Path(event.src_path).resolve().is_relative_to(p.resolve()) for p in FILE_PATHS):
            return

        event_json = {
            "id": str(uuid.uuid4()),
            "device_id": DEVICE_ID,
            "event_type": "file",  # <-- MUST match hub expectation
            "details": {
                "path": str(event.src_path),
                "action": event.event_type,
                "process": "unknown"
            },
            "timestamp": utc_timestamp()
        }
        save_event_locally(event_json, is_file_event=True)

# === Network Monitoring via C Program ===
def monitor_network_c(c_program_path: Path):
    if not c_program_path.exists():
        print(f"[ERROR] C network monitor not found at {c_program_path}")
        return

    proc = subprocess.Popen(
        [str(c_program_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
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
                "event_type": "network",  # <-- MUST match hub expectation
                "timestamp": utc_timestamp()
            })
            save_event_locally(event_json, is_file_event=False)
        except json.JSONDecodeError:
            print(f"[WARNING] Could not decode JSON from C monitor: {line}")

# === Main Daemon ===
def main():
    print("Daemon started (file + network monitoring).")
    Thread(target=event_sender_worker, daemon=True).start()

    # File monitoring
    observers = []
    if FILE_MONITOR_ENABLED and FILE_PATHS:
        for path in FILE_PATHS:
            if not path.exists():
                print(f"[WARNING] File path does not exist: {path}")
                continue
            observer = Observer()
            observer.schedule(FileEventHandler(), path=str(path), recursive=True)
            observer.start()
            observers.append(observer)

    # Network monitoring
    if NETWORK_MONITOR_ENABLED:
        Thread(target=monitor_network_c, args=(NET_MON,), daemon=True).start()

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
