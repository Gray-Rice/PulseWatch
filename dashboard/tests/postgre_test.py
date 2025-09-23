import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../collector')))

from app import create_app
from app.models import db, Device

app = create_app()

with app.app_context():
    db.create_all()

with app.app_context():
    # CREATE
    device = Device(device_id="test01", name="Test Device", api_key="dummykey")
    db.session.add(device)
    db.session.commit()
    print("Created device:", device.device_id)

    # READ
    retrieved = Device.query.filter_by(device_id="test01").first()
    print("Retrieved:", retrieved.name)

    # UPDATE
    retrieved.name = "Updated Device"
    db.session.commit()
    print("Updated:", retrieved.name)

    # DELETE
    db.session.delete(retrieved)
    db.session.commit()
    print("Deleted device")
