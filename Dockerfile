# Multi-stage Dockerfile for Mafia42 Collection Journal
# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Production runner
FROM python:3.12-slim AS runner
WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install runtime dependencies (libpq-dev for psycopg2, gcc for compilation)
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
# Copy game image assets from frontend/public into backend/static so they're served via /assets/
COPY --from=frontend-builder /app/frontend/public/assets ./backend/static/assets

# Persistent image upload directory (mount a volume here in production for uploaded images)
RUN mkdir -p /app/backend/static/assets/uploaded

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
