# Mafia42 Collection Journal — Production Deployment Guide

This guide details how to deploy the Mafia42 Collection Journal as a publicly accessible HTTPS web application with a persistent database and owner-only administration.

---

## 1. Architecture Overview

- **Frontend**: React 18 + TypeScript + Vite, compiled into `frontend/dist/`.
- **Backend**: FastAPI with Uvicorn, serving API routes at `/api/*` and static assets at `/assets/*`.
- **Database**: PostgreSQL (relational database with ACID guarantees, foreign keys, indexes).
- **Authentication**: JWT access tokens stored in HTTP-only cookies or Authorization headers, passwords hashed with bcrypt.
- **Image Assets**: Statically hosted binary images (`.webp`, `.jpg`, `.png`) served under `/assets/<category>/<filename>`.

---

## 2. Option A: Cloud Deployment (Render / Railway / Fly.io)

### Step 1: Managed PostgreSQL Database
1. Provision a PostgreSQL instance on Railway, Render, or Supabase.
2. Note the connection URI:
   `postgresql://postgres:<password>@<host>:5432/<database>`

### Step 2: Environment Variables
Configure the following environment variables in your deployment dashboard:
- `DATABASE_URL`: Your PostgreSQL connection string.
- `SECRET_KEY`: A random 64-character hex secret for JWT token encryption.
- `INITIAL_OWNER_EMAIL`: The owner's email address (e.g., `owner@mafia42journal.com`).
- `INITIAL_OWNER_USERNAME`: The owner's display handle (e.g., `Owner`).
- `INITIAL_OWNER_PASSWORD`: A secure deployment-time password for the owner.

### Step 3: Build & Start Command
- **Build Command**:
  ```bash
  cd frontend && npm install && npm run build && cd .. && pip install -r backend/requirements.txt
  ```
- **Start Command**:
  ```bash
  uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
  ```

---

## 3. Option B: Docker Compose (VPS / DigitalOcean / Linode)

1. Clone repository to your server:
   ```bash
   git clone <repo-url> mafia42-journal
   cd mafia42-journal
   ```
2. Copy `.env.example` to `.env` and fill in secrets:
   ```bash
   cp .env.example .env
   ```
3. Run with Docker Compose:
   ```bash
   docker compose up -d --build
   ```
4. Configure Nginx with Let's Encrypt SSL:
   ```nginx
   server {
       server_name journal.yourdomain.com;

       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```
   ```bash
   certbot --nginx -d journal.yourdomain.com
   ```

---

## 4. Administrative Owner Account Verification

1. On first boot, the system checks if an owner exists. If none is found, it automatically creates the owner account specified in `INITIAL_OWNER_EMAIL` and `INITIAL_OWNER_PASSWORD`.
2. To reset or bootstrap an owner account via CLI:
   ```bash
   python scripts/bootstrap_owner.py owner@example.com Owner MySecurePassword2026!
   ```
3. Log in via the web interface. Once logged in as Owner, the sidebar will show the **Admin Dashboard** with access to:
   - Create, edit, and delete catalogue items.
   - Upload new catalogue images.
   - Manage wallets with 1 logo and 3 detailed images.
   - Suspend or activate user accounts.
   - View security audit logs.
   - Export and import catalogue JSON backups.

