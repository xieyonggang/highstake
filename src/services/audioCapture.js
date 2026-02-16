/**
 * Audio capture service using the browser's Web Speech API.
 *
 * Instead of streaming raw audio blobs to the server (old Deepgram approach),
 * this runs speech recognition entirely in the browser and emits transcript
 * text to the server via Socket.IO.
 *
 * Events emitted:
 *   socket.emit('transcript_text', { text, isFinal, confidence })
 */
export class AudioCaptureService {
  constructor(socket) {
    this.socket = socket;
    this.recognition = null;
    this.isRunning = false;
    this.isMuted = false;

    // Callbacks for UI updates
    this.onInterimTranscript = null;
    this.onFinalTranscript = null;
    this.onError = null;
  }

  async start() {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      console.warn(
        'Web Speech API not supported in this browser. Try Chrome or Edge.'
      );
      this.onError?.('Speech recognition not supported in this browser.');
      return;
    }

    this.recognition = new SpeechRecognition();
    this.recognition.continuous = true;
    this.recognition.interimResults = true;
    this.recognition.lang = 'en-US';
    this.recognition.maxAlternatives = 1;

    this.recognition.onresult = (event) => {
      if (this.isMuted) return;

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        const text = result[0].transcript.trim();
        const confidence = result[0].confidence || 0.9;
        const isFinal = result.isFinal;

        if (!text) continue;

        // Emit to server
        if (this.socket?.connected) {
          this.socket.emit('transcript_text', {
            text,
            isFinal,
            confidence,
          });
        }

        // Notify UI callbacks
        if (isFinal) {
          this.onFinalTranscript?.(text);
        } else {
          this.onInterimTranscript?.(text);
        }
      }
    };

    this.recognition.onerror = (event) => {
      // 'no-speech' and 'aborted' are expected during normal usage
      if (event.error === 'no-speech' || event.error === 'aborted') {
        return;
      }
      console.warn('Speech recognition error:', event.error);
      this.onError?.(event.error);
    };

    // Auto-restart when the recognition ends (browser stops after silence)
    this.recognition.onend = () => {
      if (this.isRunning && !this.isMuted) {
        try {
          this.recognition.start();
        } catch {
          // Already started or disposed — ignore
        }
      }
    };

    this.isRunning = true;
    try {
      this.recognition.start();
    } catch (err) {
      console.warn('Failed to start speech recognition:', err.message);
    }
  }

  stop() {
    this.isRunning = false;
    if (this.recognition) {
      try {
        this.recognition.stop();
      } catch {
        // Already stopped
      }
      this.recognition = null;
    }
  }

  mute() {
    this.isMuted = true;
    // Stop recognition while muted to avoid processing speech
    if (this.recognition) {
      try {
        this.recognition.stop();
      } catch {
        // ignore
      }
    }
  }

  unmute() {
    this.isMuted = false;
    // Restart recognition when unmuted
    if (this.isRunning && this.recognition) {
      try {
        this.recognition.start();
      } catch {
        // ignore
      }
    }
  }
}
