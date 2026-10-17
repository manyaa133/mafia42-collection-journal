import os
import mimetypes
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response

from backend.app.config import settings
from backend.app.database import engine, Base, SessionLocal
from backend.app.seed import seed_database
from backend.app.routers import auth, catalogue, collection, user, admin, gems

# Create tables
Base.metadata.create_all(bind=engine)

# Resolve workspace root (two dirs up from this file: backend/app/main.py -> workspace)
WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Paths
BACKEND_ASSETS = os.path.join(WORKSPACE_DIR, "backend", "static", "assets")
os.makedirs(BACKEND_ASSETS, exist_ok=True)

FRONTEND_DIST = os.path.join(WORKSPACE_DIR, "frontend", "dist")
FRONTEND_DIST_ASSETS = os.path.join(FRONTEND_DIST, "assets")

# Initialize application
app = FastAPI(
    title=settings.APP_NAME,
    version="2.0.0",
    description="Mafia42 Collection Journal API with multi-user persistence and owner administration.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers (registered FIRST so they take priority)
app.include_router(auth.router, prefix="/api")
app.include_router(catalogue.router, prefix="/api")
app.include_router(collection.router, prefix="/api")
app.include_router(gems.router, prefix="/api")
app.include_router(user.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.on_event("startup")
def startup_seed():
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "2.0.0",
    }


# ---------------------------------------------------------------------------
# /assets/ — dual-source static route
#   Priority 1: frontend/dist/assets/   (Vite JS / CSS bundles)
#   Priority 2: backend/static/assets/  (game images: skins, icons, frames…)
# ---------------------------------------------------------------------------
@app.get("/assets/{file_path:path}")
async def serve_assets(file_path: str):
    # 1. Try the Vite-compiled frontend bundle first
    fe_path = os.path.join(FRONTEND_DIST_ASSETS, file_path)
    if os.path.isfile(fe_path):
        return FileResponse(fe_path)

    # 2. Fall back to game images
    game_path = os.path.join(BACKEND_ASSETS, file_path)
    if os.path.isfile(game_path):
        mime, _ = mimetypes.guess_type(game_path)
        return FileResponse(game_path, media_type=mime or "application/octet-stream")

    return Response(status_code=404)


# ---------------------------------------------------------------------------
# Serve remaining static files from frontend/dist (vite.svg, favicon, etc.)
# and the SPA index.html for all non-API, non-asset routes.
# ---------------------------------------------------------------------------
@app.get("/{full_path:path}")
async def serve_spa(full_path: str, request: Request):
    if not os.path.exists(FRONTEND_DIST):
        return Response(
            content="Frontend not built. Run: cd frontend && npm run build",
            status_code=503,
            media_type="text/plain",
        )

    # Try exact file in dist root (e.g. vite.svg, favicon.ico)
    candidate = os.path.join(FRONTEND_DIST, full_path)
    if os.path.isfile(candidate):
        return FileResponse(candidate)

    # Fall back to index.html (SPA client-side routing)
    return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
