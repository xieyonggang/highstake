import logging

import socketio

logger = logging.getLogger(__name__)

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False,
)

# Store active session mappings: sid -> session_id
active_sessions: dict[str, str] = {}


@sio.event
async def connect(sid, environ, auth):
    session_id = None
    if auth and isinstance(auth, dict):
        session_id = auth.get("sessionId")

    if session_id:
        active_sessions[sid] = session_id
        await sio.enter_room(sid, f"session_{session_id}")
        logger.info(f"Client {sid} connected to session {session_id}")
    else:
        logger.info(f"Client {sid} connected without session ID")


@sio.event
async def disconnect(sid):
    session_id = active_sessions.pop(sid, None)
    if session_id:
        logger.info(f"Client {sid} disconnected from session {session_id}")

        # Stop STT stream if active
        from app.ws.events import stop_stt_for_session
        await stop_stt_for_session(session_id)


@sio.event
async def audio_chunk(sid, data):
    from app.ws.events import handle_audio_chunk
    session_id = active_sessions.get(sid)
    if session_id:
        await handle_audio_chunk(session_id, sid, data)


@sio.event
async def slide_change(sid, data):
    from app.ws.events import handle_slide_change
    session_id = active_sessions.get(sid)
    if session_id:
        await handle_slide_change(session_id, sid, data)


@sio.event
async def presenter_response(sid, data):
    from app.ws.events import handle_presenter_response
    session_id = active_sessions.get(sid)
    if session_id:
        await handle_presenter_response(session_id, sid, data)


@sio.event
async def end_session(sid, data):
    from app.ws.events import handle_end_session
    session_id = active_sessions.get(sid)
    if session_id:
        await handle_end_session(session_id, sid)
