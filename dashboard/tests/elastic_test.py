# dashboard/test_es_crud.py
import time
from app import create_app
from elasticsearch import Elasticsearch

app = create_app()

with app.app_context():
    # Connect to Elasticsearch using the docker-compose service name
    es = Elasticsearch(
        ["http://elasticsearch:9200"],  # service name from docker-compose.yml
        basic_auth=("elastic", "0Ji99IlL")  # replace with env var if you want
    )

    # Wait until ES is ready
    for _ in range(10):
        if es.ping():
            break
        print("Waiting for Elasticsearch to be ready...")
        time.sleep(3)
    else:
        raise Exception("Elasticsearch not ready")

    # Test CRUD
    doc = {"device_id": "123", "event_type": "network", "message": "Test event"}
    doc = {"device_id": "124", "event_type": "network", "message": "Test event"}
    doc = {"device_id": "125", "event_type": "network", "message": "Test event"}
    doc = {"device_id": "126", "event_type": "network", "message": "Test event"}
    doc = {"device_id": "127", "event_type": "network", "message": "Test event"}
    doc = {"device_id": "128", "event_type": "network", "message": "Test event"}
    res = es.index(index="network-events", document=doc)
    print("Indexed:", res)

    # retrieved = es.get(index="network-events", id=res["_id"])
    # print("Retrieved:", retrieved["_source"])

    # es.delete(index="network-events", id=res["_id"])
    # print("Deleted document")
