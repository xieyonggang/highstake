import logging
import os

# Prevent OMP duplicate library crash when torch + ctranslate2 both load OpenMP
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import socketio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.config import settings
from app.api import sessions, decks, debrief
from app.ws.handler import sio

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

# Suppress noisy third-party loggers
logging.getLogger("google_genai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create tables on startup (SQLite — no migration step needed)
    from app.models.base import init_db
    await init_db()
    logger.info("Database tables created / verified")

    # Ensure storage directory exists
    os.makedirs(settings.storage_dir, exist_ok=True)
    yield


app = FastAPI(
    title="HighStake API",
    description="AI-powered boardroom simulator backend",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount REST routes
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(decks.router, prefix="/api/decks", tags=["decks"])
app.include_router(debrief.router, prefix="/api", tags=["debrief"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.2.0"}


# ---------------------------------------------------------------------------
# Static file serving — local storage (replaces R2/S3 signed URLs)
# ---------------------------------------------------------------------------
MIME_MAP = {
    ".wav": "audio/wav",
    ".webm": "video/webm",
    ".mp4": "video/mp4",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".json": "application/json",
    ".pdf": "application/pdf",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


@app.get("/api/files/{file_path:path}")
async def serve_file(file_path: str):
    """Serve files from the local storage directory."""
    full_path = os.path.join(settings.storage_dir, file_path)
    # Prevent directory traversal
    full_path = os.path.realpath(full_path)
    storage_real = os.path.realpath(settings.storage_dir)
    if not full_path.startswith(storage_real):
        raise HTTPException(status_code=403, detail="Access denied")
    if not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="File not found")

    ext = os.path.splitext(full_path)[1].lower()
    media_type = MIME_MAP.get(ext, "application/octet-stream")
    return FileResponse(full_path, media_type=media_type)


@app.get("/api/resources/{file_path:path}")
async def serve_resource(file_path: str):
    """Serve static application resources."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    resources_dir = os.path.join(base_dir, "resources")
    full_path = os.path.join(resources_dir, file_path)
    
    # Prevent directory traversal
    full_path = os.path.realpath(full_path)
    resources_real = os.path.realpath(resources_dir)
    if not full_path.startswith(resources_real):
        raise HTTPException(status_code=403, detail="Access denied")
    if not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="File not found")

    ext = os.path.splitext(full_path)[1].lower()
    media_type = MIME_MAP.get(ext, "application/octet-stream")
    return FileResponse(full_path, media_type=media_type)


# Mount Socket.IO as ASGI sub-app
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)
