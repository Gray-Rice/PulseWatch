# **Workflow for Person A (Dashboard & Device Management)**

## 🎯 Responsibilities

* Provide a **visual dashboard** (Kibana) to search, filter, and view IDS events.
* Expose a simple **device management UI** (add/remove devices).
* Call helper functions from **Person B’s module** for provisioning when a device is added.

---

## 🔄 Workflow

### **1. Setup & Integration**

* Install **Elasticsearch + Kibana**.
* Ensure Person B’s server is already writing events into the `events` index in Elasticsearch (or PostgreSQL + Elasticsearch sync if you want).
* Connect Kibana to the DB / Elasticsearch.

---

### **2. Event Visualization in Kibana**

* **Events Index Setup**:

  * Index pattern: `events-*`.
  * Each document = one event JSON sent from an agent.
  * Example JSON in DB/Elasticsearch:

    ```json
    {
      "device_id": "agent-123",
      "type": "network",
      "details": {
        "src_ip": "1.1.1.1",
        "dst_port": 22,
        "timestamp": "2025-09-13T12:34:56Z"
      },
      "received_at": "2025-09-13T12:35:00Z"
    }
    ```

* **Dashboards**:

  * Tab **Per Device Logs** → Filter by `device_id`.
  * Tab **Network Events** → Visualize by source IP / port over time.
  * Tab **File Events** → Show modified / deleted file counts over time.
  * Tab **Suspicious Events** → Highlight anomalies flagged by Person B.

* **Search/Filter**:

  * Allow query like: `device_id:agent-123 AND type:network AND details.dst_port:22`.

---

### **3. Device Management Page**

* Create a **custom plugin or lightweight web frontend** alongside Kibana (since Kibana isn’t ideal for CRUD).
* This page has:

  * Input: `device_name`, `device_id`.
  * Button → “Add Device”.
* When clicked:

  * Calls `device_helper.create_device(device_id, device_name)` (from Person B’s helper module).
  * This generates config & certificates (Person B’s responsibility).
  * UI then shows the generated config/certs for download.

---

### **4. Workflow (End-to-End)**

1. **Device joins**:

   * Admin opens Dashboard → *Add Device*.
   * Calls Person B’s helper → generates config (`config.yaml`) + certs.
   * Admin downloads and installs on new agent (Person C’s daemon).
2. **Events stream in**:

   * Agent sends events → Person B’s hub stores them in DB/Elasticsearch.
   * Person A’s Kibana dashboards update in real-time.
3. **Analysis**:

   * Admin uses Kibana to filter/search suspicious events.
   * Device status can be visualized in a simple “online/offline” panel (based on Person B’s heartbeats).

---

## ✅ Deliverables for Person A

1. **Kibana Dashboards**:

   * Network events.
   * File events.
   * Suspicious/anomaly flagged events.
   * Per device event explorer.
2. **Custom Device Management Page**:

   * Web UI (simple Flask/FastAPI app or Kibana plugin).
   * Uses helper from Person B’s `device_helper.py`.
   * Can: Add device, remove device.
3. **Docs for Workflow**:

   * How to use dashboard.
   * How to add/remove devices.

---

👉 This workflow makes Person A’s role mostly **visualization + lightweight frontend**, while keeping all auth/provisioning in **Person B’s helper functions**.

