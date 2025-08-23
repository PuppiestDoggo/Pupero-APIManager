# API Manager (FastAPI) - Alpine
FROM python:3.11-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install build deps (httpx has wheels; minimal set is fine)
RUN apk add --no-cache build-base gcc musl-dev linux-headers libffi-dev

WORKDIR /app
COPY APIManager/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy app
COPY APIManager/app /app/app
COPY APIManager/.env /app/.env

EXPOSE 8000

# Use env API_MANAGER_PORT to select port
CMD ["/bin/sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${API_MANAGER_PORT:-8000}"]
