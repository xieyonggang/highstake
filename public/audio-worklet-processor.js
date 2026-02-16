/**
 * AudioWorklet processor that captures PCM 16kHz Int16 audio.
 *
 * Resamples from AudioContext sample rate to 16kHz,
 * buffers 1600 samples (100ms) per message,
 * and posts Int16 PCM data to the main thread.
 */
class PCMProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._buffer = new Float32Array(0);
    // 1600 samples at 16kHz = 100ms
    this._targetSamples = 1600;
    this._targetRate = 16000;
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0] || input[0].length === 0) {
      return true;
    }

    const channelData = input[0]; // mono channel
    const sourceRate = sampleRate; // global in AudioWorkletGlobalScope

    // Resample to 16kHz
    let resampled;
    if (sourceRate === this._targetRate) {
      resampled = channelData;
    } else {
      const ratio = sourceRate / this._targetRate;
      const outputLength = Math.floor(channelData.length / ratio);
      resampled = new Float32Array(outputLength);
      for (let i = 0; i < outputLength; i++) {
        const srcIndex = Math.floor(i * ratio);
        resampled[i] = channelData[srcIndex];
      }
    }

    // Append to buffer
    const newBuffer = new Float32Array(this._buffer.length + resampled.length);
    newBuffer.set(this._buffer, 0);
    newBuffer.set(resampled, this._buffer.length);
    this._buffer = newBuffer;

    // Emit 100ms chunks (1600 samples)
    while (this._buffer.length >= this._targetSamples) {
      const chunk = this._buffer.slice(0, this._targetSamples);
      this._buffer = this._buffer.slice(this._targetSamples);

      // Convert Float32 [-1, 1] to Int16
      const int16 = new Int16Array(chunk.length);
      for (let i = 0; i < chunk.length; i++) {
        const s = Math.max(-1, Math.min(1, chunk[i]));
        int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
      }

      this.port.postMessage(int16.buffer, [int16.buffer]);
    }

    return true;
  }
}

registerProcessor('pcm-processor', PCMProcessor);
