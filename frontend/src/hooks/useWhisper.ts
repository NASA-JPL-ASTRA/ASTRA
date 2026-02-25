import { useCallback, useRef, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { APP_MODE } from '../config/env';
import { createSession, endSession } from '../services/api';
import { connectSessionWs, type SessionWsConnection } from '../services/sessionWs';

/**
 * Mock transcription sentences for testing.
 * When a real Whisper backend is available, set MOCK_MODE = false
 * and the original WebSocket + audio capture code will be used.
 */
const MOCK_SENTENCES = [
  { speaker: 'speaker_0', text: 'Initiating system diagnostics on panel Alpha-3. All indicators are showing nominal.' },
  { speaker: 'speaker_1', text: 'Confirmed. Telemetry link is stable. Signal strength at ninety-two percent.' },
  { speaker: 'speaker_0', text: 'Running thermal sweep on the reaction wheel assembly. Temperature reads twenty-eight point three degrees.' },
  { speaker: 'speaker_1', text: 'Copy that. I see a slight drift on gyroscope channel two. Monitoring closely.' },
  { speaker: 'speaker_2', text: 'Power distribution looks good. Solar array output at four point seven kilowatts.' },
  { speaker: 'speaker_0', text: 'ASTRA, log current voltage readings on all power rails.' },
  { speaker: 'speaker_1', text: 'Switching to backup antenna for the next communication window.' },
  { speaker: 'speaker_2', text: 'Ground station reports clear skies. Uplink margin is healthy.' },
  { speaker: 'speaker_0', text: 'Beginning actuator stress test sequence. Load profile set to standard.' },
  { speaker: 'speaker_1', text: 'Vibration levels are within spec. No anomalous frequencies detected so far.' },
  { speaker: 'speaker_0', text: 'Mark the current timestamp. We are starting the endurance phase now.' },
  { speaker: 'speaker_2', text: 'Data recorder is running. Storage utilization at thirty-seven percent.' },
  { speaker: 'speaker_1', text: 'Joint four encoder showing clean output. Resolution test passed at zero point one degrees.' },
  { speaker: 'speaker_0', text: 'Good. Proceeding to the mobility test. Wheels to nominal speed.' },
  { speaker: 'speaker_2', text: 'All navigation cameras are online. Image quality is excellent across the board.' },
  { speaker: 'speaker_0', text: 'Adjusting arm position to configuration Delta. Torque limits at forty-five newton meters.' },
  { speaker: 'speaker_1', text: 'Noticing minor oscillation in IMU accelerometer data. Could be a grounding issue.' },
  { speaker: 'speaker_2', text: 'Battery charge at seventy-eight percent. Estimated runtime is four hours twenty minutes.' },
  { speaker: 'speaker_0', text: 'Copy. Running isolation test on the IMU power supply line.' },
  { speaker: 'speaker_1', text: 'Isolation test complete. Noise floor improved. The oscillation was from the adjacent servo driver.' },
];

/**
 * Audio capture + transcription hook.
 *
 * In mock mode (default): generates random test transcriptions for UI testing.
 * In real mode: connects to Whisper backend via WebSocket + captures audio.
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
  } = useStore();

  const mockTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const audioTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const wsConnectionRef = useRef<SessionWsConnection | null>(null);
  const mockIndexRef = useRef(0);
  const isActiveRef = useRef(false);

  const addTranscriptionRef = useRef(addTranscription);
  useEffect(() => {
    addTranscriptionRef.current = addTranscription;
  }, [addTranscription]);

  const scheduleMockEntry = useCallback(() => {
    const delay = 2500 + Math.random() * 2500;
    mockTimerRef.current = setTimeout(() => {
      if (!isActiveRef.current) return;

      const entry = MOCK_SENTENCES[mockIndexRef.current % MOCK_SENTENCES.length];
      addTranscriptionRef.current({
        id: `tr_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
        timestamp: new Date(),
        speakerId: entry.speaker,
        rawText: entry.text,
        confidence: 0.85 + Math.random() * 0.14,
        isFinal: Math.random() > 0.08,
      });
      mockIndexRef.current++;

      if (isActiveRef.current) {
        scheduleMockEntry();
      }
    }, delay);
  }, []);

  const startRecording = useCallback(async () => {
    try {
      setRecordingError(null);
      setSessionStartTime(new Date());
      setIsRecording(true);
      setIsPaused(false);
      setWsConnected(false);
      setBackendSessionId(null);

      if (APP_MODE === 'live') {
        const session = await createSession('Frontend Live Session');
        setBackendSessionId(session.id);

        wsConnectionRef.current = connectSessionWs(session.id, {
          onOpen: () => setWsConnected(true),
          onClose: () => setWsConnected(false),
          onError: () => setWsConnected(false),
          onMessage: () => {
            // This step only establishes connectivity. Event-to-UI mapping
            // can be expanded incrementally in page/store integration.
          },
        });
      } else {
        setWsConnected(true);
      }

      isActiveRef.current = true;
      mockIndexRef.current = 0;

      audioTimerRef.current = setInterval(() => {
        if (isActiveRef.current) {
          updateAudioLevel(0.05 + Math.random() * 0.45);
        }
      }, 100);

      setTimeout(() => scheduleMockEntry(), 1200);
    } catch (err) {
      wsConnectionRef.current?.close();
      wsConnectionRef.current = null;
      setBackendSessionId(null);
      updateAudioLevel(0);
      setIsRecording(false);
      setIsPaused(false);
      setWsConnected(false);
      setSessionStartTime(null);
      const msg = err instanceof Error ? err.message : 'Failed to start recording';
      setRecordingError(msg);
    }
  }, [
    setRecordingError,
    setSessionStartTime,
    setIsRecording,
    setIsPaused,
    setWsConnected,
    setBackendSessionId,
    updateAudioLevel,
    scheduleMockEntry,
  ]);

  const pauseRecording = useCallback(() => {
    isActiveRef.current = false;
    if (mockTimerRef.current) {
      clearTimeout(mockTimerRef.current);
      mockTimerRef.current = null;
    }
    updateAudioLevel(0);
    setIsPaused(true);
  }, [updateAudioLevel, setIsPaused]);

  const resumeRecording = useCallback(() => {
    setIsPaused(false);
    isActiveRef.current = true;
    setTimeout(() => scheduleMockEntry(), 500);
  }, [setIsPaused, scheduleMockEntry]);

  const stopRecording = useCallback(async () => {
    isActiveRef.current = false;

    if (mockTimerRef.current) {
      clearTimeout(mockTimerRef.current);
      mockTimerRef.current = null;
    }
    if (audioTimerRef.current) {
      clearInterval(audioTimerRef.current);
      audioTimerRef.current = null;
    }

    if (APP_MODE === 'live' && backendSessionId) {
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
  ]);

  useEffect(() => {
    return () => {
      if (mockTimerRef.current) clearTimeout(mockTimerRef.current);
      if (audioTimerRef.current) clearInterval(audioTimerRef.current);
      wsConnectionRef.current?.close();
      wsConnectionRef.current = null;
    };
  }, []);

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
