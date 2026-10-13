# Deployment Guide — Mafia42 Collection Journal

This guide covers deploying the application to [Render.com](https://render.com) (recommended free option)
using [Supabase](https://supabase.com) for the persistent PostgreSQL database.

---

## Architecture

```
GitHub Repo (code + images)
       │
       ▼
  Render.com (Docker web service)
  ├── FastAPI backend
  ├── React frontend (served as SPA from /dist)
  ├── Game images (baked into Docker image from frontend/public/assets)
  └── DATABASE_URL ──────────► Supabase PostgreSQL (persistent data)
```

---

## Step 1 — Create a Free Supabase PostgreSQL Database

> This is your **permanent database** — all catalogue items, users, and personal collections live here.

1. Go to **[supabase.com](https://supabase.com)** → **Sign up** (free)
2. Click **New Project**
   - Organisation: your personal org
   - Project name: `mafia42-journal`
   - Database password: choose a strong password (save it!)
   - Region: pick the closest region to you
3. Wait ~2 minutes for project to be created
4. In the left sidebar go to **Project Settings → Database**
5. Copy the **Connection string (URI)** under "Connection string" → select **URI** tab
   - It looks like: `postgresql://postgres:[YOUR-PASSWORD]@db.xxxx.supabase.co:5432/postgres`
6. **Save this URL** — you'll need it in Step 3

---

## Step 2 — Deploy to Render

1. Go to **[render.com](https://render.com)** → **Sign up** (free, use GitHub login)
2. Click **New → Web Service**
3. Select **"Build and deploy from a Git repository"**
4. Connect your GitHub account if not already connected
5. Find and select: `manyaa133/mafia42-collection-journal`
6. Configure the service:
   - **Name**: `mafia42-collection-journal`
   - **Region**: Oregon (US West) or nearest
   - **Branch**: `main`
   - **Runtime**: **Docker**
   - **Dockerfile Path**: `./Dockerfile`
   - **Plan**: **Free**
7. Click **Create Web Service** — Render will start building

---

## Step 3 — Set Environment Variables in Render

After the service is created, go to its **Environment** tab and add:

| Key | Value |
|-----|-------|
| `DATABASE_URL` | `postgresql://postgres:YOUR_PASSWORD@db.xxxx.supabase.co:5432/postgres` |
| `SECRET_KEY` | Run `python -c "import secrets; print(secrets.token_hex(32))"` and paste result |
| `INITIAL_OWNER_EMAIL` | `owner@mafia42journal.com` (or your email) |
| `INITIAL_OWNER_USERNAME` | `Owner` |
| `INITIAL_OWNER_PASSWORD` | A strong password (you'll log in with this!) |
| `CORS_ORIGINS` | `["https://mafia42-collection-journal.onrender.com"]` |

> [!IMPORTANT]
> Replace `mafia42-collection-journal.onrender.com` with your **actual** Render URL (visible in the service overview).
> After setting env vars, click **Manual Deploy → Deploy latest commit** to apply them.

---

## Step 4 — Verify the Deployment

1. Open your Render URL (e.g. `https://mafia42-collection-journal.onrender.com`)
2. The site should load — you'll see the Mafia42 Collection Journal
3. Check the health endpoint: `https://mafia42-collection-journal.onrender.com/api/health`
   - Should return: `{"status": "healthy", ...}`
4. Log in with your owner credentials
5. Go to **Owner Administration** → verify catalogue items are present
6. Try adding a test item in any section → verify it saves and appears

---

## Step 5 — Change Your Owner Password

On first login:
1. Go to **Profile** → change the password set in `INITIAL_OWNER_PASSWORD`
2. This is important — the initial password was set via env var which anyone with Render access could see

---

## Data Persistence

| Data type | Where stored | Persists after redeploy? |
|-----------|-------------|--------------------------|
| Catalogue items | Supabase PostgreSQL | ✅ Yes — external database |
| User accounts | Supabase PostgreSQL | ✅ Yes |
| User collections | Supabase PostgreSQL | ✅ Yes |
| Pre-existing game images | Docker image (baked in) | ✅ Yes — always rebuilt from repo |
| Images uploaded via admin | Container filesystem | ⚠️ Lost on redeploy (see below) |

### Uploaded Image Persistence (Optional — Paid)

If you upload new images through the Admin Panel and want them to survive redeployments:
- **Render Disk**: $1/GB/month — add a 1GB persistent disk mounted at `/app/backend/static/assets`
- **Cloudinary free tier**: 25GB storage — requires code changes to use Cloudinary SDK for uploads

For now (free tier), uploaded images survive **server restarts** but not full redeployments. The pre-built game images are always safe.

---

## Updating the Application

To deploy code changes:
```bash
# Make your changes locally
git add .
git commit -m "your change description"
git push origin main
```

Render will **automatically redeploy** on every push to `main`.

> [!CAUTION]
> The database is **never** reset on redeploy — only missing owner account and empty catalogue are seeded.
> Existing items, user collections, and relationships are always preserved.

---

## Local Development

```bash
# Backend
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

---

## Administrator Usage

Once deployed, the owner can:

1. **Log in** at the public URL with the owner credentials
2. **Open Owner Administration** from the left navigation
3. **Add new items** to any section: Skins, Icons, Cards, Wallets, Nameplates, Frames
4. **Edit existing items** via the edit button on any catalogue item
5. **Delete items** with a confirmation step
6. **Upload images** through the item creation/edit form
7. **Manage users** and view audit logs

All changes save to the Supabase database immediately and permanently.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| White page / 404 | Frontend not built — check Render build logs |
| 500 on login | Check `DATABASE_URL` env var in Render |
| Images not loading | Check that `COPY frontend/public/assets` step ran in Docker build |
| "Not authenticated" | JWT secret mismatch — verify `SECRET_KEY` env var |
| Owner can't log in | Check `INITIAL_OWNER_*` env vars — reset by clearing DB and redeploying |
| Slow first load | Render free tier sleeps after 15min inactivity — first request wakes it up (~30s) |
