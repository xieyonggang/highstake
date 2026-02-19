"""Thin JSON file store for session data.

Each session lives at: {storage_dir}/sessions/{session_id}/session.json
"""
from __future__ import annotations

import json
import os
import shutil
import uuid
from datetime import datetime, timezone

from app.config import settings


def _json_default(obj):
    """Handle datetime and other non-serializable types."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _session_dir(session_id: str) -> str:
    return os.path.join(settings.storage_dir, "sessions", session_id)


def _session_path(session_id: str) -> str:
    return os.path.join(_session_dir(session_id), "session.json")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_session(data: dict) -> dict:
    """Create a new session. Returns the full session dict with id and timestamps."""
    session_id = str(uuid.uuid4())
    now = _now_iso()
    session = {
        "id": session_id,
        "status": "configuring",
        "interaction_mode": data.get("interaction_mode", "q_and_a"),
        "intensity": data.get("intensity", "medium"),
        "agents": data.get("agents", ["skeptic", "analyst", "contrarian"]),
        "focus_areas": data.get("focus_areas", []),
        "deck_id": data.get("deck_id"),
        "started_at": None,
        "ended_at": None,
        "duration_secs": None,
        "recording_key": None,
        "created_at": now,
        "updated_at": now,
    }
    directory = _session_dir(session_id)
    os.makedirs(directory, exist_ok=True)
    with open(_session_path(session_id), "w") as f:
        json.dump(session, f, indent=2, default=_json_default)
    return session


def read_session(session_id: str) -> dict | None:
    """Read session.json. Returns None if not found."""
    path = _session_path(session_id)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def update_session(session_id: str, updates: dict) -> dict | None:
    """Merge updates into session.json and bump updated_at. Returns updated dict or None."""
    session = read_session(session_id)
    if session is None:
        return None
    for key, value in updates.items():
        if value is not None:
            session[key] = value
    session["updated_at"] = _now_iso()
    with open(_session_path(session_id), "w") as f:
        json.dump(session, f, indent=2, default=_json_default)
    return session


def delete_session(session_id: str) -> bool:
    """Delete the entire session directory. Returns True if it existed."""
    directory = _session_dir(session_id)
    if not os.path.exists(directory):
        return False
    shutil.rmtree(directory)
    return True
