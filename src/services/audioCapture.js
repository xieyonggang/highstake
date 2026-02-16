export class AudioCaptureService {
  constructor(socket) {
    this.socket = socket;
    this.mediaRecorder = null;
    this.stream = null;
  }

  async start() {
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        sampleRate: 48000,
      },
    });

    this.mediaRecorder = new MediaRecorder(this.stream, {
      mimeType: 'audio/webm;codecs=opus',
    });

    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0 && this.socket?.connected) {
        this.socket.emit('audio_chunk', {
          audio: event.data,
          timestamp: performance.now() / 1000,
        });
      }
    };

    this.mediaRecorder.start(250); // 250ms chunks
  }

  stop() {
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
    }
    if (this.stream) {
      this.stream.getTracks().forEach((t) => t.stop());
      this.stream = null;
    }
  }

  mute() {
    if (this.stream) {
      this.stream.getAudioTracks().forEach((t) => {
        t.enabled = false;
      });
    }
  }

  unmute() {
    if (this.stream) {
      this.stream.getAudioTracks().forEach((t) => {
        t.enabled = true;
      });
    }
  }
}
