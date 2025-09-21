# app/__init__.py

from flask import Flask
from app.models import db
from app.routes.events import events_bp
from app.routes.devices import devices_bp
from elasticsearch import Elasticsearch
import os

def create_app(config_path=None):
    app = Flask(__name__)

    # -----------------------------
    # Postgres config for devices
    # -----------------------------
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "postgresql://ids_user:ids_pass@localhost:5432/ids_db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Initialize SQLAlchemy
    db.init_app(app)

    # -----------------------------
    # Elasticsearch config for events
    # -----------------------------
    es_host = os.getenv("ES_HOST", "http://localhost:9200")
    es_user = os.getenv("ES_USER", "elastic")
    es_pass = os.getenv("ES_PASS", "changeme")

    app.elasticsearch = Elasticsearch(
        hosts=[es_host],
        basic_auth=(es_user, es_pass)
    )

    # -----------------------------
    # Register Blueprints
    # -----------------------------
    app.register_blueprint(events_bp, url_prefix="/api/events")
    app.register_blueprint(devices_bp, url_prefix="/api/devices")

    return app
