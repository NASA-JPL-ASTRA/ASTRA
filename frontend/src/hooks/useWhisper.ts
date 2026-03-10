import { useCallback, useRef, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { createSession, endSession, uploadSttChunk } from '../services/api';
import { connectSessionWs, type SessionWsConnection } from '../services/sessionWs';

/** VAD 参数：与 realtime_demo 一致 - 有语音才发送 */
const FRAME_DURATION_MS = 30;
const SILENCE_SEC = 1.5;
const MIN_SPEECH_SEC = 0.45;
/** 能量阈值 (Float32 RMS)：高于此值视为语音，可随环境微调 */
const SPEECH_RMS_THRESHOLD = 0.012;

const TARGET_SAMPLE_RATE = 16000;
const LEVEL_UPDATE_INTERVAL_MS = 80;

/**
 * Compute RMS of a Float32 frame (energy-based VAD).
 */
function computeRms(frame: Float32Array): number {
  let sumSq = 0;
  for (let i = 0; i < frame.length; i++) sumSq += frame[i] * frame[i];
  return Math.sqrt(sumSq / frame.length);
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
    setRecordingError,
    setIsRecording,
    setIsPaused,
    setWsConnected,
    setBackendSessionId,
    addTranscription,
    clearTranscriptions,
    updateAudioLevel,
    setSessionStartTime,
    saveSessionToHistory,
  } = useStore();

  // ── Audio capture refs ──
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const processorRef = useRef<AudioWorkletNode | null>(null);
  const levelTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  /** 原始 PCM 暂存，用于 VAD 帧提取 */
  const stagingChunksRef = useRef<Float32Array[]>([]);
  /** 当前语句 buffer（语音 + 尾随静音），满足条件时发送 */
  const utteranceChunksRef = useRef<Float32Array[]>([]);
  /** VAD 状态：与 realtime_demo 一致 */
  const vadStateRef = useRef({
    inSpeech: false,
    speechFrames: 0,
    silenceFrames: 0,
  });

  // ── Connection refs ──
  const wsConnectionRef = useRef<SessionWsConnection | null>(null);
  const backendSessionIdRef = useRef<string | null>(null);

  const isActiveRef = useRef(false);

  const addTranscriptionRef = useRef(addTranscription);
  useEffect(() => {
    addTranscriptionRef.current = addTranscription;
  }, [addTranscription]);

  // Keep backendSessionIdRef in sync with store
  useEffect(() => {
    backendSessionIdRef.current = backendSessionId;
  }, [backendSessionId]);

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

  // ── PCM 发送（合并、重采样、上传）──

  const sendAudioChunk = useCallback(
    async (chunks: Float32Array[]) => {
      if (chunks.length === 0) return;

      const totalLen = chunks.reduce((n, c) => n + c.length, 0);
      const merged = new Float32Array(totalLen);
      let offset = 0;
      for (const c of chunks) {
        merged.set(c, offset);
        offset += c.length;
      }

      const inputRate = audioCtxRef.current?.sampleRate ?? 44100;
      const resampled = downsample(merged, inputRate, TARGET_SAMPLE_RATE);
      const pcm16 = float32ToInt16(resampled);

      if (import.meta.env.DEV) {
        console.debug(
          `[ASTRA] VAD chunk: ${(resampled.length / TARGET_SAMPLE_RATE).toFixed(1)}s, ` +
            `${pcm16.byteLength} bytes PCM16 @ ${TARGET_SAMPLE_RATE}Hz`,
        );
      }

      const sid = backendSessionIdRef.current;
      if (sid) {
        try {
          await uploadSttChunk(sid, pcm16, TARGET_SAMPLE_RATE, `chunk_${Date.now()}`);
        } catch (err) {
          if (import.meta.env.DEV) {
            console.error('[ASTRA] STT upload failed:', err);
          }
          setRecordingError(err instanceof Error ? err.message : 'STT upload failed');
        }
      }
    },
    [setRecordingError],
  );

  // ── VAD 帧处理：有语音 + 约 1.5s 静音后发送（与 realtime_demo 一致）──

  const processVadOnPcm = useCallback(
    (pcm: Float32Array) => {
      const sampleRate = audioCtxRef.current?.sampleRate ?? 44100;
      const frameSize = Math.round(sampleRate * (FRAME_DURATION_MS / 1000));
      const silenceThresholdFrames = Math.round((SILENCE_SEC * 1000) / FRAME_DURATION_MS);
      const minSpeechFrames = Math.round((MIN_SPEECH_SEC * 1000) / FRAME_DURATION_MS);

      stagingChunksRef.current.push(pcm);
      const staging = stagingChunksRef.current;
      const totalLen = staging.reduce((n, c) => n + c.length, 0);
      if (totalLen < frameSize) return;

      // 合并并提取完整帧
      const merged = new Float32Array(totalLen);
      let off = 0;
      for (const c of staging) {
        merged.set(c, off);
        off += c.length;
      }
      stagingChunksRef.current = [];

      const state = vadStateRef.current;
      let readOffset = 0;

      while (readOffset + frameSize <= merged.length) {
        const frame = merged.subarray(readOffset, readOffset + frameSize);
        readOffset += frameSize;

        const rms = computeRms(frame);
        const isSpeech = rms > SPEECH_RMS_THRESHOLD;

        if (isSpeech) {
          utteranceChunksRef.current.push(new Float32Array(frame));
          state.silenceFrames = 0;
          state.inSpeech = true;
          state.speechFrames++;
        } else if (state.inSpeech) {
          utteranceChunksRef.current.push(new Float32Array(frame));
          state.silenceFrames++;

          if (state.silenceFrames >= silenceThresholdFrames) {
            if (state.speechFrames >= minSpeechFrames) {
              const toSend = utteranceChunksRef.current;
              utteranceChunksRef.current = [];
              sendAudioChunk(toSend);
            }
            state.inSpeech = false;
            state.speechFrames = 0;
            state.silenceFrames = 0;
            utteranceChunksRef.current = [];
          }
        }
      }

      if (readOffset < merged.length) {
        stagingChunksRef.current = [merged.subarray(readOffset)];
      }
    },
    [sendAudioChunk],
  );

  /** 停止录音时发送未完成的 utterance */
  const flushRemainingUtterance = useCallback(async () => {
    const chunks = utteranceChunksRef.current;
    const state = vadStateRef.current;
    if (chunks.length > 0 && state.speechFrames >= Math.round((MIN_SPEECH_SEC * 1000) / FRAME_DURATION_MS)) {
      utteranceChunksRef.current = [];
      vadStateRef.current = { inSpeech: false, speechFrames: 0, silenceFrames: 0 };
      await sendAudioChunk(chunks);
    }
  }, [sendAudioChunk]);

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

    // AudioWorkletNode captures raw PCM (replaces deprecated ScriptProcessorNode)
    await ctx.audioWorklet.addModule('/pcm-processor.js');
    const processor = new AudioWorkletNode(ctx, 'pcm-processor');
    processor.port.onmessage = (e) => {
      if (!isActiveRef.current) return;
      const { pcm } = e.data;
      if (pcm) processVadOnPcm(pcm);
    };
    source.connect(processor);

    // Route through a silent gain so the processor fires without speaker output
    const silentGain = ctx.createGain();
    silentGain.gain.value = 0;
    processor.connect(silentGain);
    silentGain.connect(ctx.destination);
    processorRef.current = processor;

    startLevelMonitor();
  }, [processVadOnPcm, startLevelMonitor]);

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

    stagingChunksRef.current = [];
    utteranceChunksRef.current = [];
    vadStateRef.current = { inSpeech: false, speechFrames: 0, silenceFrames: 0 };
  }, [stopLevelMonitor]);

  // ── Main control functions ──

  const startRecording = useCallback(async () => {
    try {
      setRecordingError(null);
      clearTranscriptions(); // 新会话清空之前的转写
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
          if (msg.event === 'stt.task.done') {
            const data = msg.data as Record<string, unknown>;
            const transcript =
              typeof data.transcript === 'string' && data.transcript
                ? data.transcript
                : '—';
            const rawConf = data.confidence;
            const confidence =
              transcript === '—'
                ? 0
                : typeof rawConf === 'number'
                  ? Math.min(1, Math.max(0, rawConf))
                  : 0.9;
            // 低于 50% 置信度不展示（含噪音幻觉如 "We'll see you next time"）
            if (confidence < 0.5) return;
            addTranscriptionRef.current({
              id: String(data.id ?? `tr_${Date.now()}`),
              timestamp: new Date(),
              speakerId: 'speaker_0',
              rawText: transcript,
              confidence,
              isFinal: true,
            });
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
    clearTranscriptions,
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

    // 发送未完成的 utterance（有语音但未满 1.5s 静音）
    await flushRemainingUtterance();

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
    setSessionStartTime(null);
  }, [
    backendSessionId,
    setBackendSessionId,
    updateAudioLevel,
    setIsRecording,
    setIsPaused,
    setWsConnected,
    saveSessionToHistory,
    setSessionStartTime,
    teardownAudio,
    flushRemainingUtterance,
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
