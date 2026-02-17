export class TTSPlaybackService {
  constructor(socket) {
    this.socket = socket;
    this.queue = [];
    this.isPlaying = false;
    this.currentAudio = null;
  }

  enqueue(agentId, audioUrl, onStart, onEnd) {
    this.socket?.emit('client_debug_log', { msg: `TTS: Enqueueing audio for ${agentId}` });
    this.queue.push({ agentId, audioUrl, onStart, onEnd });
    if (!this.isPlaying) {
      this._playNext();
    }
  }

  async _playNext() {
    if (this.queue.length === 0) {
      this.isPlaying = false;
      this.socket?.emit('client_debug_log', { msg: 'TTS: Queue empty, stopping' });
      return;
    }

    this.isPlaying = true;
    const { agentId, audioUrl, onStart, onEnd } = this.queue.shift();
    this.socket?.emit('client_debug_log', { msg: `TTS: Playing next: ${agentId}, url=${audioUrl}` });

    try {
      // Fetch the full audio file as a blob to avoid 206 Partial Content issues
      const resp = await fetch(audioUrl);
      const blob = await resp.blob();
      const blobUrl = URL.createObjectURL(blob);
      this.socket?.emit('client_debug_log', { msg: `TTS: Fetched blob for ${agentId}, size=${blob.size}` });

      this.currentAudio = new Audio(blobUrl);

      this.socket?.emit('client_debug_log', { msg: `TTS: Started playing for ${agentId}` });
      onStart?.(agentId);

      this.currentAudio.onended = () => {
        this.socket?.emit('client_debug_log', { msg: `TTS: Audio ended for ${agentId}` });
        URL.revokeObjectURL(blobUrl);
        onEnd?.(agentId);
        this._playNext();
      };

      this.currentAudio.onerror = (e) => {
        this.socket?.emit('client_debug_log', { msg: `TTS: Audio error for ${agentId}: ${e.message || 'unknown'}` });
        URL.revokeObjectURL(blobUrl);
        onEnd?.(agentId);
        this._playNext();
      };

      await this.currentAudio.play();
      this.socket?.emit('client_debug_log', { msg: `TTS: play() resolved for ${agentId}` });
    } catch (e) {
      this.socket?.emit('client_debug_log', { msg: `TTS: Failed for ${agentId}: ${e.message}` });
      onEnd?.(agentId);
      this._playNext();
    }
  }

  stop() {
    this.socket?.emit('client_debug_log', { msg: 'TTS: Stop called' });
    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio = null;
    }
    this.queue = [];
    this.isPlaying = false;
  }
}
