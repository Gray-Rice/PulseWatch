from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# -------------------
# Device Table
# -------------------
class Device(db.Model):
    __tablename__ = "devices"
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100))
    status = db.Column(db.String(20), default="offline")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# -------------------
# Network Events Table
# -------------------
class NetworkEvent(db.Model):
    __tablename__ = "network_events"
    id = db.Column(db.Integer, primary_key=True)

    device_id = db.Column(
        db.String(50),
        db.ForeignKey("devices.device_id"),
        nullable=False
    )

    direction = db.Column(db.String(10))   # ingress / egress
    ip = db.Column(db.String(45))          # IPv4/IPv6
    port = db.Column(db.Integer)
    action = db.Column(db.String(50))      # connect / disconnect / attempt
    rating = db.Column(db.Integer, default=0)  # 0=low, 1=medium, 2=high
    extra = db.Column(db.JSON)             # flexible metadata

    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# -------------------
# File Events Table
# -------------------
class FileEvent(db.Model):
    __tablename__ = "file_events"
    id = db.Column(db.Integer, primary_key=True)

    device_id = db.Column(
        db.String(50),
        db.ForeignKey("devices.device_id"),
        nullable=False
    )

    file_path = db.Column(db.Text, nullable=False)
    action = db.Column(db.String(50))      # create / read / modify / delete
    rating = db.Column(db.Integer, default=0)  # 0=low, 1=medium, 2=high
    extra = db.Column(db.JSON)             # flexible metadata

    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
