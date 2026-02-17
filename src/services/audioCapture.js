/**
 * Audio capture service using AudioWorklet + Gemini Live API for STT.
 *
 * Captures PCM 16kHz Int16 audio via AudioWorklet, base64-encodes 100ms
 * chunks, and streams them to the server via Socket.IO. The server
 * forwards audio to a Gemini Live API session and emits transcript
 * segments back.
 *
 * Works identically across all browsers (Chrome, Firefox, Safari).
 */
export class AudioCaptureService {
  constructor(socket) {
    this.socket = socket;
    this.isRunning = false;
    this.isMuted = false;

    // AudioWorklet state
    this.audioContext = null;
    this.sourceNode = null;
    this.workletNode = null;
    this.mediaStream = null;

    // Callbacks for UI updates
    this.onInterimTranscript = null;
    this.onFinalTranscript = null;
    this.onError = null;
  }

  async start() {
    this.socket?.emit('client_debug_log', { msg: 'AudioCaptureService: start() called' });
    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      this.socket?.emit('client_debug_log', { msg: 'AudioCaptureService: getUserMedia success' });
    } catch (err) {
      console.warn('Microphone access denied:', err.message);
      this.socket?.emit('client_debug_log', { msg: 'AudioCaptureService: Microphone access denied: ' + err.message });
      this.onError?.('Microphone access denied.');
      return;
    }

    try {
      // Use native sample rate — the worklet will resample to 16kHz.
      // Forcing 16kHz breaks audio capture on many systems (macOS, etc.)
      this.audioContext = new AudioContext();
      await this.audioContext.resume();
      this.socket?.emit('client_debug_log', {
        msg: `AudioCaptureService: AudioContext created, sampleRate=${this.audioContext.sampleRate}, state=${this.audioContext.state}`,
      });

      // Load AudioWorklet processor
      await this.audioContext.audioWorklet.addModule('/audio-worklet-processor.js');
      this.socket?.emit('client_debug_log', { msg: 'AudioCaptureService: AudioWorklet module loaded' });

      this.sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream);
      this.workletNode = new AudioWorkletNode(this.audioContext, 'pcm-processor');

      // Handle PCM chunks from worklet
      this.workletNode.port.onmessage = (event) => {
        if (this.isMuted || !this.socket?.connected) return;

        const pcmBuffer = event.data; // ArrayBuffer of Int16 PCM
        const base64 = this._arrayBufferToBase64(pcmBuffer);
        this.socket.emit('audio_chunk', { audio: base64 });
      };

      this.sourceNode.connect(this.workletNode);
      // Connect to destination to keep the pipeline alive (silent output)
      this.workletNode.connect(this.audioContext.destination);

      this.isRunning = true;
      this.socket?.emit('client_debug_log', { msg: 'AudioCaptureService: Pipeline connected and running' });

      // Listen for server transcription results
      this._setupTranscriptListener();
    } catch (err) {
      console.warn('Failed to start audio capture:', err.message);
      this.socket?.emit('client_debug_log', { msg: 'AudioCaptureService: Failed to start: ' + err.message });
      this.onError?.('Failed to start audio capture: ' + err.message);
      this.stop();
    }
  }

  _setupTranscriptListener() {
    if (!this.socket) return;

    // Remove any existing listener to avoid duplicates
    this.socket.off('transcript_segment', this._onTranscriptSegment);

    this._onTranscriptSegment = (segment) => {
      if (segment.text) {
        if (segment.is_final) {
          this.onFinalTranscript?.(segment.text);
        } else {
          this.onInterimTranscript?.(segment.text);
        }
      }
    };

    this.socket.on('transcript_segment', this._onTranscriptSegment);
  }

  _arrayBufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }

  stop() {
    this.isRunning = false;

    if (this.workletNode) {
      this.workletNode.disconnect();
      this.workletNode = null;
    }

    if (this.sourceNode) {
      this.sourceNode.disconnect();
      this.sourceNode = null;
    }

    if (this.audioContext) {
      this.audioContext.close().catch(() => {});
      this.audioContext = null;
    }

    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((t) => t.stop());
      this.mediaStream = null;
    }

    if (this.socket && this._onTranscriptSegment) {
      this.socket.off('transcript_segment', this._onTranscriptSegment);
    }
  }

  mute() {
    this.isMuted = true;
  }

  unmute() {
    this.isMuted = false;
  }
}
