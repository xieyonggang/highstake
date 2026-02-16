import logging

import socketio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import sessions, decks, debrief
from app.ws.handler import sio

logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create tables on startup (SQLite — no migration step needed)
    from app.models.base import init_db
    await init_db()
    logger.info("Database tables created / verified")
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


# Mount Socket.IO as ASGI sub-app
socket_app = socketio.ASGIApp(sio, other_app=app)
