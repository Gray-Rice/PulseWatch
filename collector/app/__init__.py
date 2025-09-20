from flask import Flask
from app.models import db
from app.routes.events import events_bp
from app.routes.devices import devices_bp
import yaml

def create_app(config_path="config.yaml"):
    app = Flask(__name__)
    
    # Load config
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)
    app.config["SQLALCHEMY_DATABASE_URI"] = cfg["database"]["uri"]
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    db.init_app(app)
    
    # Register blueprints
    app.register_blueprint(events_bp, url_prefix="/api/events")
    app.register_blueprint(devices_bp, url_prefix="/api/devices")
    
    return app
