from flask import Blueprint, request, jsonify
from app.models import db, Device, NetworkEvent, FileEvent
from datetime import datetime

events_bp = Blueprint("events", __name__)

@events_bp.route("/", methods=["POST"])
def receive_event():
    data = request.get_json()
    device_id = data.get("device_id")
    event_type = data.get("event_type")

    # Validate device
    device = Device.query.filter_by(device_id=device_id).first()
    if not device:
        return jsonify({"error": "Unknown device"}), 400

    if event_type == "network":
        event = NetworkEvent(
            device_id=device_id,
            direction=data.get("direction"),
            ip=data.get("ip"),
            port=data.get("port"),
            action=data.get("action"),
            rating=data.get("rating", 0),
            extra=data.get("extra"),
            timestamp=datetime.utcnow()
        )
    elif event_type == "file":
        event = FileEvent(
            device_id=device_id,
            file_path=data.get("file_path"),
            action=data.get("action"),
            rating=data.get("rating", 0),
            extra=data.get("extra"),
            timestamp=datetime.utcnow()
        )
    else:
        return jsonify({"error": "Invalid event_type"}), 400

    db.session.add(event)
    db.session.commit()

    return jsonify({"status": "success"}), 201
