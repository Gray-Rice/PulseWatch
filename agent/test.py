from helper import encrypt_payload

api_key = "S1KPNMXG_Sn3LOXM9Q8b5PpPkdjsbLnLjPBRsgHMhK0="  # your device API key
payload = {
    "event_type": "file",
    "details": {"path": "/tmp/test.txt", "action": "closed", "process": "unknown"},
    "id": "test123",
}

encrypted = encrypt_payload(api_key, payload)
print(encrypted)
