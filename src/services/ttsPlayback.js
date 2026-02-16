export class TTSPlaybackService {
  constructor() {
    this.queue = [];
    this.isPlaying = false;
    this.currentAudio = null;
  }

  enqueue(agentId, audioUrl, onStart, onEnd) {
    this.queue.push({ agentId, audioUrl, onStart, onEnd });
    if (!this.isPlaying) {
      this._playNext();
    }
  }

  _playNext() {
    if (this.queue.length === 0) {
      this.isPlaying = false;
      return;
    }

    this.isPlaying = true;
    const { agentId, audioUrl, onStart, onEnd } = this.queue.shift();
    this.currentAudio = new Audio(audioUrl);

    onStart?.(agentId);

    this.currentAudio.onended = () => {
      onEnd?.(agentId);
      this._playNext();
    };

    this.currentAudio.onerror = () => {
      onEnd?.(agentId);
      this._playNext();
    };

    this.currentAudio.play().catch(() => {
      onEnd?.(agentId);
      this._playNext();
    });
  }

  stop() {
    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio = null;
    }
    this.queue = [];
    this.isPlaying = false;
  }
}
