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

  _playNext() {
    if (this.queue.length === 0) {
      this.isPlaying = false;
      this.socket?.emit('client_debug_log', { msg: 'TTS: Queue empty, stopping' });
      return;
    }

    this.isPlaying = true;
    const { agentId, audioUrl, onStart, onEnd } = this.queue.shift();
    this.socket?.emit('client_debug_log', { msg: `TTS: Playing next: ${agentId}, url=${audioUrl}` });
    
    this.currentAudio = new Audio(audioUrl);

    // Wrapper for onStart to log
    const handleStart = (id) => {
        this.socket?.emit('client_debug_log', { msg: `TTS: Started playing for ${id}` });
        onStart?.(id);
    };

    handleStart(agentId); // Usually called immediately, or maybe we should wait for 'play'?

    this.currentAudio.onended = () => {
      this.socket?.emit('client_debug_log', { msg: `TTS: Audio ended for ${agentId}` });
      onEnd?.(agentId);
      this._playNext();
    };

    this.currentAudio.onerror = (e) => {
      this.socket?.emit('client_debug_log', { msg: `TTS: Audio error for ${agentId}: ${e.message || 'unknown'}` });
      onEnd?.(agentId);
      this._playNext();
    };

    this.currentAudio.play().then(() => {
        this.socket?.emit('client_debug_log', { msg: `TTS: play() promise resolved for ${agentId}` });
    }).catch((e) => {
      this.socket?.emit('client_debug_log', { msg: `TTS: play() failed for ${agentId}: ${e.message}` });
      onEnd?.(agentId);
      this._playNext();
    });
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
