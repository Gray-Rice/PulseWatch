from flask import Blueprint, request, jsonify
from app.models import db, Device, NetworkEvent, FileEvent
from datetime import datetime
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64, json

events_bp = Blueprint("events", __name__)

def decrypt_payload(api_key, encrypted_payload):
    """
    Decrypt payload using AES-GCM with the device's API key.
    Expects encrypted_payload as URL-safe base64 string.
    """
    key = base64.urlsafe_b64decode(api_key)
    aesgcm = AESGCM(key)
    encrypted_bytes = base64.urlsafe_b64decode(encrypted_payload)
    nonce = encrypted_bytes[:12]
    ct = encrypted_bytes[12:]
    decrypted = aesgcm.decrypt(nonce, ct, None)
    return json.loads(decrypted)

@events_bp.route("/", methods=["POST"])
def receive_event():
    encrypted_payload = request.get_data(as_text=True)  # raw body
    device_id = request.headers.get("X-Device-ID")
    
    if not device_id:
        return jsonify({"error": "Missing X-Device-ID header"}), 400

    device = Device.query.filter_by(device_id=device_id).first()
    if not device:
        return jsonify({"error": "Unknown device"}), 400

    try:
        payload = decrypt_payload(device.api_key, encrypted_payload)
    except Exception as e:
        return jsonify({"error": "Decryption failed", "details": str(e)}), 400

    event_type = payload.get("event_type")
    if event_type == "network":
        event = NetworkEvent(
            device_id=device_id,
            direction=payload.get("direction"),
            ip=payload.get("ip"),
            port=payload.get("port"),
            action=payload.get("action"),
            rating=payload.get("rating", 0),
            extra=payload.get("extra"),
            timestamp=datetime.utcnow()
        )
    elif event_type == "file":
        event = FileEvent(
            device_id=device_id,
            file_path=payload.get("file_path"),
            action=payload.get("action"),
            rating=payload.get("rating", 0),
            extra=payload.get("extra"),
            timestamp=datetime.utcnow()
        )
    else:
        return jsonify({"error": "Invalid event_type"}), 400

    db.session.add(event)
    db.session.commit()

    return jsonify({"status": "success"}), 201
