export class VideoCaptureService {
  constructor() {
    this.stream = null;
    this.mediaRecorder = null;
    this.recordedChunks = [];
  }

  async startCamera() {
    this.stream = await navigator.mediaDevices.getUserMedia({
      video: { width: 1280, height: 720, frameRate: 30 },
      audio: true,
    });
    return this.stream;
  }

  startRecording() {
    if (!this.stream) return;
    this.recordedChunks = [];

    const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp9,opus')
      ? 'video/webm;codecs=vp9,opus'
      : 'video/webm';

    this.mediaRecorder = new MediaRecorder(this.stream, { mimeType });

    this.mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) {
        this.recordedChunks.push(e.data);
      }
    };

    this.mediaRecorder.start(1000); // 1s chunks
  }

  stopRecording() {
    return new Promise((resolve) => {
      if (!this.mediaRecorder || this.mediaRecorder.state === 'inactive') {
        resolve(null);
        return;
      }
      this.mediaRecorder.onstop = () => {
        const blob = new Blob(this.recordedChunks, { type: 'video/webm' });
        resolve(blob);
      };
      this.mediaRecorder.stop();
    });
  }

  stopCamera() {
    if (this.stream) {
      this.stream.getTracks().forEach((t) => t.stop());
      this.stream = null;
    }
  }

  toggleCamera(enabled) {
    if (this.stream) {
      this.stream.getVideoTracks().forEach((t) => {
        t.enabled = enabled;
      });
    }
  }
}
