#!/usr/bin/env python3
import os
import subprocess
import tarfile
from pathlib import Path
import shutil
import yaml

# === Inputs ===
hub_url = input("Enter Hub URL (e.g. http://10.0.0.1:5000): ").strip()
device_name = input("Enter Device Name: ").strip()
device_id = input(f"Enter Device ID (default {device_name}-NODE): ").strip()
device_id = device_id or f"{device_name}-NODE"

# === Paths ===
SRC_DIR = Path(__file__).parent
BUILD_DIR = SRC_DIR / "agent_build"
TAR_FILE = SRC_DIR / f"ids_agent_{device_id}.tar.xz"

# === Clean build dir ===
if BUILD_DIR.exists():
    shutil.rmtree(BUILD_DIR)
BUILD_DIR.mkdir()

# === Copy Python agent files ===
AGENT_FILES = ["daemon.py", "gui.py", "helper.py", "client.py"]
for f in AGENT_FILES:
    shutil.copy(SRC_DIR / f, BUILD_DIR / f)

# === Create events dir ===
(BUILD_DIR / "events").mkdir()

# === Create agent.yaml ===
agent_yaml = {
    "hub_url": hub_url,
    "device_id": device_id,
    "device_name": device_name,
    "api_key": "",
    "file_monitor": {"enabled": False, "paths": []},
    "network_monitor": {"enabled": True, "ports": []},
}

with open(BUILD_DIR / "agent.yaml", "w") as f:
    yaml.safe_dump(agent_yaml, f)

# === Compile C network monitor ===
net_c = SRC_DIR / "net-mon-libpcap" / "network_monitor.c"
net_bin = BUILD_DIR / "net_mon.bin"

if not net_c.exists():
    raise FileNotFoundError(f"{net_c} not found!")

subprocess.run(["gcc", "-O2", "-Wall", "-o", str(net_bin), str(net_c), "-lpcap"], check=True)
print("[*] Compiled network_monitor.c -> net_mon.bin")

# === Write bootstrap script (install.sh inside tar) ===
bootstrap = BUILD_DIR / "install.sh"
bootstrap.write_text(f"""#!/usr/bin/env bash
set -e
echo "[*] Setting up Python venv..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt || true  # optional

echo "[*] Installing systemd service..."
SERVICE_FILE="/etc/systemd/system/agentd.service"
sudo tee "$SERVICE_FILE" >/dev/null <<EOF
[Unit]
Description=IDS Agent Daemon
After=network.target

[Service]
ExecStart=$(pwd)/.venv/bin/python $(pwd)/daemon.py
WorkingDirectory=$(pwd)
Restart=always
User=$(whoami)

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable agentd.service
sudo systemctl restart agentd.service

echo "[*] Installing GUI desktop entry..."
DESKTOP_FILE="$HOME/.local/share/applications/ids-agent.desktop"
mkdir -p "$(dirname "$DESKTOP_FILE")"
tee "$DESKTOP_FILE" >/dev/null <<EOF
[Desktop Entry]
Name=IDS Agent
Exec=$(pwd)/.venv/bin/python $(pwd)/gui.py
Icon=utilities-terminal
Type=Application
Categories=Utility;Security;
EOF

echo "=== IDS Agent Setup Complete ==="
""")
bootstrap.chmod(0o755)

# === Copy requirements.txt if exists ===
req = SRC_DIR / "requirements.txt"
if req.exists():
    shutil.copy(req, BUILD_DIR / "requirements.txt")

# === Create tar.xz ===
with tarfile.open(TAR_FILE, "w:xz") as tar:
    tar.add(BUILD_DIR, arcname=".")

print(f"[*] Created {TAR_FILE}")
print("[*] Distribute this tar.xz to a new node. Extract and run ./install.sh")
