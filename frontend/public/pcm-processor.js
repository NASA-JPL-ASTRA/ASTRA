/**
 * AudioWorklet processor to capture raw PCM (replaces deprecated ScriptProcessorNode).
 * Sends Float32 audio chunks to the main thread via postMessage.
 */
class PCMProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0]
    if (input && input.length > 0) {
      const channel = input[0]
      // Copy: input buffer is reused by Web Audio API
      this.port.postMessage({ pcm: new Float32Array(channel) })
    }
    return true // keep alive
  }
}

registerProcessor('pcm-processor', PCMProcessor)
