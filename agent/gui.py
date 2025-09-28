#!/usr/bin/env python3
import sys
import yaml
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit,
    QLabel, QLineEdit, QFormLayout, QMessageBox, QListWidget, QCheckBox,
    QFileDialog, QTabWidget, QInputDialog
)
from PyQt6.QtCore import QProcess

# ===== Paths =====
SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "agent.yaml"
DAEMON_SCRIPT = SCRIPT_DIR / "daemon.py"
VENV_PYTHON = SCRIPT_DIR.parent / ".venv" / "bin" / "python"  # .venv in parent dir


class IDSAgentUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IDS Agent Control")
        self.resize(750, 600)
        self.process: QProcess | None = None

        # Load config first
        self.config = self.load_config()

        # Main layout
        main_layout = QVBoxLayout(self)

        # Tabs: Daemon/Logs first, Config second
        self.tabs = QTabWidget()
        self.logs_tab = QWidget()
        self.config_tab = QWidget()
        self.tabs.addTab(self.config_tab, "Config")
        self.tabs.addTab(self.logs_tab, "Daemon / Logs")
        main_layout.addWidget(self.tabs)

        # Initialize tabs
        self.init_logs_tab()
        self.init_config_tab()

    # ===== Load config from YAML =====
    def load_config(self):
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
                if not isinstance(cfg, dict):
                    cfg = {}
        return cfg

    # ===== Config Tab =====
    def init_config_tab(self):
        layout = QVBoxLayout(self.config_tab)
        form_layout = QFormLayout()

        # Device ID and API key
        hub_ip = self.config.get("hub_ip")
        device_id = self.config.get("device_id", "agent-123")
        api_key = self.config.get("api_key", "")
        self.hub_ip = QLineEdit(hub_ip)
        self.device_field = QLineEdit(device_id)
        self.apikey_field = QLineEdit(api_key)  # visible

        # File monitor
        filemon_cfg = self.config.get("file_monitor", {})
        self.filemon_enabled = QCheckBox("Enable File Monitor")
        self.filemon_enabled.setChecked(filemon_cfg.get("enabled", False))
        self.paths_list = QListWidget()
        for path in filemon_cfg.get("paths", []):
            self.paths_list.addItem(path)

        path_btn_layout = QHBoxLayout()
        add_path_btn = QPushButton("Add Path")
        add_path_btn.clicked.connect(self.add_path)
        remove_path_btn = QPushButton("Remove Selected")
        remove_path_btn.clicked.connect(self.remove_path)
        path_btn_layout.addWidget(add_path_btn)
        path_btn_layout.addWidget(remove_path_btn)

        # Network monitor
        netmon_cfg = self.config.get("network_monitor", {})
        self.network_enabled = QCheckBox("Enable Network Monitor")
        self.network_enabled.setChecked(netmon_cfg.get("enabled", False))
        self.ports_list = QListWidget()
        for port in netmon_cfg.get("ports", []):
            self.ports_list.addItem(str(port))

        ports_btn_layout = QHBoxLayout()
        add_port_btn = QPushButton("Add Port")
        add_port_btn.clicked.connect(self.add_port)
        remove_port_btn = QPushButton("Remove Selected")
        remove_port_btn.clicked.connect(self.remove_port)
        ports_btn_layout.addWidget(add_port_btn)
        ports_btn_layout.addWidget(remove_port_btn)

        # Assemble form
        form_layout.addRow("HUB IP:", self.hub_ip)
        form_layout.addRow("Device ID:", self.device_field)
        form_layout.addRow("API Key:", self.apikey_field)
        form_layout.addRow(self.filemon_enabled)
        form_layout.addRow(QLabel("File Monitor Paths:"), self.paths_list)
        form_layout.addRow(path_btn_layout)
        form_layout.addRow(self.network_enabled)
        form_layout.addRow(QLabel("Network Ports:"), self.ports_list)
        form_layout.addRow(ports_btn_layout)

        save_btn = QPushButton("Save Config")
        save_btn.clicked.connect(self.save_config)

        # Optional: Reload button to refresh from YAML
        reload_btn = QPushButton("Reload Config")
        reload_btn.clicked.connect(self.reload_config)

        layout.addLayout(form_layout)
        layout.addWidget(save_btn)
        layout.addWidget(reload_btn)

    def add_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if path:
            self.paths_list.addItem(path)

    def remove_path(self):
        for item in self.paths_list.selectedItems():
            self.paths_list.takeItem(self.paths_list.row(item))

    def add_port(self):
        port, ok = QInputDialog.getText(self, "Add Port", "Enter port number:")
        if ok and port:
            try:
                port_num = int(port)
                self.ports_list.addItem(str(port_num))
            except ValueError:
                QMessageBox.warning(self, "Invalid Input", "Port must be an integer.")

    def remove_port(self):
        for item in self.ports_list.selectedItems():
            self.ports_list.takeItem(self.ports_list.row(item))

    def save_config(self):
        cfg = {
            "hub_ip": self.hub_field.text(),
            "device_id": self.device_field.text(),
            "api_key": self.apikey_field.text(),
            "file_monitor": {
                "enabled": self.filemon_enabled.isChecked(),
                "paths": [self.paths_list.item(i).text() for i in range(self.paths_list.count())]
            },
            "network_monitor": {
                "enabled": self.network_enabled.isChecked(),
                "ports": [int(self.ports_list.item(i).text()) for i in range(self.ports_list.count())]
            }
        }

        try:
            with open(CONFIG_FILE, "w") as f:
                yaml.safe_dump(cfg, f)
            QMessageBox.information(self, "Config", f"Configuration saved to {CONFIG_FILE}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save config: {e}")

    def reload_config(self):
        self.config = self.load_config()
        self.device_field.setText(self.config.get("device_id", "agent-123"))
        self.apikey_field.setText(self.config.get("api_key", ""))

        self.filemon_enabled.setChecked(self.config.get("file_monitor", {}).get("enabled", False))
        self.paths_list.clear()
        for path in self.config.get("file_monitor", {}).get("paths", []):
            self.paths_list.addItem(path)

        self.network_enabled.setChecked(self.config.get("network_monitor", {}).get("enabled", False))
        self.ports_list.clear()
        for port in self.config.get("network_monitor", {}).get("ports", []):
            self.ports_list.addItem(str(port))

    # ===== Logs / Daemon Tab =====
    def init_logs_tab(self):
        layout = QVBoxLayout(self.logs_tab)

        # Control buttons
        control_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start Daemon")
        self.stop_btn = QPushButton("Stop Daemon")
        self.stop_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start_daemon)
        self.stop_btn.clicked.connect(self.stop_daemon)
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)

        # Logs view
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)

        layout.addLayout(control_layout)
        layout.addWidget(QLabel("Daemon Logs:"))
        layout.addWidget(self.log_view)

    # ===== Daemon Control =====
    def start_daemon(self):
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            QMessageBox.warning(self, "Warning", "Daemon already running.")
            return

        if not VENV_PYTHON.exists():
            QMessageBox.critical(self, "Error", f"Virtual environment Python not found at {VENV_PYTHON}")
            return

        self.process = QProcess(self)
        self.process.setWorkingDirectory(str(DAEMON_SCRIPT.parent))  # <- run in daemon.py folder
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.on_ready_output)
        self.process.start("pkexec", [str(VENV_PYTHON), str(DAEMON_SCRIPT)])
        
        if not self.process.waitForStarted(3000):
            QMessageBox.critical(self, "Error", "Failed to start daemon.")
            self.process = None
            return

        self.log_view.append("[INFO] Daemon started...")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def stop_daemon(self):
        if self.process:
            self.process.terminate()
            if not self.process.waitForFinished(3000):
                self.process.kill()
            self.log_view.append("[INFO] Daemon stopped.")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.process = None

    def on_ready_output(self):
        if self.process:
            data = self.process.readAllStandardOutput().data().decode("utf-8")
            self.log_view.append(data.strip())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = IDSAgentUI()
    window.show()
    sys.exit(app.exec())
