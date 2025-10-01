# dashboard/main.py

import sys
import os
import time
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, current_app
from elasticsearch import Elasticsearch
from datetime import datetime, timezone
import base64, json
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

# Ensure project root importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import collector app, models, and helper
from app import create_app
from app.models import db, Device
# from user.helper import create_device
def create_device(device_id, device_name):
    """
    Generate config and certs for a new device.
    Replace this with Person B's real implementation.
    """
    config = {
        "device_id": device_id,
        "device_name": device_name,
        "hub_url": "https://hub.example.com"
    }
    certs = {
        "cert": f"-----BEGIN CERTIFICATE-----\n{device_id}-CERT\n-----END CERTIFICATE-----",
        "key": f"-----BEGIN PRIVATE KEY-----\n{device_id}-KEY\n-----END PRIVATE KEY-----"
    }
    return config, certs
# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------
# Init Elasticsearch
# -----------------------------
def init_elasticsearch():
    """Initialize Elasticsearch connection with retry logic"""
    es = Elasticsearch(
        ["http://elasticsearch:9200"],
        basic_auth=("elastic", os.getenv("ELASTIC_PASSWORD", "0Ji99IlL"))
    )
    
    for attempt in range(10):
        try:
            if es.ping():
                logger.info("Elasticsearch is ready")
                # Create indices if they don't exist
                create_indices(es)
                return es
        except Exception as e:
            logger.warning(f"Elasticsearch connection attempt {attempt + 1} failed: {e}")
        
        logger.info("Waiting for Elasticsearch...")
        time.sleep(3)
    
    raise RuntimeError("Elasticsearch not ready after 10 attempts")


def create_indices(es):
    """Create Elasticsearch indices with proper mappings if they don't exist"""
    indices = {
        "network-events": {
            "mappings": {
                "properties": {
                    "device_id": {"type": "keyword"},
                    "device_name": {"type": "text"},
                    "event_type": {"type": "keyword"},
                    "message": {"type": "text"},
                    "timestamp": {"type": "date"},
                    "source_ip": {"type": "ip"},
                    "dest_ip": {"type": "ip"},
                    "source_port": {"type": "integer"},
                    "dest_port": {"type": "integer"},
                    "protocol": {"type": "keyword"},
                    "bytes_sent": {"type": "long"},
                    "bytes_received": {"type": "long"}
                }
            }
        },
        "file-events": {
            "mappings": {
                "properties": {
                    "device_id": {"type": "keyword"},
                    "device_name": {"type": "text"},
                    "event_type": {"type": "keyword"},
                    "message": {"type": "text"},
                    "timestamp": {"type": "date"},
                    "file_path": {"type": "keyword"},
                    "file_name": {"type": "text"},
                    "file_size": {"type": "long"},
                    "file_hash": {"type": "keyword"},
                    "action": {"type": "keyword"},
                    "user": {"type": "keyword"}
                }
            }
        }
    }
    
    for index_name, mapping in indices.items():
        try:
            if not es.indices.exists(index=index_name):
                es.indices.create(index=index_name, body=mapping)
                logger.info(f"Created index '{index_name}' with proper mapping")
            else:
                logger.info(f"Index '{index_name}' already exists")
        except Exception as e:
            logger.error(f"Failed to create index '{index_name}': {e}")


# -----------------------------
# Event decryption helper
# -----------------------------
def decrypt_payload(api_key, encrypted_payload):
    """Decrypt the encrypted payload using the device's API key"""
    try:
        # Decode the API key from base64
        key = base64.urlsafe_b64decode(api_key)
        aesgcm = AESGCM(key)
        
        # Decode the encrypted payload
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_payload)
        nonce = encrypted_bytes[:12]
        ciphertext = encrypted_bytes[12:]
        
        # Decrypt and parse
        decrypted = aesgcm.decrypt(nonce, ciphertext, None)
        return json.loads(decrypted)
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise


def generate_api_key():
    """Generate a new API key for device encryption"""
    key = AESGCM.generate_key(bit_length=256)
    return base64.urlsafe_b64encode(key).decode('utf-8')


# -----------------------------
# Init Dashboard (extends collector app)
# -----------------------------
def create_dashboard_app():
    base_dir = os.path.dirname(__file__)
    app = create_app(template_folder=os.path.join(base_dir, "templates"))
    app.secret_key = os.getenv("DASHBOARD_SECRET", "supersecret")

    # Initialize database
    with app.app_context():
        db.create_all()

    # Initialize and attach Elasticsearch
    es = init_elasticsearch()
    app.elasticsearch = es

    # -----------------------------
    # Dashboard Routes
    # -----------------------------
    @app.route("/")
    def index():
        """Dashboard home page"""
        try:
            device_count = Device.query.count()
            
            # Get recent events count from Elasticsearch
            recent_network_events = 0
            recent_file_events = 0
            
            try:
                # Count events from last 24 hours
                query = {
                    "query": {
                        "range": {
                            "timestamp": {
                                "gte": "now-24h"
                            }
                        }
                    }
                }
                
                network_res = es.search(index="network-events", body=query, size=0)
                recent_network_events = network_res["hits"]["total"]["value"]
                
                file_res = es.search(index="file-events", body=query, size=0)
                recent_file_events = file_res["hits"]["total"]["value"]
                
            except Exception as e:
                logger.warning(f"Failed to get event counts: {e}")
            
            return render_template("index.html", 
                                 device_count=device_count,
                                 recent_network_events=recent_network_events,
                                 recent_file_events=recent_file_events)
        except Exception as e:
            logger.error(f"Error loading dashboard: {e}")
            flash("Error loading dashboard data", "error")
            return render_template("index.html")

    # --- Device Management ---
    @app.route("/devices")
    def devices():
        """List all devices"""
        try:
            devices_list = Device.query.all()
            return render_template("devices.html", devices=devices_list)
        except Exception as e:
            logger.error(f"Error loading devices: {e}")
            flash("Error loading devices", "error")
            return render_template("devices.html", devices=[])

    @app.route("/devices/add", methods=["POST"])
    def add_device_route():
        """Add a new device"""
        device_name = request.form.get("device_name", "").strip()
        device_id = request.form.get("device_id", "").strip()

        if not device_name or not device_id:
            flash("Device name and ID are required", "error")
            return redirect(url_for("devices"))

        # Check if device already exists
        existing_device = Device.query.filter_by(device_id=device_id).first()
        if existing_device:
            flash(f"Device with ID '{device_id}' already exists", "error")
            return redirect(url_for("devices"))

        try:
            # Generate proper API key for encryption
            api_key = generate_api_key()
            
            # Create device configuration and certificates
            config, certs = create_device(device_id, device_name)

            # Save device to database
            new_device = Device(device_id=device_id, name=device_name, api_key=api_key)
            db.session.add(new_device)
            db.session.commit()

            flash(f"Device '{device_name}' added successfully!", "success")
            logger.info(f"Added new device: {device_id} ({device_name})")
            
            return render_template(
                "devices.html",
                devices=Device.query.all(),
                config=config,
                certs=certs,
                new_device_api_key=api_key
            )
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding device: {e}")
            flash(f"Error adding device: {str(e)}", "error")
            return redirect(url_for("devices"))

    @app.route("/devices/delete/<device_id>", methods=["POST"])
    def delete_device_route(device_id):
        """Delete a device"""
        try:
            device = Device.query.filter_by(device_id=device_id).first()
            if device:
                device_name = device.name
                db.session.delete(device)
                db.session.commit()
                flash(f"Device '{device_name}' deleted successfully", "success")
                logger.info(f"Deleted device: {device_id} ({device_name})")
            else:
                flash("Device not found", "error")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting device: {e}")
            flash(f"Error deleting device: {str(e)}", "error")
        
        return redirect(url_for("devices"))

    # --- Event Ingestion (from agents) ---
    @app.route("/events", methods=["POST"])
    def receive_event():
        """Receive and process events from agents"""
        try:
            encrypted_payload = request.get_data(as_text=True)
            device_id = request.headers.get("X-Device-ID")

            if not device_id:
                return jsonify({"error": "Missing X-Device-ID header"}), 400

            if not encrypted_payload:
                return jsonify({"error": "Empty payload"}), 400

            # Find device in database
            device = Device.query.filter_by(device_id=device_id).first()
            if not device:
                logger.warning(f"Event received from unknown device: {device_id}")
                return jsonify({"error": "Unknown device"}), 401

            # Decrypt the payload
            try:
                payload = decrypt_payload(device.api_key, encrypted_payload)
            except Exception as e:
                logger.error(f"Decryption failed for device {device_id}: {e}")
                return jsonify({"error": "Decryption failed"}), 400

            # Add metadata
            payload["device_id"] = device_id
            payload["device_name"] = device.name
            payload["timestamp"] = datetime.now(timezone.utc).isoformat()

            # Validate and index event
            event_type = payload.get("event_type")
            if event_type == "network":
                es.index(index="network-events", document=payload)
                logger.info(f"Indexed network event from device {device_id}")
            elif event_type == "file":
                es.index(index="file-events", document=payload)
                logger.info(f"Indexed file event from device {device_id}")
            else:
                return jsonify({"error": f"Invalid event_type: {event_type}"}), 400

            return jsonify({"status": "success", "message": "Event processed"}), 201

        except Exception as e:
            logger.error(f"Error processing event: {e}")
            return jsonify({"error": "Internal server error"}), 500

    @app.route("/devices/<device_id>/events")
    def device_events(device_id):
        """Get events for a specific device"""
        try:
            # Verify device exists
            device = Device.query.filter_by(device_id=device_id).first()
            if not device:
                return jsonify({"error": "Device not found"}), 404

            # Get query parameters
            event_type = request.args.get('type', 'network')  # default to network events
            limit = min(int(request.args.get('limit', 100)), 1000)  # max 1000 events
            
            # Determine index based on event type
            if event_type == 'network':
                index_name = "network-events"
            elif event_type == 'file':
                index_name = "file-events"
            else:
                return jsonify({"error": "Invalid event type"}), 400

            # Elasticsearch query
            query_body = {
                "query": {"match": {"device_id": device_id}},
                "size": limit,
                "sort": [{"timestamp": {"order": "desc"}}]
            }

            # Execute search
            res = es.search(index=index_name, body=query_body)
            events_list = [hit["_source"] for hit in res["hits"]["hits"]]
            
            return jsonify({
                "device_id": device_id,
                "device_name": device.name,
                "event_type": event_type,
                "total_events": res["hits"]["total"]["value"],
                "events": events_list
            })

        except Exception as e:
            logger.error(f"Error retrieving events for device {device_id}: {e}")
            return jsonify({"error": "Failed to retrieve events"}), 500

    @app.route("/events/search")
    def search_events():
        """Search events across all devices"""
        try:
            # Get query parameters
            query_text = request.args.get('q', '')
            event_type = request.args.get('type', 'both')
            device_id = request.args.get('device_id', '')
            limit = min(int(request.args.get('limit', 100)), 1000)
            
            # Build Elasticsearch query
            must_clauses = []
            
            if query_text:
                must_clauses.append({
                    "multi_match": {
                        "query": query_text,
                        "fields": ["message", "file_path", "file_name"]
                    }
                })
            
            if device_id:
                must_clauses.append({"match": {"device_id": device_id}})
            
            if not must_clauses:
                must_clauses.append({"match_all": {}})
            
            query_body = {
                "query": {"bool": {"must": must_clauses}},
                "size": limit,
                "sort": [{"timestamp": {"order": "desc"}}]
            }
            
            # Search appropriate indices
            indices = []
            if event_type in ['network', 'both']:
                indices.append('network-events')
            if event_type in ['file', 'both']:
                indices.append('file-events')
            
            res = es.search(index=','.join(indices), body=query_body)
            events_list = [hit["_source"] for hit in res["hits"]["hits"]]
            
            return jsonify({
                "query": query_text,
                "event_type": event_type,
                "total_results": res["hits"]["total"]["value"],
                "events": events_list
            })
            
        except Exception as e:
            logger.error(f"Error searching events: {e}")
            return jsonify({"error": "Search failed"}), 500

    # --- Kibana Embeds ---
    @app.route("/kibana/<dashboard_name>")
    def kibana(dashboard_name):
        """Embed Kibana dashboard"""
        kibana_url = f"http://localhost:5601/app/dashboards#/view/{dashboard_name}"
        return render_template("kibana.html", 
                             kibana_url=kibana_url,
                             dashboard_name=dashboard_name)

    # --- Health Check ---
    @app.route("/health")
    def health_check():
        """Health check endpoint"""
        try:
            # Check database
            db.session.execute('SELECT 1')
            
            # Check Elasticsearch
            es.ping()
            
            return jsonify({
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "services": {
                    "database": "ok",
                    "elasticsearch": "ok"
                }
            })
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return jsonify({
                "status": "unhealthy",
                "error": str(e)
            }), 503

    return app


# -----------------------------
# Run App
# -----------------------------
if __name__ == "__main__":
    app = create_dashboard_app()
    logger.info("Starting dashboard application...")
    app.run(host="0.0.0.0", port=5000, debug=os.getenv("DEBUG", "False").lower() == "true")