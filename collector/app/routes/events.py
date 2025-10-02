# app/routes/events.py

from flask import Blueprint, request, jsonify, current_app
from app.models import Device
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64, json
from datetime import datetime, timezone
from elasticsearch import Elasticsearch, exceptions as es_exceptions

events_bp = Blueprint("events", __name__)

def decrypt_payload(api_key, encrypted_payload):
    """
    Decrypt AES-GCM payload using device API key.
    `encrypted_payload` should be base64 URL-safe encoded.
    """
    try:
        key = base64.urlsafe_b64decode(api_key)
        aesgcm = AESGCM(key)
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_payload)
        nonce = encrypted_bytes[:12]
        ct = encrypted_bytes[12:]
        decrypted = aesgcm.decrypt(nonce, ct, None)
        return json.loads(decrypted)
    except Exception as e:
        raise ValueError(f"Decryption failed: {e}")

@events_bp.route("/", methods=["POST"])
def receive_event():
    """
    Receive encrypted event payloads from agents.
    Headers:
        X-Device-ID : ID of the device
    Body:
        raw encrypted payload (AES-GCM, base64)
    """
    encrypted_payload = request.get_data(as_text=True)
    device_id = request.headers.get("X-Device-ID")
    if not device_id:
        return jsonify({"error": "Missing X-Device-ID header"}), 400

    # Validate device in Postgres
    device = Device.query.filter_by(device_id=device_id).first()
    if not device:
        return jsonify({"error": "Unknown device"}), 400

    # Decrypt payload
    try:
        payload = decrypt_payload(device.api_key, encrypted_payload)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    # Add metadata
    payload["device_id"] = device_id
    payload["device_name"] = device.name
    payload["timestamp"] = datetime.now(timezone.utc).isoformat()

    # Index to Elasticsearch
    es: Elasticsearch = current_app.elasticsearch
    index_map = {
        "file": "file-events",
        "network": "network-events"
    }
    event_type = payload.get("event_type")
    index_name = index_map.get(event_type)

    if not index_name:
        return jsonify({"error": "Invalid event_type"}), 400

    try:
        res = es.index(index=index_name, document=payload)
    except es_exceptions.AuthenticationException:
        return jsonify({"error": "Elasticsearch authentication failed"}), 500
    except es_exceptions.ConnectionError:
        return jsonify({"error": "Cannot connect to Elasticsearch"}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to index event: {e}"}), 500

    return jsonify({"status": "success", "es_result": res.get("result")}), 201
