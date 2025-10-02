import sys
import os
import time
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, g, current_app
from elasticsearch import Elasticsearch
from datetime import datetime, timezone
import base64, json
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import requests
from functools import wraps

# Ensure project root importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import collector app, models
from app import create_app
from app.models import db, Device

# -----------------------------
# JWT CONFIG
# -----------------------------
import jwt
JWT_SECRET = os.getenv("DASHBOARD_JWT_SECRET", "supersecretjwt")
JWT_ALGORITHM = "HS256"
JWT_EXP_SECONDS = 3600  # 1 hour

def generate_jwt(payload: dict) -> str:
    import time
    payload_copy = payload.copy()
    payload_copy["exp"] = time.time() + JWT_EXP_SECONDS
    token = jwt.encode(payload_copy, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token

def decode_jwt(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = session.get("jwt_token") or request.cookies.get("jwt_token")
        if not token:
            flash("Authentication required", "error")
            return redirect(url_for("login"))
        try:
            g.user = decode_jwt(token)
        except jwt.ExpiredSignatureError:
            flash("Session expired, please login again", "error")
            return redirect(url_for("login"))
        except jwt.InvalidTokenError:
            flash("Invalid token, please login again", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# -----------------------------
# DEVICE CONFIG HELPER
# -----------------------------
def create_device(device_id, device_name):
    config = {
        "device_id": device_id,
        "device_name": device_name,
        "hub_url": "https://hub.example.com"
    }
    certs = {
        "cert": f"-----BEGIN CERTIFICATE-----\n{device_id}-CERT\n-----END CERTIFICATE-----",
        "key": f"-----BEGIN PRIVATE KEY-----\n{device_id}-KEY\n-----END PRIVATE KEY-----"
    }
    return config, certs

def add_device_via_api(device_id, device_name):
    url = "http://127.0.0.1:5000/api/devices/"
    headers = {
        "X-Internal-Auth": os.getenv("INTERNAL_SECRET", "super-secret-token"),
        "Content-Type": "application/json"
    }
    payload = {"device_id": device_id, "name": device_name}
    resp = requests.post(url, json=payload, headers=headers)
    if resp.status_code == 201:
        return resp.json()
    else:
        raise RuntimeError(f"Failed to add device via API: {resp.text}")

# -----------------------------
# DASHBOARD APP
# -----------------------------
def create_dashboard_app():
    base_dir = os.path.dirname(__file__)
    app = create_app(template_folder=os.path.join(base_dir, "templates"))
    app.secret_key = os.getenv("DASHBOARD_SECRET", "supersecret")

    # Setup logging
    logging.basicConfig(level=logging.INFO)
    app.logger.setLevel(logging.INFO)

    with app.app_context():
        try:
            db.create_all()
            app.logger.info("Database initialized")
        except Exception as e:
            app.logger.error(f"Error initializing DB: {e}", exc_info=True)

    # -----------------------------
    # Error Handling
    # -----------------------------
    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.error(f"Unhandled exception: {e}", exc_info=True)
        return "Internal Server Error", 500

    # -----------------------------
    # LOGIN / LOGOUT
    # -----------------------------
    @app.route("/", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")
            if username == "admin" and password == os.getenv("DASHBOARD_PASSWORD", "admin"):
                token = generate_jwt({"username": username})
                session["jwt_token"] = token
                flash("Logged in successfully", "success")
                return redirect(url_for("devices"))
            else:
                flash("Invalid username or password", "error")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.pop("jwt_token", None)
        flash("Logged out", "success")
        return redirect(url_for("login"))

    # -----------------------------
    # DEVICES
    # -----------------------------
    @app.route("/devices")
    @jwt_required
    def devices():
        try:
            devices_list = Device.query.all()
            return render_template("devices.html", devices=devices_list)
        except Exception as e:
            app.logger.error(f"Error fetching devices: {e}", exc_info=True)
            flash("Failed to load devices", "error")
            return render_template("devices.html", devices=[])

    @app.route("/devices/add", methods=["POST"])
    @jwt_required
    def add_device_route():
        device_name = request.form.get("device_name", "").strip()
        device_id = request.form.get("device_id", "").strip()
        if not device_name or not device_id:
            flash("Device name and ID required", "error")
            return redirect(url_for("devices"))
        try:
            existing = Device.query.filter_by(device_id=device_id).first()
            if existing:
                flash(f"Device '{device_id}' exists", "error")
                return redirect(url_for("devices"))

            info = add_device_via_api(device_id, device_name)
            api_key = info["api_key"]
            config, certs = create_device(device_id, device_name)

            new_device = Device(device_id=device_id, name=device_name, api_key=api_key)
            db.session.add(new_device)
            db.session.commit()

            flash(f"Device '{device_name}' added!", "success")
            return render_template("devices.html", devices=Device.query.all(),
                                   config=config, certs=certs, new_device_api_key=api_key)
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error adding device: {e}", exc_info=True)
            flash(str(e), "error")
            return redirect(url_for("devices"))

    @app.route("/devices/delete/<device_id>", methods=["POST"])
    @jwt_required
    def delete_device_route(device_id):
        try:
            device = Device.query.filter_by(device_id=device_id).first()
            if device:
                db.session.delete(device)
                db.session.commit()
                flash(f"Device '{device.name}' deleted", "success")
            else:
                flash("Device not found", "error")
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error deleting device: {e}", exc_info=True)
            flash("Error deleting device", "error")
        return redirect(url_for("devices"))

    return app

# -----------------------------
# RUN APP
# -----------------------------
if __name__ == "__main__":
    app = create_dashboard_app()
    logging.info("Starting dashboard application...")
    app.run(host="0.0.0.0", port=5001, debug=True)
