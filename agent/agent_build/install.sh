#!/usr/bin/env bash
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
