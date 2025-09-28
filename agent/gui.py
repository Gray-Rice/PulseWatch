import sys
import yaml
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QLineEdit, QFormLayout,
    QMessageBox, QListWidget, QCheckBox, QFileDialog
)
from PyQt6.QtCore import QProcess


SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "agent.yaml"
DAEMON_SCRIPT = SCRIPT_DIR / "daemon.py"


class IDSAgentUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IDS Agent Control")
        self.resize(700, 600)
        self.process: QProcess | None = None
        self.config = self.load_config()

        main_layout = QVBoxLayout(self)

        # ===== Config Section =====
        form_layout = QFormLayout()

        self.device_field = QLineEdit(self.config.get("device_id", "agent-123"))
        self.apikey_field = QLineEdit(self.config.get("api_key", ""))
        self.apikey_field.setEchoMode(QLineEdit.EchoMode.Password)

        self.filemon_enabled = QCheckBox("Enable File Monitor")
        self.filemon_enabled.setChecked(self.config.get("file_monitor", {}).get("enabled", False))

        self.network_enabled = QCheckBox("Enable Network Monitor")
        self.network_enabled.setChecked(self.config.get("network_monitor", {}).get("enabled", False))

        # File paths list
        self.paths_list = QListWidget()
        for path in self.config.get("file_monitor", {}).get("paths", []):
            self.paths_list.addItem(path)

        # Buttons to add/remove paths
        path_btn_layout = QHBoxLayout()
        add_path_btn = QPushButton("Add Path")
        add_path_btn.clicked.connect(self.add_path)
        remove_path_btn = QPushButton("Remove Selected")
        remove_path_btn.clicked.connect(self.remove_path)
        path_btn_layout.addWidget(add_path_btn)
        path_btn_layout.addWidget(remove_path_btn)

        # Assemble form
        form_layout.addRow("Device ID:", self.device_field)
        form_layout.addRow("API Key:", self.apikey_field)
        form_layout.addRow(self.filemon_enabled)
        form_layout.addRow(self.network_enabled)
        form_layout.addRow(QLabel("File Monitor Paths:"), self.paths_list)
        form_layout.addRow(path_btn_layout)

        save_btn = QPushButton("Save Config")
        save_btn.clicked.connect(self.save_config)

        # ===== Control Section =====
        control_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start Daemon")
        self.stop_btn = QPushButton("Stop Daemon")
        self.stop_btn.setEnabled(False)

        self.start_btn.clicked.connect(self.start_daemon)
        self.stop_btn.clicked.connect(self.stop_daemon)

        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)

        # ===== Logs Section =====
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)

        # ===== Add all to main layout =====
        main_layout.addLayout(form_layout)
        main_layout.addWidget(save_btn)
        main_layout.addLayout(control_layout)
        main_layout.addWidget(QLabel("Daemon Logs:"))
        main_layout.addWidget(self.log_view)

    # ===== Config Methods =====
    def load_config(self):
        if CONFIG_FILE.exists():
            try:
                return yaml.safe_load(CONFIG_FILE)
            except Exception:
                return {}
        return {}

    def save_config(self):
        cfg = {
            "device_id": self.device_field.text(),
            "api_key": self.apikey_field.text(),
            "file_monitor": {
                "enabled": self.filemon_enabled.isChecked(),
                "paths": [self.paths_list.item(i).text() for i in range(self.paths_list.count())]
            },
            "network_monitor": {
                "enabled": self.network_enabled.isChecked()
            }
        }

        try:
            with open(CONFIG_FILE, "w") as f:
                yaml.safe_dump(cfg, f)
            QMessageBox.information(self, "Config", f"Configuration saved to {CONFIG_FILE}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save config: {e}")

    def add_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if path:
            self.paths_list.addItem(path)

    def remove_path(self):
        for item in self.paths_list.selectedItems():
            self.paths_list.takeItem(self.paths_list.row(item))

    # ===== Daemon Control =====
    def start_daemon(self):
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            QMessageBox.warning(self, "Warning", "Daemon already running.")
            return

        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.on_ready_output)

        # Use pkexec for polkit elevation
        self.process.start("pkexec", ["python3", str(DAEMON_SCRIPT)])
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
