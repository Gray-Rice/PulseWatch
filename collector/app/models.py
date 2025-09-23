from flask_sqlalchemy import SQLAlchemy
from datetime import datetime , timezone

db = SQLAlchemy()

class Device(db.Model):
    __tablename__ = "devices"
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100))
    status = db.Column(db.String(20), default="offline")
    api_key = db.Column(db.String(100), unique=True, nullable=False)  # for auth
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
