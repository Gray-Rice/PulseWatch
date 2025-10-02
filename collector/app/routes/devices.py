from flask import Blueprint, request, jsonify
from app.models import db, Device
import secrets
import base64
import os

devices_bp = Blueprint("devices", __name__)

# Load secret from environment or config file
INTERNAL_SECRET = os.getenv("INTERNAL_SECRET", "super-secret-token")

def generate_api_key():
    """
    Generate a 256-bit (32-byte) random API key, encoded in URL-safe base64.
    """
    key = secrets.token_bytes(32)
    return base64.urlsafe_b64encode(key).decode('utf-8')

@devices_bp.route("/", methods=["POST"])
def add_device():
    # Secret check
    auth = request.headers.get("X-Internal-Auth")
    if auth != INTERNAL_SECRET:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    device_id = data.get("device_id")
    name = data.get("name", "Unnamed Device")
    
    if not device_id:
        return jsonify({"error": "device_id is required"}), 400

    if Device.query.filter_by(device_id=device_id).first():
        return jsonify({"error": "Device already exists"}), 400
    
    # Generate unique API key for this device
    api_key = generate_api_key()
    
    device = Device(device_id=device_id, name=name, api_key=api_key)
    db.session.add(device)
    db.session.commit()
    
    return jsonify({
        "status": "device added",
        "device_id": device_id,
        "name": device.name,
        "api_key": api_key
    }), 200
