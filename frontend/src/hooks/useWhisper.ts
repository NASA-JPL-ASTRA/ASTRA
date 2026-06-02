import { useCallback, useRef, useEffect } from 'react';
import { useStore } from '../store/useStore';
import {
  createSession,
  endSession,
  getLogTelemetryScenarios,
  uploadAudioChunk,
} from '../services/api';
import { connectSessionWs, type SessionWsConnection } from '../services/sessionWs';
import type { BackendNote } from '../types';
import {
  detectConnectedMics,
  loadDualMicConfig,
  MIC_1_SOURCE,
  MIC_2_SOURCE,
  MIC_SOURCE_LABELS,
  speakerIdForMicSource,
  type MicSourceId,
} from '../config/audioInputs';

const TARGET_SAMPLE_RATE = 16000;

/** End an utterance and send STT after this much trailing silence (pause-based chunking). */
const PAUSE_TO_FLUSH_SEC = 0.45;
/** Drop very short bursts; these are usually clicks, bumps, or room noise. */
const MIN_UTTERANCE_SEC = 0.45;
/** Safety cap so one uninterrupted monologue still ships in bounded chunks. */
const MAX_UTTERANCE_SEC = 8;

/** When both stay below these, skip STT upload (reduces silence / room-noise hallucinations). */
const SILENCE_RMS_MAX = 0.01;
const SILENCE_PEAK_MAX = 0.035;
const MIN_FINAL_RMS = 0.012;
const MIN_FINAL_PEAK = 0.045;
const MIN_DYNAMIC_RANGE = 0.025;
const LEVEL_UPDATE_INTERVAL_MS = 80;
const MAX_SENTENCE_CHARS = 400;
const SENTENCE_TERMINATOR_RE = /[.!?。！？][\s"')\]]*$/;

interface ChunkUploadMeta {
  micSource: MicSourceId;
  speakerId: string;
  utteranceStartMs: number;
}

interface MicPipeline {
  micSource: MicSourceId;
  deviceId: string;
  speakerId: string;
  label: string;
  mediaStream: MediaStream | null;
  audioCtx: AudioContext | null;
  analyser: AnalyserNode | null;
  source: MediaStreamAudioSourceNode | null;
  processor: ScriptProcessorNode | null;
  utterancePcmParts: Float32Array[];
  silenceGapSamples: number;
  utteranceStartMs: number | null;
  sentenceId: string | null;
  sentenceBase: string;
  uploadChain: Promise<void>;
  chunkSequence: number;
}

function createMicPipeline(micSource: MicSourceId, deviceId: string): MicPipeline {
  return {
    micSource,
    deviceId,
    speakerId: speakerIdForMicSource(micSource),
    label: MIC_SOURCE_LABELS[micSource],
    mediaStream: null,
    audioCtx: null,
    analyser: null,
    source: null,
    processor: null,
    utterancePcmParts: [],
    silenceGapSamples: 0,
    utteranceStartMs: null,
    sentenceId: null,
    sentenceBase: '',
    uploadChain: Promise.resolve(),
    chunkSequence: 0,
  };
}

function pcmWindowSignalStats(
  samples: Float32Array,
): { rms: number; peak: number; dynamicRange: number } {
  if (samples.length === 0) return { rms: 0, peak: 0, dynamicRange: 0 };
  let sumSq = 0;
  let peak = 0;
  let min = 1;
  let max = -1;
  for (let i = 0; i < samples.length; i++) {
    const v = samples[i];
    const a = Math.abs(v);
    if (a > peak) peak = a;
    if (v < min) min = v;
    if (v > max) max = v;
    sumSq += v * v;
  }
  return { rms: Math.sqrt(sumSq / samples.length), peak, dynamicRange: max - min };
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

function endsSentence(text: string): boolean {
  return SENTENCE_TERMINATOR_RE.test(text.trim());
}

function mergeSentenceText(base: string, incoming: string): string {
  const next = incoming.trim();
  if (!base) return next;
  if (!next) return base;
  return /\s$/.test(base) ? base + next : `${base} ${next}`;
}

function newSentenceId(micSource: MicSourceId): string {
  return `sent_${micSource}_${Math.random().toString(36).slice(2, 10)}`;
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

function resolveMicFromWsData(
  data: Record<string, unknown>,
  chunkMeta: Map<string, ChunkUploadMeta>,
): MicSourceId | null {
  const audioSource = data.audio_source;
  if (audioSource === MIC_1_SOURCE || audioSource === MIC_2_SOURCE) {
    return audioSource;
  }
  const chunkId = data.audio_chunk_id;
  if (typeof chunkId === 'string') {
    const meta = chunkMeta.get(chunkId);
    if (meta) return meta.micSource;
  }
  return null;
}

function resolveUtteranceStartMs(
  data: Record<string, unknown>,
  chunkMeta: Map<string, ChunkUploadMeta>,
  micSource: MicSourceId,
  pipelines: Map<MicSourceId, MicPipeline>,
): number {
  const raw = data.utterance_start_ms;
  if (typeof raw === 'number' && Number.isFinite(raw)) {
    return raw;
  }
  const chunkId = data.audio_chunk_id;
  if (typeof chunkId === 'string') {
    const meta = chunkMeta.get(chunkId);
    if (meta) return meta.utteranceStartMs;
  }
  return pipelines.get(micSource)?.utteranceStartMs ?? Date.now();
}

function resolveConfidence(data: Record<string, unknown>): number | undefined {
  const raw = data.confidence;
  if (typeof raw !== 'number' || !Number.isFinite(raw)) return undefined;
  return Math.min(1, Math.max(0, raw));
}

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
    clearVoiceTelemetryQueries,
    setTelemetryScenariosInfo,
    setMicSpeakers,
  } = useStore();

  const pipelinesRef = useRef<Map<MicSourceId, MicPipeline>>(new Map());
  const chunkMetaRef = useRef<Map<string, ChunkUploadMeta>>(new Map());
  const flushHandlersRef = useRef<Map<MicSourceId, () => Promise<void> | null>>(new Map());

  const wsConnectionRef = useRef<SessionWsConnection | null>(null);
  const sessionNameRef = useRef('');
  const globalChunkSequenceRef = useRef(0);
  const selectedSttModelRef = useRef(selectedSttModel);
  const isActiveRef = useRef(false);
  const levelTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const dualMicActiveRef = useRef(false);

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

  const applySttDelta = useCallback(
    (
      micSource: MicSourceId,
      transcript: string,
      utteranceStartMs: number,
      confidence?: number,
    ) => {
      const pipeline = pipelinesRef.current.get(micSource);
      if (!pipeline || !transcript) return;
      if (!pipeline.sentenceId) {
        pipeline.sentenceId = newSentenceId(micSource);
      }
      const display = mergeSentenceText(pipeline.sentenceBase, transcript);
      upsertStreamingRef.current(
        pipeline.sentenceId,
        display,
        false,
        pipeline.speakerId,
        utteranceStartMs,
        confidence,
      );
    },
    [],
  );

  const applySttDone = useCallback(
    (
      micSource: MicSourceId,
      transcript: string,
      utteranceStartMs: number,
      confidence?: number,
    ) => {
      const pipeline = pipelinesRef.current.get(micSource);
      if (!pipeline || !transcript) return;
      if (!pipeline.sentenceId) {
        pipeline.sentenceId = newSentenceId(micSource);
      }
      const sid = pipeline.sentenceId;
      const merged = mergeSentenceText(pipeline.sentenceBase, transcript);
      const shouldFinalize =
        endsSentence(merged) || merged.length > MAX_SENTENCE_CHARS;
      if (shouldFinalize) {
        upsertStreamingRef.current(
          sid,
          merged,
          true,
          pipeline.speakerId,
          utteranceStartMs,
          confidence,
        );
        pipeline.sentenceId = null;
        pipeline.sentenceBase = '';
      } else {
        pipeline.sentenceBase = merged;
        upsertStreamingRef.current(
          sid,
          merged,
          false,
          pipeline.speakerId,
          utteranceStartMs,
          confidence,
        );
      }
    },
    [],
  );

  const handleWsMessage = useCallback(
    (msg: { event: string; data: Record<string, unknown> }) => {
      const data = msg.data;
      if (import.meta.env.DEV) {
        console.debug('[ASTRA-WS]', msg.event, data);
      }

      if (msg.event === 'transcript.chunk.ready') {
        const micSource = resolveMicFromWsData(data, chunkMetaRef.current);
        if (!micSource) return;
        const transcript =
          typeof data.transcript === 'string' ? data.transcript : '';
        const utteranceStartMs = resolveUtteranceStartMs(
          data,
          chunkMetaRef.current,
          micSource,
          pipelinesRef.current,
        );
        applySttDelta(
          micSource,
          transcript,
          utteranceStartMs,
          resolveConfidence(data),
        );
      } else if (msg.event === 'stt.task.done') {
        const micSource = resolveMicFromWsData(data, chunkMetaRef.current);
        if (!micSource) return;
        const transcript =
          typeof data.transcript === 'string' ? data.transcript : '';
        const utteranceStartMs = resolveUtteranceStartMs(
          data,
          chunkMetaRef.current,
          micSource,
          pipelinesRef.current,
        );
        applySttDone(
          micSource,
          transcript,
          utteranceStartMs,
          resolveConfidence(data),
        );
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
    [applySttDelta, applySttDone],
  );

  const startLevelMonitor = useCallback(() => {
    levelTimerRef.current = window.setInterval(() => {
      if (!isActiveRef.current) return;
      let maxRms = 0;
      for (const pipeline of pipelinesRef.current.values()) {
        const analyser = pipeline.analyser;
        if (!analyser) continue;
        const buf = new Float32Array(analyser.fftSize);
        analyser.getFloatTimeDomainData(buf);
        let sumSq = 0;
        for (let i = 0; i < buf.length; i++) sumSq += buf[i] * buf[i];
        maxRms = Math.max(maxRms, Math.sqrt(sumSq / buf.length));
      }
      updateAudioLevel(Math.min(1, maxRms * 5));
    }, LEVEL_UPDATE_INTERVAL_MS);
  }, [updateAudioLevel]);

  const stopLevelMonitor = useCallback(() => {
    if (levelTimerRef.current !== null) {
      window.clearInterval(levelTimerRef.current);
      levelTimerRef.current = null;
    }
  }, []);

  const enqueueChunkUpload = useCallback(
    (
      pipeline: MicPipeline,
      sessionId: string,
      wavBlob: Blob,
      durationSeconds: number,
      utteranceStartMs: number,
    ) => {
      globalChunkSequenceRef.current += 1;
      pipeline.chunkSequence += 1;
      const chunkId = `chunk_${pipeline.micSource}_${String(globalChunkSequenceRef.current).padStart(6, '0')}`;

      chunkMetaRef.current.set(chunkId, {
        micSource: pipeline.micSource,
        speakerId: pipeline.speakerId,
        utteranceStartMs,
      });

      const uploadTask = async () => {
        try {
          await uploadAudioChunk(
            sessionId,
            wavBlob,
            chunkId,
            durationSeconds,
            selectedSttModelRef.current,
            {
              speaker: pipeline.label,
              audioSource: pipeline.micSource,
              utteranceStartMs,
            },
          );
        } catch (err) {
          console.error(`[ASTRA] upload failed (${pipeline.micSource}):`, err);
        }
      };

      pipeline.uploadChain = pipeline.uploadChain.catch(() => {}).then(uploadTask);
      return pipeline.uploadChain;
    },
    [],
  );

  const makeFlushPending = useCallback(
    (pipeline: MicPipeline) => (): Promise<void> | null => {
      const parts = pipeline.utterancePcmParts;
      if (parts.length === 0) return null;
      const merged = mergeFloat32Parts(parts);
      pipeline.utterancePcmParts = [];
      pipeline.silenceGapSamples = 0;

      const utteranceStartMs = pipeline.utteranceStartMs ?? Date.now();
      pipeline.utteranceStartMs = null;

      const inputRate = pipeline.audioCtx?.sampleRate ?? 44100;
      const { rms, peak } = pcmWindowSignalStats(merged);
      if (rms < MIN_FINAL_RMS || peak < MIN_FINAL_PEAK) {
        return null;
      }

      const resampled = downsample(merged, inputRate, TARGET_SAMPLE_RATE);
      const pcm16 = float32ToInt16(resampled);
      const durationSeconds = resampled.length / TARGET_SAMPLE_RATE;
      if (durationSeconds < MIN_UTTERANCE_SEC) {
        return null;
      }
      const finalStats = pcmWindowSignalStats(resampled);
      if (finalStats.dynamicRange < MIN_DYNAMIC_RANGE) {
        return null;
      }
      const sessionId = backendSessionIdRef.current;
      if (!sessionId) return null;

      const wavBlob = pcm16ToWavBlob(pcm16, TARGET_SAMPLE_RATE);
      return enqueueChunkUpload(
        pipeline,
        sessionId,
        wavBlob,
        durationSeconds,
        utteranceStartMs,
      );
    },
    [enqueueChunkUpload],
  );

  const setupMicPipeline = useCallback(
    async (pipeline: MicPipeline) => {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          deviceId: pipeline.deviceId ? { exact: pipeline.deviceId } : undefined,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: false,
          channelCount: 1,
        },
      });
      pipeline.mediaStream = stream;

      const ctx = new AudioContext();
      await ctx.resume();
      pipeline.audioCtx = ctx;

      const source = ctx.createMediaStreamSource(stream);
      pipeline.source = source;

      const analyser = ctx.createAnalyser();
      analyser.fftSize = 2048;
      analyser.smoothingTimeConstant = 0.8;
      source.connect(analyser);
      pipeline.analyser = analyser;

      pipeline.utterancePcmParts = [];
      pipeline.silenceGapSamples = 0;
      pipeline.utteranceStartMs = null;

      const flush = makeFlushPending(pipeline);
      flushHandlersRef.current.set(pipeline.micSource, flush);

      const processor = ctx.createScriptProcessor(4096, 1, 1);
      processor.onaudioprocess = (e) => {
        if (!isActiveRef.current) return;
        const inputRate = pipeline.audioCtx?.sampleRate ?? 44100;
        const buf = new Float32Array(e.inputBuffer.getChannelData(0));
        const stats = pcmWindowSignalStats(buf);
        const isSpeech =
          stats.rms >= SILENCE_RMS_MAX || stats.peak >= SILENCE_PEAK_MAX;
        const pauseSamples = Math.floor(inputRate * PAUSE_TO_FLUSH_SEC);

        if (isSpeech) {
          if (pipeline.utterancePcmParts.length === 0) {
            pipeline.utteranceStartMs = Date.now();
          }
          pipeline.utterancePcmParts.push(buf);
          pipeline.silenceGapSamples = 0;
          const total = pipeline.utterancePcmParts.reduce((n, c) => n + c.length, 0);
          if (total >= Math.floor(inputRate * MAX_UTTERANCE_SEC)) {
            void flushHandlersRef.current.get(pipeline.micSource)?.();
          }
        } else {
          pipeline.silenceGapSamples += buf.length;
          if (
            pipeline.utterancePcmParts.length > 0 &&
            pipeline.silenceGapSamples >= pauseSamples
          ) {
            void flushHandlersRef.current.get(pipeline.micSource)?.();
          }
        }
      };
      source.connect(processor);

      const silentGain = ctx.createGain();
      silentGain.gain.value = 0;
      processor.connect(silentGain);
      silentGain.connect(ctx.destination);
      pipeline.processor = processor;
    },
    [makeFlushPending],
  );

  const teardownPipeline = useCallback((pipeline: MicPipeline) => {
    pipeline.processor?.disconnect();
    pipeline.processor = null;
    pipeline.source?.disconnect();
    pipeline.source = null;
    pipeline.analyser = null;
    pipeline.audioCtx?.close().catch(() => {});
    pipeline.audioCtx = null;
    pipeline.mediaStream?.getTracks().forEach((t) => t.stop());
    pipeline.mediaStream = null;
    pipeline.utterancePcmParts = [];
    pipeline.silenceGapSamples = 0;
    pipeline.utteranceStartMs = null;
    flushHandlersRef.current.delete(pipeline.micSource);
  }, []);

  const teardownAllAudio = useCallback(() => {
    stopLevelMonitor();
    for (const pipeline of pipelinesRef.current.values()) {
      teardownPipeline(pipeline);
    }
    pipelinesRef.current.clear();
    chunkMetaRef.current.clear();
  }, [stopLevelMonitor, teardownPipeline]);

  const setupAllAudio = useCallback(async () => {
    const dualConfig = loadDualMicConfig();
    const pipelines = new Map<MicSourceId, MicPipeline>();

    if (dualConfig.enabled) {
      const connected = await detectConnectedMics(dualConfig);
      if (connected.sources.length === 0) {
        throw new Error(
          'No microphones detected. Connect VoiceMeeter outputs and select devices in Settings → Audio.',
        );
      }
      setMicSpeakers(connected.sources);
      dualMicActiveRef.current = connected.sources.length > 1;
      for (const source of connected.sources) {
        const deviceId = connected.deviceIds[source] ?? '';
        pipelines.set(source, createMicPipeline(source, deviceId));
      }
    } else {
      dualMicActiveRef.current = false;
      pipelines.set(MIC_1_SOURCE, createMicPipeline(MIC_1_SOURCE, ''));
    }

    pipelinesRef.current = pipelines;
    await Promise.all(
      Array.from(pipelines.values()).map((p) => setupMicPipeline(p)),
    );
    startLevelMonitor();
  }, [setupMicPipeline, startLevelMonitor, setMicSpeakers]);

  const finalizeAllOpenSentences = useCallback(() => {
    for (const pipeline of pipelinesRef.current.values()) {
      if (pipeline.sentenceId && pipeline.sentenceBase) {
        upsertStreamingRef.current(
          pipeline.sentenceId,
          pipeline.sentenceBase,
          true,
          pipeline.speakerId,
          pipeline.utteranceStartMs ?? Date.now(),
        );
      }
      pipeline.sentenceId = null;
      pipeline.sentenceBase = '';
    }
  }, []);

  const flushAllPending = useCallback(async () => {
    const tasks: Promise<void>[] = [];
    for (const flush of flushHandlersRef.current.values()) {
      const result = flush();
      if (result) tasks.push(result.catch(() => {}));
    }
    await Promise.all(tasks);
    await Promise.all(
      Array.from(pipelinesRef.current.values()).map((p) =>
        p.uploadChain.catch(() => {}),
      ),
    );
  }, []);

  const startRecording = useCallback(async () => {
    try {
      const now = new Date();
      const sessionName = buildSessionName(now);
      const dualConfig = loadDualMicConfig();

      setRecordingError(null);
      setSessionStartTime(now);
      setIsRecording(true);
      setIsPaused(false);
      setWsConnected(false);
      setBackendSessionId(null);
      clearTranscriptions();
      clearLiveNotes();
      clearVoiceTelemetryQueries();
      dismissSavedToast();

      getLogTelemetryScenarios()
        .then((info) => {
          setTelemetryScenariosInfo(info.scenarios, info.default_scenario);
        })
        .catch(() => {
          // Non-blocking if log telemetry is not configured.
        });

      globalChunkSequenceRef.current = 0;
      chunkMetaRef.current.clear();
      sessionNameRef.current = sessionName;

      await setupAllAudio();

      const micCount = pipelinesRef.current.size;
      const session = await createSession(
        sessionName,
        dualConfig.enabled
          ? micCount > 1
            ? 'Dual VoiceMeeter inputs (mic_1 + mic_2) with backend STT.'
            : 'Single VoiceMeeter input with backend STT.'
          : 'Browser microphone recording routed through backend STT.',
      );
      backendSessionIdRef.current = session.id;
      setBackendSessionId(session.id);

      wsConnectionRef.current = connectSessionWs(session.id, {
        onOpen: () => setWsConnected(true),
        onClose: () => setWsConnected(false),
        onError: () => setWsConnected(false),
        onMessage: (msg) =>
          handleWsMessage({
            event: msg.event,
            data: msg.data as Record<string, unknown>,
          }),
      });

      isActiveRef.current = true;
    } catch (err) {
      teardownAllAudio();
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
          'No microphone found. Please connect VoiceMeeter outputs and try again.',
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
    setupAllAudio,
    teardownAllAudio,
    clearTranscriptions,
    clearLiveNotes,
    clearVoiceTelemetryQueries,
    setTelemetryScenariosInfo,
    dismissSavedToast,
    handleWsMessage,
  ]);

  const pauseRecording = useCallback(() => {
    isActiveRef.current = false;
    for (const flush of flushHandlersRef.current.values()) {
      void flush();
    }
    for (const pipeline of pipelinesRef.current.values()) {
      pipeline.audioCtx?.suspend();
    }
    stopLevelMonitor();
    updateAudioLevel(0);
    setIsPaused(true);
  }, [updateAudioLevel, setIsPaused, stopLevelMonitor]);

  const resumeRecording = useCallback(() => {
    setIsPaused(false);
    isActiveRef.current = true;
    for (const pipeline of pipelinesRef.current.values()) {
      pipeline.audioCtx?.resume();
    }
    startLevelMonitor();
  }, [setIsPaused, startLevelMonitor]);

  const stopRecording = useCallback(async () => {
    isActiveRef.current = false;
    finalizeAllOpenSentences();
    await flushAllPending();
    teardownAllAudio();

    let finishedSessionName = sessionNameRef.current;
    if (backendSessionId) {
      try {
        const endedSession = await endSession(backendSessionId);
        finishedSessionName = endedSession.name;
      } catch {
        // Non-blocking
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
    clearVoiceTelemetryQueries();
    chunkMetaRef.current.clear();
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
    clearVoiceTelemetryQueries,
    showSavedToast,
    setSessionStartTime,
    teardownAllAudio,
    finalizeAllOpenSentences,
    flushAllPending,
  ]);

  useEffect(() => {
    return () => {
      teardownAllAudio();
      wsConnectionRef.current?.close();
      wsConnectionRef.current = null;
    };
  }, [teardownAllAudio]);

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
