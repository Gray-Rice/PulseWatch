# PulseWatch

## Description

todo

## Compose Instructions

Add details to .env

```
START_LOCAL_VERSION=0.11.0
ES_LOCAL_VERSION=9.1.4
ES_LOCAL_CONTAINER_NAME=es-local-dev
ES_LOCAL_PASSWORD=
ES_LOCAL_PORT=9200
ES_LOCAL_URL=http://localhost:${ES_LOCAL_PORT}
ES_LOCAL_DISK_SPACE_REQUIRED=1gb
ES_LOCAL_JAVA_OPTS="-Xms128m -Xmx2g"
KIBANA_LOCAL_CONTAINER_NAME=kibana-local-dev
KIBANA_LOCAL_SETTINGS_CONTAINER_NAME=kibana-local-settings
KIBANA_LOCAL_PORT=5601
KIBANA_LOCAL_PASSWORD=
KIBANA_ENCRYPTION_KEY=
ES_LOCAL_API_KEY=
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=ids_db
POSTGRES_PORT=5432
INTERNAL_SECRET=""
```

Then start with compose

./start.sh

Elasticsearch: Your Flask app’s backend search engine, accessible at http://localhost:9200.

Kibana: Dashboard UI for Elasticsearch, accessible at http://localhost:5601.

Postgres: Your app’s relational database, accessible at localhost:5432.

Flask app: Your main API backend, accessible at http://localhost:5000.
Working Inside the Container

All dependencies and services are pre-configured inside the Flask app container. To run tests or manage the app:

docker exec -it pulsewatch-flask-app-1 bash


