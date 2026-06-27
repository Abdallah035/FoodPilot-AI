# Food Pilot — FastAPI SSE bridge (Podman/Docker compatible)
# Build from the repo root:
#   podman build -t foodpilot-bridge -f server/Dockerfile .
#   podman run --rm -p 8000:8000 --env-file .env foodpilot-bridge
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code (agents, pipeline, RAG, bridge).
COPY . .

EXPOSE 8000

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
