# hub_client.py
import requests
import yaml
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "agent.yaml"

def fetch_api_key(device_id: str, device_name: str, hub_url: str, secret_token: str):
    """
    Request a new API key from the dashboard if agent.yaml does not have one.
    """
    url = f"{hub_url}/api/devices/"
    headers = {
        "X-Internal-Auth": secret_token,
        "Content-Type": "application/json"
    }
    payload = {"device_id": device_id, "name": device_name}

    resp = requests.post(url, json=payload, headers=headers)
    if resp.status_code in [200, 201]:
        api_key = resp.json()["api_key"]
        print(f"[INFO] Retrieved API key for {device_id}: {api_key[:6]}...")

        # Save it back to agent.yaml
        config = yaml.safe_load(CONFIG_FILE.read_text())
        config["api_key"] = api_key
        CONFIG_FILE.write_text(yaml.dump(config))
        return api_key
    elif resp.status_code == 409:  # Device already exists
        api_key = resp.json().get("api_key")
        print(f"[INFO] Device already registered. Using existing API key.")
        return api_key
    else:
        raise RuntimeError(f"Failed to fetch API key: {resp.status_code}, {resp.text}")

def send_event(event_json: dict):
    print("[DEBUG] Event ready to send:", event_json)
