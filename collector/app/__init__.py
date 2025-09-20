from flask import Flask
from app.models import db
from app.routes.events import events_bp
from app.routes.devices import devices_bp
import os

def create_app(config_path="config.yaml"):
    app = Flask(__name__)
    
    # Load config
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
            "DATABASE_URL", "postgresql://ids_user:ids_pass@localhost:5432/ids_db"
        )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    db.init_app(app)
    
    # Register blueprints
    app.register_blueprint(events_bp, url_prefix="/api/events")
    app.register_blueprint(devices_bp, url_prefix="/api/devices")
    
    return app
