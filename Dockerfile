# Multi-stage Dockerfile for Mafia42 Collection Journal
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runner
WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY backend/ ./backend/
COPY database/ ./database/
COPY scripts/ ./scripts/

# Copy built frontend assets
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist
COPY --from=frontend-builder /app/frontend/public/assets ./backend/static/assets

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

