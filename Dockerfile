# API Manager (FastAPI) - Alpine
FROM python:3.11-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install build deps (httpx has wheels; minimal set is fine)
RUN apk add --no-cache build-base gcc musl-dev linux-headers libffi-dev mariadb-connector-c-dev python3-dev

WORKDIR /app
# Use repo root as build context; copy from service dir
COPY Pupero-APIManager/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy app source
COPY Pupero-APIManager/app /app/app
# .env is provided at runtime via env vars or docker-compose; don't copy a missing file

EXPOSE 8000

# Use env API_MANAGER_PORT to select port
CMD ["/bin/sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${API_MANAGER_PORT:-8000}"]
