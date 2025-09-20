# Outline
Daemon runs as systemd service -> Userspace program monitors Daemon -> When daemon encounters event pushes it to userspace program -> userspace processes ad send JSON object to HUB


# **Person C – Agent Development (Daemon + Event Collection Only)**

## 🎯 **Responsibilities**

1. **Agent Daemon (systemd Service)**

   * Runs in background as `systemd` service.
   * Monitors **event sources**:

     * **Network connections** (e.g. new socket connect events).
     * **File system changes** (via `watchdog`, configurable folders).
   * For each event, builds a **JSON object**:

     ```json
     {
       "device_id": "agent-123",
       "type": "network",
       "details": {
         "src_ip": "1.1.1.1",
         "dst_port": 22,
         "timestamp": "2025-09-13T12:34:56Z"
       }
     }
     ```
   * Calls a **dummy helper function** (imported from Person B’s module) to “send” the JSON.

     * For now → just prints/logs the JSON.
     * Later → Person B will implement actual **mTLS + REST POST** in that helper.

2. **Event Flow**

   * Event occurs → Daemon captures → Formats JSON → Calls `hub_client.send_event(event_json)` (dummy).
   * This means **no networking, no TLS, no retries** in C’s code.

3. **Configuration Management**

   * Agent reads `config.yaml` for:

     * Folders to monitor.
     * Ports to watch.
     * Device ID.
   * Daemon should reload config on restart (systemd handles service restart).

---

## 📦 **Deliverables**

### 1. **Daemon Service (`daemon.py`)**

* Monitors:

  * File system paths (using `watchdog` observers).
  * Network connections (polling via `psutil` or `ss` wrapper).
* Formats events into JSON dicts.
* Calls:

  ```python
  from hub_client import send_event

  send_event(event_json)
  ```

### 2. **Dummy Helper Module (`hub_client.py`)**

* Exposes placeholder functions for Person B to later implement:

  ```python
  def send_event(event_json: dict):
      # Dummy implementation
      print("[DEBUG] Event ready to send:", event_json)
  ```

### 3. **Config File (`config.yaml`)**

Example:

```yaml
device_id: "agent-123"

network_monitor:
  enabled: true
  ports: [22, 80]

file_monitor:
  enabled: true
  paths:
    - /mnt/shared
    - /var/log/shared
```

### 4. **Systemd Unit File (`agent.service`)**

```ini
[Unit]
Description=IDS Agent Daemon
After=network.target

[Service]
ExecStart=/usr/bin/python3 /opt/agent/daemon.py
Restart=always
User=root
WorkingDirectory=/opt/agent
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
```

### 5. **Logging**

* Log to syslog (`systemd` captures).
* Events that fail JSON formatting → log as warnings.

---

## ✅ **What Person C Can Expect Already in Place**

* **From Person B:**

  * Eventually, `hub_client.send_event()` will be fully implemented (mTLS + REST).
  * Certificates & provisioning mechanism will be handled externally.
* **From Person A:**

  * Nothing needed (dashboard consumes DB later).

---

## ⚡ **Stretch Goals for C**

* Add basic **rate limiting** (avoid flooding with identical events).
* Implement **light enrichment** (e.g. reverse DNS lookup for IPs).
* Add **local file cache** to save JSONs if helper is unavailable (optional, Person B might prefer to own retries).

---

👉 This way Person C’s daemon is **fully testable right now** (prints JSON), and later Person B just **drops in the real `hub_client.py`** without any rewrite.

Would you like me to sketch a **minimal working prototype of `daemon.py` + dummy `hub_client.py`** so Person C can run it right away?
