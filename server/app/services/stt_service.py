import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class STTService:
    """Deepgram streaming speech-to-text service."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.connections: dict[str, object] = {}  # session_id -> Deepgram live connection

    async def start_stream(self, session_id: str, on_transcript: Callable) -> None:
        """Open a Deepgram live transcription connection."""
        try:
            from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions

            client = DeepgramClient(self.api_key)
            connection = client.listen.asyncwebsocket.v("1")

            async def on_message(self_conn, result, **kwargs):
                try:
                    transcript = result.channel.alternatives[0].transcript
                    if not transcript:
                        return

                    is_final = result.is_final
                    start = result.start if hasattr(result, "start") else 0
                    duration = result.duration if hasattr(result, "duration") else 0

                    segment = {
                        "type": "final" if is_final else "interim",
                        "text": transcript,
                        "start_time": start,
                        "end_time": start + duration,
                        "confidence": result.channel.alternatives[0].confidence,
                        "is_final": is_final,
                    }
                    await on_transcript(segment)
                except Exception as e:
                    logger.error(f"Error processing STT result: {e}")

            async def on_error(self_conn, error, **kwargs):
                logger.error(f"Deepgram error for session {session_id}: {error}")

            connection.on(LiveTranscriptionEvents.Transcript, on_message)
            connection.on(LiveTranscriptionEvents.Error, on_error)

            options = LiveOptions(
                model="nova-2",
                language="en",
                smart_format=True,
                interim_results=True,
                utterance_end_ms="1000",
                vad_events=True,
                encoding="linear16",
                sample_rate=48000,
                channels=1,
            )

            started = await connection.start(options)
            if started:
                self.connections[session_id] = connection
                logger.info(f"Deepgram stream started for session {session_id}")
            else:
                logger.error(f"Failed to start Deepgram stream for session {session_id}")

        except ImportError:
            logger.error("Deepgram SDK not installed")
            raise
        except Exception as e:
            logger.error(f"Failed to start STT for session {session_id}: {e}")
            raise

    async def send_audio(self, audio_bytes: bytes) -> None:
        """Forward audio bytes to all active Deepgram connections."""
        for session_id, connection in list(self.connections.items()):
            try:
                await connection.send(audio_bytes)
            except Exception as e:
                logger.error(f"Error sending audio for session {session_id}: {e}")

    async def stop_stream(self, session_id: str) -> None:
        """Close the Deepgram connection for a session."""
        connection = self.connections.pop(session_id, None)
        if connection:
            try:
                await connection.finish()
                logger.info(f"Deepgram stream stopped for session {session_id}")
            except Exception as e:
                logger.error(f"Error stopping Deepgram stream: {e}")
