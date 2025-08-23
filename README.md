# APIManager

Pupero API Manager is a FastAPI reverse‑proxy that exposes a single entrypoint and forwards requests to the right microservice.

- Public port: 8000
- Proxied services (defaults, configurable via .env):
  - /auth/*  -> Login service (default http://localhost:8001)
  - /offers/* -> Offers service (default http://localhost:8002)
  - /transactions/* -> Transactions service (default http://localhost:8003)

## Features
- Lightweight reverse proxy using httpx
- 502 Bad Gateway with context when upstream is unreachable
- OpenAPI passthrough for each upstream at:
  - /auth/openapi.json
  - /offers/openapi.json
  - /transactions/openapi.json
- Experimental combined OpenAPI and docs at:
  - /combined-openapi.json
  - /combined-docs (Swagger UI)

## Environment
Create an `.env` (already present) and adjust if needed:

```
API_MANAGER_PORT=8000
LOGIN_SERVICE_URL=http://localhost:8001
OFFERS_SERVICE_URL=http://localhost:8002
TRANSACTIONS_SERVICE_URL=http://localhost:8003
```

## Run locally

```
cd APIManager
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Docker

```
docker build -t pupero-api-manager -f APIManager/Dockerfile .
docker run --rm -p 8000:8000 --env-file APIManager/.env pupero-api-manager
```

## Notes
- The APIManager does not do auth by itself; it forwards Bearer tokens/cookies to upstreams.
- Ensure the upstream services are running and reachable at the configured URLs.
