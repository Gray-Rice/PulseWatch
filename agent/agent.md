# Outline
Daemon runs as systemd service -> Userspace program monitors Daemon -> When daemon encounters event pushes it to userspace program -> userspace processes ad send JSON object to HUB

Got it ✅
You want **Person C** to focus on the **agent side**, where the daemon runs as a `systemd` service and communicates with a userspace program that handles the hub communication. Here’s the **full detailed work description for Person C**:

---
## Implement The below except JSON logic and Authentication part 

## **Person C – Agent Development (Daemon + Userspace Program)**

### **Responsibilities**

1. **Daemon Service (Background Monitoring)**

   * Implement a `systemd` service (`agent-daemon`) that:

     * Runs continuously in the background.
     * Monitors events:

       * **Network events** → detect new connections (`ss`, `netstat`, or `psutil` sockets).
       * **File events** → using `watchdog` for configured folders.
     * For each event:

       * Build a structured event payload (e.g. `{type: "network", details: {...}, timestamp: ...}`).
       * Push the event to a **userspace program** via:

         * **Local IPC** (Unix domain socket, named pipe, or ZeroMQ).

2. **Userspace Program (Event Processor + Hub Client)**

   * Runs alongside the daemon (started by the user, not systemd).
   * Responsibilities:

     * Receive events from the daemon.
     * Perform light preprocessing (add hostname, format into JSON).
     * Send JSON payload to Hub via **REST API** (endpoints defined by Person B).
     * Handle retries if hub is unavailable (basic queue or local file buffer).

3. **Configuration Management**

   * A single `config.yaml` for the agent:

     * Folders to monitor.
     * Optional network ports or filters.
     * Hub URL and TLS certificate paths.
   * Daemon should reload config on `SIGHUP` (systemd supports `ExecReload`).

4. **Packaging & Deployment**

   * Provide:

     * `agent.service` systemd unit file (for daemon).
     * CLI instructions for installing daemon (`systemctl enable --now agent.service`).
     * Simple installer script for dependencies (`pip install -r requirements.txt`).
   * Document **how to copy certificates** (provisioned manually as per Person B’s mTLS setup).

---

### **Deliverables**

1. **Daemon Implementation (`daemon.py`)**

   * Runs as systemd service.
   * Monitors:

     * File system (via `watchdog`).
     * Network connections (via `psutil.net_connections()` or `ss` wrapper).
   * Sends events to userspace over **Unix socket**.

2. **Userspace Program (`agent_client.py`)**

   * Connects to daemon’s socket.
   * Reads events, enriches them (hostname, device\_id).
   * Converts to JSON.
   * Sends to Hub’s REST endpoint (`/events`) with mTLS.

3. **Shared Library (`client_funcs.py`)**

   * Helper functions for:

     * `send_event(event_obj)` → send JSON to hub.
     * `read_config()` → parse `config.yaml`.
     * Logging wrapper.

4. **Config File (`config.yaml`)**
   Example:

   ```yaml
   hub_url: "https://hub.example.com:8443"
   cert_path: "/etc/agent/certs/agent.crt"
   key_path: "/etc/agent/certs/agent.key"
   ca_cert: "/etc/agent/certs/ca.crt"

   network_monitor:
     enabled: true
     ports: [22, 80, 443]

   file_monitor:
     enabled: true
     paths:
       - /mnt/shared
       - /var/log/shared
   ```

5. **Systemd Unit File (`agent.service`)**
   Example:

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

---

### **What Person C Can Expect Already in Place**

* **From Person B:**

  * Hub REST API endpoints (`/events`, `/devices`, `/status`) with mTLS enabled.
  * Device registration mechanism (manual provisioning).
  * DB schema ready to receive events (`events` table).
  * Certificates provisioned per device.

* **From Person A:**

  * Nothing initially (dashboard is independent, will just visualize what Person B stores).

---

### **Stretch Goals (optional, nice-to-have)**

* Implement a **local cache** so if hub is unreachable, events are stored on disk and retried later.
* Add **lightweight anomaly tagging** (e.g. >5 SSH failures in 1 min → tag as suspicious before sending).
* Provide **uninstall script** (stop service, clean configs).

---

👉 Person C’s work is **mostly endpoint agent design**, requiring skills in:

* Python system programming (daemonizing, IPC).
* Systemd service handling.
* Watchdog & psutil libraries.
* REST client with mTLS (`requests` library).

---

Would you like me to **write a minimal proof-of-concept daemon + userspace client (with Unix socket communication)** so Person C can test end-to-end with Person B’s mock `/events` API?


