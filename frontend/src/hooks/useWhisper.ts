import { useCallback, useRef, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { createSession, endSession } from '../services/api';
import { connectSessionWs, type SessionWsConnection } from '../services/sessionWs';
import type { BackendNote } from '../types';

const CHUNK_INTERVAL_MS = 3000;
const TARGET_SAMPLE_RATE = 16000;
const LEVEL_UPDATE_INTERVAL_MS = 80;

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

/**
 * Real audio capture + transcription hook.
 *
 * Captures audio from the browser microphone via getUserMedia, provides
 * real-time audio levels from an AnalyserNode, and buffers PCM chunks
 * (16kHz mono Int16) ready to send to the Whisper backend.
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
    addTranscription,
    updateAudioLevel,
    setRecordingError,
    setSessionStartTime,
    saveSessionToHistory,
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
  const pcmBufferRef = useRef<Float32Array[]>([]);
  const chunkTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Connection refs ──
  const wsConnectionRef = useRef<SessionWsConnection | null>(null);

  const isActiveRef = useRef(false);

  const addTranscriptionRef = useRef(addTranscription);
  const addLiveNoteRef = useRef(addLiveNote);
  const updateLiveNoteRef = useRef(updateLiveNote);
  const removeLiveNoteRef = useRef(removeLiveNote);
  useEffect(() => {
    addTranscriptionRef.current = addTranscription;
    addLiveNoteRef.current = addLiveNote;
    updateLiveNoteRef.current = updateLiveNote;
    removeLiveNoteRef.current = removeLiveNote;
  }, [addTranscription, addLiveNote, updateLiveNote, removeLiveNote]);

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

  const flushChunk = useCallback(() => {
    const chunks = pcmBufferRef.current;
    if (chunks.length === 0) return null;

    const totalLen = chunks.reduce((n, c) => n + c.length, 0);
    const merged = new Float32Array(totalLen);
    let offset = 0;
    for (const c of chunks) {
      merged.set(c, offset);
      offset += c.length;
    }
    pcmBufferRef.current = [];

    const inputRate = audioCtxRef.current?.sampleRate ?? 44100;
    const resampled = downsample(merged, inputRate, TARGET_SAMPLE_RATE);
    const pcm16 = float32ToInt16(resampled);

    if (import.meta.env.DEV) {
      console.debug(
        `[ASTRA] audio chunk: ${(resampled.length / TARGET_SAMPLE_RATE).toFixed(1)}s, ` +
          `${pcm16.byteLength} bytes PCM16 @ ${TARGET_SAMPLE_RATE}Hz`,
      );
    }

    // TODO: send pcm16.buffer via /ws/transcribe when the Whisper backend is ready
    return pcm16;
  }, []);

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

    // ScriptProcessorNode captures raw PCM for chunking
    const processor = ctx.createScriptProcessor(4096, 1, 1);
    processor.onaudioprocess = (e) => {
      if (!isActiveRef.current) return;
      pcmBufferRef.current.push(new Float32Array(e.inputBuffer.getChannelData(0)));
    };
    source.connect(processor);

    // Route through a silent gain so the processor fires without speaker output
    const silentGain = ctx.createGain();
    silentGain.gain.value = 0;
    processor.connect(silentGain);
    silentGain.connect(ctx.destination);
    processorRef.current = processor;

    // Periodically flush buffered PCM into discrete chunks
    chunkTimerRef.current = setInterval(() => {
      if (isActiveRef.current) flushChunk();
    }, CHUNK_INTERVAL_MS);

    startLevelMonitor();
  }, [flushChunk, startLevelMonitor]);

  const teardownAudio = useCallback(() => {
    stopLevelMonitor();

    if (chunkTimerRef.current) {
      clearInterval(chunkTimerRef.current);
      chunkTimerRef.current = null;
    }

    processorRef.current?.disconnect();
    processorRef.current = null;
    sourceRef.current?.disconnect();
    sourceRef.current = null;
    analyserRef.current = null;

    audioCtxRef.current?.close().catch(() => {});
    audioCtxRef.current = null;

    mediaStreamRef.current?.getTracks().forEach((t) => t.stop());
    mediaStreamRef.current = null;

    pcmBufferRef.current = [];
  }, [stopLevelMonitor]);

  // ── Main control functions ──

  const startRecording = useCallback(async () => {
    try {
      setRecordingError(null);
      setSessionStartTime(new Date());
      setIsRecording(true);
      setIsPaused(false);
      setWsConnected(false);
      setBackendSessionId(null);

      // Request real microphone access and set up audio pipeline
      await setupAudio();

      // Create backend session + WebSocket connection
      const session = await createSession('Frontend Live Session');
      setBackendSessionId(session.id);

      wsConnectionRef.current = connectSessionWs(session.id, {
        onOpen: () => setWsConnected(true),
        onClose: () => setWsConnected(false),
        onError: () => setWsConnected(false),
        onMessage: (msg) => {
          const data = msg.data as Record<string, unknown>;

          if (msg.event === 'stt.task.done') {
            if (typeof data.transcript === 'string' && data.transcript) {
              addTranscriptionRef.current({
                id: String(data.id ?? `tr_${Date.now()}`),
                timestamp: new Date(),
                speakerId: 'speaker_0',
                rawText: data.transcript,
                confidence: 0.9,
                isFinal: true,
              });
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
  ]);

  const pauseRecording = useCallback(() => {
    isActiveRef.current = false;

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

    // Flush any remaining buffered audio
    flushChunk();

    // Release microphone and close AudioContext
    teardownAudio();

    if (backendSessionId) {
      try {
        await endSession(backendSessionId);
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

    saveSessionToHistory();
    clearLiveNotes();
    setSessionStartTime(null);
  }, [
    backendSessionId,
    setBackendSessionId,
    updateAudioLevel,
    setIsRecording,
    setIsPaused,
    setWsConnected,
    saveSessionToHistory,
    clearLiveNotes,
    setSessionStartTime,
    teardownAudio,
    flushChunk,
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
