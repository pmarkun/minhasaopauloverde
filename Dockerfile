FROM node:22-slim AS frontend

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
RUN npm run build

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV TREECHECK_DATA_DIR=/data

COPY backend ./backend
RUN uv pip install --system ./backend

COPY --from=frontend /app/frontend/out ./frontend/out

CMD ["sh", "-c", "python -m uvicorn treecheck_api.main:app --app-dir backend/src --host 0.0.0.0 --port ${PORT:-8000}"]
