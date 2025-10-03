import json
import base64
import os
import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def encrypt_payload(api_key, payload_dict):
    """
    Encrypt a JSON-serializable dictionary using AES-GCM with the API key.
    Returns a URL-safe base64 encoded string.
    """
    key = base64.urlsafe_b64decode(api_key)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit nonce for AES-GCM
    data = json.dumps(payload_dict).encode('utf-8')
    ct = aesgcm.encrypt(nonce, data, None)
    return base64.urlsafe_b64encode(nonce + ct).decode('utf-8')

def send_event(hub_url, device_id, api_key, payload_dict, timeout=10):
    """
    Encrypts payload and sends it to the Hub over HTTPS.
    Headers:
        X-Device-ID: device_id
    Returns:
        Response object from requests
    """
    encrypted_payload = encrypt_payload(api_key, payload_dict)

    headers = {
        "X-Device-ID": device_id,
        "Content-Type": "text/plain"  # sending raw encrypted string
    }

    try:
        response = requests.post(
            hub_url,
            headers=headers,
            data=encrypted_payload,
            verify=True,  # Ensure TLS verification; set path to CA bundle if needed
            timeout=timeout
        )
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to send event: {e}")
        return None

def create_device(device_id, device_name):
    """
    Generate config and certs for a new device.
    Replace this with Person B's real implementation.
    """
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
