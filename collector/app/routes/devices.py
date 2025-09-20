from flask import Blueprint, request, jsonify
from app.models import db, Device

devices_bp = Blueprint("devices", __name__)

@devices_bp.route("/", methods=["POST"])
def add_device():
    data = request.get_json()
    device_id = data.get("device_id")
    name = data.get("name", "Unnamed Device")
    
    if Device.query.filter_by(device_id=device_id).first():
        return jsonify({"error": "Device already exists"}), 400
    
    device = Device(device_id=device_id, name=name)
    db.session.add(device)
    db.session.commit()
    
    # Person B: here we can call helper to create YAML + certs
    return jsonify({"status": "device added"}), 201
