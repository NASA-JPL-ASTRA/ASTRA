import { useCallback, useRef, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { createSession, endSession, uploadAudioChunk } from '../services/api';
import { connectSessionWs, type SessionWsConnection } from '../services/sessionWs';
import type { BackendNote } from '../types';

const TARGET_SAMPLE_RATE = 16000;

/** End an utterance and send STT after this much trailing silence (pause-based chunking). */
const PAUSE_TO_FLUSH_SEC = 0.45;
/** Safety cap so one uninterrupted monologue still ships in bounded chunks. */
const MAX_UTTERANCE_SEC = 8;

/** When both stay below these, skip STT upload (reduces silence / room-noise hallucinations). */
const SILENCE_RMS_MAX = 0.006;
const SILENCE_PEAK_MAX = 0.022;

function pcmWindowSignalStats(samples: Float32Array): { rms: number; peak: number } {
  if (samples.length === 0) return { rms: 0, peak: 0 };
  let sumSq = 0;
  let peak = 0;
  for (let i = 0; i < samples.length; i++) {
    const v = samples[i];
    const a = Math.abs(v);
    if (a > peak) peak = a;
    sumSq += v * v;
  }
  return { rms: Math.sqrt(sumSq / samples.length), peak };
}

function mergeFloat32Parts(parts: Float32Array[]): Float32Array {
  const totalLen = parts.reduce((n, c) => n + c.length, 0);
  const merged = new Float32Array(totalLen);
  let offset = 0;
  for (const c of parts) {
    merged.set(c, offset);
    offset += c.length;
  }
  return merged;
}

const LEVEL_UPDATE_INTERVAL_MS = 80;

// Force-finalize a sentence if it keeps growing past this many characters
// without ever hitting terminal punctuation — prevents a single entry from
// becoming an unbounded wall of text when the speaker never pauses.
const MAX_SENTENCE_CHARS = 400;

// Detect sentence-ending punctuation (ASCII + CJK), tolerating trailing
// quotes/brackets/whitespace.
const SENTENCE_TERMINATOR_RE = /[.!?。！？][\s"')\]]*$/;

function endsSentence(text: string): boolean {
  return SENTENCE_TERMINATOR_RE.test(text.trim());
}

function mergeSentenceText(base: string, incoming: string): string {
  const next = incoming.trim();
  if (!base) return next;
  if (!next) return base;
  return /\s$/.test(base) ? base + next : `${base} ${next}`;
}

function newSentenceId(): string {
  return `sent_${Math.random().toString(36).slice(2, 10)}`;
}

function buildSessionName(now: Date): string {
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  const seconds = String(now.getSeconds()).padStart(2, '0');
  return `REC-${year}${month}${day}-${hours}${minutes}${seconds}`;
}

/**
 * Downsample Float32 PCM from inputRate to outputRate via linear interpolation.
 */
function downsample(buffer: Float32Array, inputRate: number, outputRate: number): Float32Array {
  if (inputRate === outputRate) return buffer;
  const ratio = inputRate / outputRate;
  const newLength = Math.round(buffer.length / ratio);
  const result = new Float32Array(newLength);
  for (let i = 0; i < newLength; i++) {
    const srcIdx = i * ratio;
    const lo = Math.floor(srcIdx);
    const hi = Math.min(lo + 1, buffer.length - 1);
    const frac = srcIdx - lo;
    result[i] = buffer[lo] * (1 - frac) + buffer[hi] * frac;
  }
  return result;
}

/**
 * Convert Float32 PCM [-1, 1] to Int16 PCM for network transmission.
 */
function float32ToInt16(float32: Float32Array): Int16Array {
  const int16 = new Int16Array(float32.length);
  for (let i = 0; i < float32.length; i++) {
    const s = Math.max(-1, Math.min(1, float32[i]));
    int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return int16;
}

function writeString(view: DataView, offset: number, str: string) {
  for (let i = 0; i < str.length; i++) {
    view.setUint8(offset + i, str.charCodeAt(i));
  }
}

/**
 * Wrap raw PCM16 samples in a WAV container so the backend receives a
 * self-describing audio file.
 */
function pcm16ToWavBlob(pcm16: Int16Array, sampleRate: number): Blob {
  const numChannels = 1;
  const bitsPerSample = 16;
  const byteRate = sampleRate * numChannels * (bitsPerSample / 8);
  const blockAlign = numChannels * (bitsPerSample / 8);
  const dataSize = pcm16.byteLength;
  const headerSize = 44;
  const buffer = new ArrayBuffer(headerSize + dataSize);
  const view = new DataView(buffer);

  writeString(view, 0, 'RIFF');
  view.setUint32(4, 36 + dataSize, true);
  writeString(view, 8, 'WAVE');
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, byteRate, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, bitsPerSample, true);
  writeString(view, 36, 'data');
  view.setUint32(40, dataSize, true);

  new Uint8Array(buffer, headerSize).set(new Uint8Array(pcm16.buffer));
  return new Blob([buffer], { type: 'audio/wav' });
}

/**
 * Real audio capture + transcription hook.
 *
 * Captures audio from the browser microphone via getUserMedia, provides
 * real-time audio levels from an AnalyserNode, and ships **pause-based**
 * utterances (flush after ~1s silence, or max length cap) as 16 kHz mono WAV
 * to the backend STT.
 */
export function useWhisper() {
  const {
    isRecording,
    isPaused,
    wsConnected,
    backendSessionId,
    setIsRecording,
    setIsPaused,
    setWsConnected,
    setBackendSessionId,
    upsertStreamingTranscription,
    clearTranscriptions,
    updateAudioLevel,
    setRecordingError,
    setSessionStartTime,
    selectedSttModel,
    showSavedToast,
    dismissSavedToast,
    addLiveNote,
    updateLiveNote,
    removeLiveNote,
    clearLiveNotes,
  } = useStore();

  // ── Audio capture refs ──
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const levelTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  /** Float32 mic buffers accumulated for the current spoken utterance (native sample rate). */
  const utterancePcmPartsRef = useRef<Float32Array[]>([]);
  /** Consecutive silent samples while waiting to close an utterance. */
  const silenceGapSamplesRef = useRef(0);
  const flushPendingUtteranceRef = useRef<() => Promise<void> | null>(null);

  // ── Connection refs ──
  const wsConnectionRef = useRef<SessionWsConnection | null>(null);
  const uploadChainRef = useRef<Promise<void>>(Promise.resolve());
  const sessionNameRef = useRef<string>('');
  const chunkSequenceRef = useRef(0);
  const selectedSttModelRef = useRef(selectedSttModel);

  const isActiveRef = useRef(false);

  // ── Sentence accumulation refs ──
  // Transcriptions arrive per pause-based chunk; a spoken sentence may still span
  // multiple chunks. We accumulate chunk text client-side into one "live"
  // entry keyed by a frontend-generated sentence id, and only promote it to
  // final when we see sentence-terminating punctuation.
  const sentenceIdRef = useRef<string | null>(null);
  const sentenceBaseRef = useRef<string>('');

  const backendSessionIdRef = useRef(backendSessionId);
  const upsertStreamingRef = useRef(upsertStreamingTranscription);
  const addLiveNoteRef = useRef(addLiveNote);
  const updateLiveNoteRef = useRef(updateLiveNote);
  const removeLiveNoteRef = useRef(removeLiveNote);
  useEffect(() => {
    backendSessionIdRef.current = backendSessionId;
    upsertStreamingRef.current = upsertStreamingTranscription;
    addLiveNoteRef.current = addLiveNote;
    updateLiveNoteRef.current = updateLiveNote;
    removeLiveNoteRef.current = removeLiveNote;
    selectedSttModelRef.current = selectedSttModel;
  }, [
    backendSessionId,
    upsertStreamingTranscription,
    addLiveNote,
    updateLiveNote,
    removeLiveNote,
    selectedSttModel,
  ]);

  // ── Audio level monitoring (real mic via AnalyserNode) ──

  const startLevelMonitor = useCallback(() => {
    levelTimerRef.current = window.setInterval(() => {
      const analyser = analyserRef.current;
      if (!analyser || !isActiveRef.current) return;

      const buf = new Float32Array(analyser.fftSize);
      analyser.getFloatTimeDomainData(buf);

      let sumSq = 0;
      for (let i = 0; i < buf.length; i++) sumSq += buf[i] * buf[i];
      const rms = Math.sqrt(sumSq / buf.length);

      updateAudioLevel(Math.min(1, rms * 5));
    }, LEVEL_UPDATE_INTERVAL_MS);
  }, [updateAudioLevel]);

  const stopLevelMonitor = useCallback(() => {
    if (levelTimerRef.current !== null) {
      window.clearInterval(levelTimerRef.current);
      levelTimerRef.current = null;
    }
  }, []);

  // ── PCM chunk flushing ──

  const enqueueChunkUpload = useCallback((
    sessionId: string,
    wavBlob: Blob,
    durationSeconds: number,
  ) => {
    chunkSequenceRef.current += 1;
    const chunkId = `chunk_${String(chunkSequenceRef.current).padStart(6, '0')}`;

    const uploadTask = async () => {
      try {
        await uploadAudioChunk(
          sessionId,
          wavBlob,
          chunkId,
          durationSeconds,
          selectedSttModelRef.current,
        );
      } catch (err) {
        console.error('[ASTRA] upload failed:', err);
      }
    };

    uploadChainRef.current = uploadChainRef.current
      .catch(() => {})
      .then(uploadTask);

    return uploadChainRef.current;
  }, []);

  const flushPendingUtterance = useCallback((): Promise<void> | null => {
    const parts = utterancePcmPartsRef.current;
    if (parts.length === 0) return null;
    const merged = mergeFloat32Parts(parts);
    utterancePcmPartsRef.current = [];
    silenceGapSamplesRef.current = 0;

    const inputRate = audioCtxRef.current?.sampleRate ?? 44100;
    const { rms, peak } = pcmWindowSignalStats(merged);
    if (rms < SILENCE_RMS_MAX && peak < SILENCE_PEAK_MAX) {
      if (import.meta.env.DEV) {
        console.debug('[ASTRA] skip silent utterance (no STT)', {
          rms: rms.toFixed(5),
          peak: peak.toFixed(5),
        });
      }
      return null;
    }

    const resampled = downsample(merged, inputRate, TARGET_SAMPLE_RATE);
    const pcm16 = float32ToInt16(resampled);
    const durationSeconds = resampled.length / TARGET_SAMPLE_RATE;

    if (import.meta.env.DEV) {
      console.debug(
        `[ASTRA] pause-based chunk: ${durationSeconds.toFixed(2)}s, ` +
          `${pcm16.byteLength} bytes PCM16 @ ${TARGET_SAMPLE_RATE}Hz`,
      );
    }

    const sessionId = backendSessionIdRef.current;
    if (!sessionId) return null;
    const wavBlob = pcm16ToWavBlob(pcm16, TARGET_SAMPLE_RATE);
    return enqueueChunkUpload(sessionId, wavBlob, durationSeconds);
  }, [enqueueChunkUpload]);

  useEffect(() => {
    flushPendingUtteranceRef.current = flushPendingUtterance;
  }, [flushPendingUtterance]);

  // ── Audio pipeline setup / teardown ──

  const setupAudio = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
        channelCount: 1,
      },
    });
    mediaStreamRef.current = stream;

    const ctx = new AudioContext();
    await ctx.resume();
    audioCtxRef.current = ctx;

    const source = ctx.createMediaStreamSource(stream);
    sourceRef.current = source;

    // AnalyserNode for real-time audio level
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 2048;
    analyser.smoothingTimeConstant = 0.8;
    source.connect(analyser);
    analyserRef.current = analyser;

    utterancePcmPartsRef.current = [];
    silenceGapSamplesRef.current = 0;

    // ScriptProcessorNode: pause-based utterance detection (flush after ~1s silence)
    const processor = ctx.createScriptProcessor(4096, 1, 1);
    processor.onaudioprocess = (e) => {
      if (!isActiveRef.current) return;
      const inputRate = audioCtxRef.current?.sampleRate ?? 44100;
      const buf = new Float32Array(e.inputBuffer.getChannelData(0));
      const stats = pcmWindowSignalStats(buf);
      const isSpeech = stats.rms >= SILENCE_RMS_MAX || stats.peak >= SILENCE_PEAK_MAX;
      const pauseSamples = Math.floor(inputRate * PAUSE_TO_FLUSH_SEC);

      if (isSpeech) {
        utterancePcmPartsRef.current.push(buf);
        silenceGapSamplesRef.current = 0;
        const total = utterancePcmPartsRef.current.reduce((n, c) => n + c.length, 0);
        if (total >= Math.floor(inputRate * MAX_UTTERANCE_SEC)) {
          void flushPendingUtteranceRef.current?.();
        }
      } else {
        silenceGapSamplesRef.current += buf.length;
        if (
          utterancePcmPartsRef.current.length > 0 &&
          silenceGapSamplesRef.current >= pauseSamples
        ) {
          void flushPendingUtteranceRef.current?.();
        }
      }
    };
    source.connect(processor);

    // Route through a silent gain so the processor fires without speaker output
    const silentGain = ctx.createGain();
    silentGain.gain.value = 0;
    processor.connect(silentGain);
    silentGain.connect(ctx.destination);
    processorRef.current = processor;

    startLevelMonitor();
  }, [startLevelMonitor]);

  const teardownAudio = useCallback(() => {
    stopLevelMonitor();

    processorRef.current?.disconnect();
    processorRef.current = null;
    sourceRef.current?.disconnect();
    sourceRef.current = null;
    analyserRef.current = null;

    audioCtxRef.current?.close().catch(() => {});
    audioCtxRef.current = null;

    mediaStreamRef.current?.getTracks().forEach((t) => t.stop());
    mediaStreamRef.current = null;

    utterancePcmPartsRef.current = [];
    silenceGapSamplesRef.current = 0;
  }, [stopLevelMonitor]);

  // ── Main control functions ──

  const startRecording = useCallback(async () => {
    try {
      const now = new Date();
      const sessionName = buildSessionName(now);

      setRecordingError(null);
      setSessionStartTime(now);
      setIsRecording(true);
      setIsPaused(false);
      setWsConnected(false);
      setBackendSessionId(null);
      clearTranscriptions();
      clearLiveNotes();
      dismissSavedToast();

      sentenceIdRef.current = null;
      sentenceBaseRef.current = '';
      uploadChainRef.current = Promise.resolve();
      sessionNameRef.current = sessionName;
      chunkSequenceRef.current = 0;

      // Request real microphone access and set up audio pipeline
      await setupAudio();

      // Create backend session + WebSocket connection
      const session = await createSession(
        sessionName,
        'Browser microphone recording routed through backend STT.',
      );
      setBackendSessionId(session.id);

      wsConnectionRef.current = connectSessionWs(session.id, {
        onOpen: () => setWsConnected(true),
        onClose: () => setWsConnected(false),
        onError: () => setWsConnected(false),
        onMessage: (msg) => {
          const data = msg.data as Record<string, unknown>;

          if (import.meta.env.DEV) {
            console.debug('[ASTRA-WS]', msg.event, data);
          }

          if (msg.event === 'transcript.chunk.ready') {
            // Streaming delta from OpenAI for the current pause-based chunk. We render
            // it combined with whatever we've accumulated from previous chunks
            // in the same (in-progress) sentence, so the typewriter sees the
            // full running sentence as its target.
            const transcript =
              typeof data.transcript === 'string' ? data.transcript : '';
            if (!transcript) return;
            if (!sentenceIdRef.current) {
              sentenceIdRef.current = newSentenceId();
            }
            const display = mergeSentenceText(sentenceBaseRef.current, transcript);
            upsertStreamingRef.current(sentenceIdRef.current, display, false);
          } else if (msg.event === 'stt.task.done') {
            // One utterance chunk finished. Append its final text to the sentence
            // buffer. If the buffer now ends with sentence-terminating
            // punctuation (or has grown too long), finalize the entry and
            // start a new sentence for the next chunk. Otherwise keep the
            // entry open so the next chunk extends it.
            const transcript =
              typeof data.transcript === 'string' ? data.transcript : '';
            if (!transcript) return;
            if (!sentenceIdRef.current) {
              sentenceIdRef.current = newSentenceId();
            }
            const sid = sentenceIdRef.current;
            const merged = mergeSentenceText(sentenceBaseRef.current, transcript);
            const shouldFinalize =
              endsSentence(merged) || merged.length > MAX_SENTENCE_CHARS;
            if (shouldFinalize) {
              upsertStreamingRef.current(sid, merged, true);
              sentenceIdRef.current = null;
              sentenceBaseRef.current = '';
            } else {
              sentenceBaseRef.current = merged;
              upsertStreamingRef.current(sid, merged, false);
            }
          } else if (msg.event === 'note.created') {
            addLiveNoteRef.current(data as unknown as BackendNote);
          } else if (msg.event === 'note.updated') {
            const note = data as unknown as BackendNote;
            updateLiveNoteRef.current(note.id, note);
          } else if (msg.event === 'note.deleted') {
            if (typeof data.id === 'string') {
              removeLiveNoteRef.current(data.id);
            }
          }
        },
      });

      isActiveRef.current = true;
    } catch (err) {
      teardownAudio();
      wsConnectionRef.current?.close();
      wsConnectionRef.current = null;
      setBackendSessionId(null);
      updateAudioLevel(0);
      setIsRecording(false);
      setIsPaused(false);
      setWsConnected(false);
      clearTranscriptions();
      clearLiveNotes();
      setSessionStartTime(null);

      if (err instanceof DOMException && err.name === 'NotAllowedError') {
        setRecordingError(
          'Microphone access denied. Please allow microphone permission and try again.',
        );
      } else if (err instanceof DOMException && err.name === 'NotFoundError') {
        setRecordingError(
          'No microphone found. Please connect a microphone and try again.',
        );
      } else {
        setRecordingError(
          err instanceof Error ? err.message : 'Failed to start recording',
        );
      }
    }
  }, [
    setRecordingError,
    setSessionStartTime,
    setIsRecording,
    setIsPaused,
    setWsConnected,
    setBackendSessionId,
    updateAudioLevel,
    setupAudio,
    teardownAudio,
    clearTranscriptions,
    clearLiveNotes,
    dismissSavedToast,
  ]);

  const pauseRecording = useCallback(() => {
    isActiveRef.current = false;
    void flushPendingUtteranceRef.current?.();

    // Suspend the AudioContext to pause microphone processing
    audioCtxRef.current?.suspend();
    stopLevelMonitor();

    updateAudioLevel(0);
    setIsPaused(true);
  }, [updateAudioLevel, setIsPaused, stopLevelMonitor]);

  const resumeRecording = useCallback(() => {
    setIsPaused(false);
    isActiveRef.current = true;

    // Resume the AudioContext to continue microphone processing
    audioCtxRef.current?.resume();
    startLevelMonitor();
  }, [setIsPaused, startLevelMonitor]);

  const stopRecording = useCallback(async () => {
    isActiveRef.current = false;

    // Flush any remaining buffered speech (may lack a trailing 1s pause)
    const finalUpload = flushPendingUtterance();

    // Finalize any in-progress sentence so it doesn't stay stuck as
    // "processing" in the UI after the mic is released.
    if (sentenceIdRef.current && sentenceBaseRef.current) {
      upsertStreamingRef.current(
        sentenceIdRef.current,
        sentenceBaseRef.current,
        true,
      );
    }
    sentenceIdRef.current = null;
    sentenceBaseRef.current = '';

    // Release microphone and close AudioContext
    teardownAudio();

    if (finalUpload) {
      await finalUpload.catch(() => {});
    }
    await uploadChainRef.current.catch(() => {});

    let finishedSessionName = sessionNameRef.current;
    if (backendSessionId) {
      try {
        const endedSession = await endSession(backendSessionId);
        finishedSessionName = endedSession.name;
      } catch {
        // Non-blocking: still stop local UI even if backend call fails.
      }
    }

    wsConnectionRef.current?.close();
    wsConnectionRef.current = null;
    setBackendSessionId(null);

    updateAudioLevel(0);
    setIsRecording(false);
    setIsPaused(false);
    setWsConnected(false);

    clearTranscriptions();
    clearLiveNotes();
    if (finishedSessionName) {
      showSavedToast(finishedSessionName);
    }
    setSessionStartTime(null);
  }, [
    backendSessionId,
    setBackendSessionId,
    updateAudioLevel,
    setIsRecording,
    setIsPaused,
    setWsConnected,
    clearTranscriptions,
    clearLiveNotes,
    showSavedToast,
    setSessionStartTime,
    teardownAudio,
    flushPendingUtterance,
  ]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      teardownAudio();
      wsConnectionRef.current?.close();
      wsConnectionRef.current = null;
    };
  }, [teardownAudio]);

  return {
    startRecording,
    pauseRecording,
    resumeRecording,
    stopRecording,
    isRecording,
    isPaused,
    wsConnected,
  };
}
