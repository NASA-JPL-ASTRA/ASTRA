import { create } from 'zustand';
import type { Session, LogEntry, TelemetryStream, BackendNote } from '../types';
import {
  sessions as mockSessions,
  logEntries as mockLogs,
  telemetryStreams as mockTelemetry,
} from '../mock/data';
import { DEFAULT_STT_MODEL, isSupportedSttModel } from '../config/sttModels';

export interface LiveTranscription {
  id: string;
  timestamp: Date;
  speakerId: string;
  rawText: string;
  confidence: number;
  isFinal: boolean;
}

export interface SpeakerProfile {
  id: string;
  name: string;
  color: string;
}

interface AppState {
  // Session
  currentSessionId: string | null;
  backendSessionId: string | null;
  sessions: Session[];
  logs: LogEntry[];
  telemetryStreams: TelemetryStream[];

  // Recording & Audio
  isRecording: boolean;
  isPaused: boolean;
  isMuted: boolean;
  audioLevel: number;
  recordingError: string | null;
  sessionStartTime: Date | null;
  selectedSttModel: string;

  // WebSocket
  wsConnected: boolean;

  // Live transcriptions from Whisper
  transcriptions: LiveTranscription[];
  speakers: SpeakerProfile[];
  activeSpeakerId: string;

  // Live notes from backend (during active session)
  liveNotes: BackendNote[];

  // UI
  sidebarCollapsed: boolean;
  sidebarWidth: number;
  savedSessionToast: string | null;

  // Actions
  setCurrentSession: (id: string | null) => void;
  setBackendSessionId: (id: string | null) => void;
  setIsRecording: (value: boolean) => void;
  toggleRecording: () => void;
  setIsPaused: (value: boolean) => void;
  toggleMute: () => void;
  toggleSidebar: () => void;
  setSidebarWidth: (width: number) => void;
  updateLog: (id: string, content: string) => void;
  addLog: (log: LogEntry) => void;
  setWsConnected: (connected: boolean) => void;
  addTranscription: (entry: LiveTranscription) => void;
  updateLiveTranscription: (id: string, newText: string) => void;
  upsertStreamingTranscription: (
    id: string,
    transcript: string,
    isFinal: boolean,
    speakerId?: string,
  ) => void;
  setActiveSpeaker: (speakerId: string) => void;
  addSpeaker: () => void;
  updateSpeaker: (
    speakerId: string,
    updates: Partial<Pick<SpeakerProfile, 'name' | 'color'>>,
  ) => void;
  removeSpeaker: (speakerId: string) => void;
  setTranscriptionSpeaker: (transcriptionId: string, speakerId: string) => void;
  clearTranscriptions: () => void;
  addLiveNote: (note: BackendNote) => void;
  updateLiveNote: (noteId: string, note: BackendNote) => void;
  removeLiveNote: (noteId: string) => void;
  clearLiveNotes: () => void;
  updateAudioLevel: (level: number) => void;
  setRecordingError: (error: string | null) => void;
  setSessionStartTime: (time: Date | null) => void;
  setSelectedSttModel: (model: string) => void;
  showSavedToast: (label: string) => void;
  dismissSavedToast: () => void;
  deleteSession: (id: string) => void;
  getSessionById: (id: string) => Session | undefined;
  updateSession: (id: string, updates: { name?: string; description?: string; summary?: string }) => void;
  updateSessionTranscription: (sessionId: string, transcriptionId: string, newText: string) => void;
}

const STT_MODEL_STORAGE_KEY = 'astra.sttModel';
const SPEAKER_PALETTE = [
  '#00d4ff',
  '#00e676',
  '#b388ff',
  '#ffab00',
  '#ff5252',
  '#4dd0e1',
  '#64ffda',
  '#f06292',
];
const DEFAULT_SPEAKER_ID = 'speaker_0';

const defaultSpeakers: SpeakerProfile[] = [
  {
    id: DEFAULT_SPEAKER_ID,
    name: 'Speaker 1',
    color: SPEAKER_PALETTE[0],
  },
];

function loadInitialSttModel(): string {
  if (typeof window === 'undefined') return DEFAULT_STT_MODEL;
  const stored = window.localStorage.getItem(STT_MODEL_STORAGE_KEY);
  return stored && isSupportedSttModel(stored) ? stored : DEFAULT_STT_MODEL;
}

export const useStore = create<AppState>((set, get) => ({
  currentSessionId: 'sess1',
  backendSessionId: null,
  sessions: mockSessions,
  logs: mockLogs,
  telemetryStreams: mockTelemetry,

  isRecording: false,
  isPaused: false,
  isMuted: false,
  audioLevel: 0,
  recordingError: null,
  sessionStartTime: null,
  selectedSttModel: loadInitialSttModel(),

  wsConnected: false,

  transcriptions: [],
  speakers: defaultSpeakers,
  activeSpeakerId: DEFAULT_SPEAKER_ID,
  liveNotes: [],

  sidebarCollapsed: false,
  sidebarWidth: 240,
  savedSessionToast: null,

  setCurrentSession: (id) => set({ currentSessionId: id }),
  setBackendSessionId: (id) => set({ backendSessionId: id }),
  setIsRecording: (value) => set({ isRecording: value }),
  toggleRecording: () => set((s) => ({ isRecording: !s.isRecording })),
  setIsPaused: (value) => set({ isPaused: value }),
  toggleMute: () => set((s) => ({ isMuted: !s.isMuted })),
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  setSidebarWidth: (width) =>
    set({ sidebarWidth: Math.min(360, Math.max(180, width)) }),
  updateLog: (id, content) =>
    set((s) => ({
      logs: s.logs.map((log) =>
        log.id === id ? { ...log, content, isEdited: true } : log
      ),
    })),
  addLog: (log) => set((s) => ({ logs: [log, ...s.logs] })),
  setWsConnected: (connected) => set({ wsConnected: connected }),
  addTranscription: (entry) =>
    set((s) => ({ transcriptions: [...s.transcriptions, entry] })),
  updateLiveTranscription: (id, newText) =>
    set((s) => ({
      transcriptions: s.transcriptions.map((t) =>
        t.id === id ? { ...t, rawText: newText } : t
      ),
    })),
  upsertStreamingTranscription: (id, transcript, isFinal, speakerId) =>
    set((s) => {
      const exists = s.transcriptions.some((t) => t.id === id);
      const resolvedSpeakerId = speakerId ?? s.activeSpeakerId;
      if (exists) {
        return {
          transcriptions: s.transcriptions.map((t) =>
            t.id === id
              ? {
                  ...t,
                  rawText: transcript,
                  isFinal,
                  speakerId: speakerId ?? t.speakerId,
                }
              : t
          ),
        };
      }
      return {
        transcriptions: [
          ...s.transcriptions,
          {
            id,
            timestamp: new Date(),
            speakerId: resolvedSpeakerId,
            rawText: transcript,
            confidence: 0.9,
            isFinal,
          },
        ],
      };
    }),
  setActiveSpeaker: (speakerId) =>
    set((s) =>
      s.speakers.some((speaker) => speaker.id === speakerId)
        ? { activeSpeakerId: speakerId }
        : {}
    ),
  addSpeaker: () =>
    set((s) => {
      const nextIndex = s.speakers.length + 1;
      const id = `speaker_${Date.now().toString(36)}_${nextIndex}`;
      const speaker = {
        id,
        name: `Speaker ${nextIndex}`,
        color: SPEAKER_PALETTE[s.speakers.length % SPEAKER_PALETTE.length],
      };
      return {
        speakers: [...s.speakers, speaker],
        activeSpeakerId: id,
      };
    }),
  updateSpeaker: (speakerId, updates) =>
    set((s) => ({
      speakers: s.speakers.map((speaker) =>
        speaker.id === speakerId
          ? {
              ...speaker,
              ...updates,
            }
          : speaker
      ),
    })),
  removeSpeaker: (speakerId) =>
    set((s) => {
      if (s.speakers.length <= 1) return {};
      const remaining = s.speakers.filter((speaker) => speaker.id !== speakerId);
      if (remaining.length === s.speakers.length) return {};
      const fallbackId = remaining[0].id;
      return {
        speakers: remaining,
        activeSpeakerId:
          s.activeSpeakerId === speakerId ? fallbackId : s.activeSpeakerId,
        transcriptions: s.transcriptions.map((entry) =>
          entry.speakerId === speakerId
            ? { ...entry, speakerId: fallbackId }
            : entry
        ),
      };
    }),
  setTranscriptionSpeaker: (transcriptionId, speakerId) =>
    set((s) => {
      if (!s.speakers.some((speaker) => speaker.id === speakerId)) return {};
      return {
        transcriptions: s.transcriptions.map((entry) =>
          entry.id === transcriptionId ? { ...entry, speakerId } : entry
        ),
      };
    }),
  clearTranscriptions: () => set({ transcriptions: [] }),
  addLiveNote: (note) =>
    set((s) => ({ liveNotes: [...s.liveNotes, note] })),
  updateLiveNote: (noteId, note) =>
    set((s) => ({
      liveNotes: s.liveNotes.map((n) => (n.id === noteId ? note : n)),
    })),
  removeLiveNote: (noteId) =>
    set((s) => ({
      liveNotes: s.liveNotes.filter((n) => n.id !== noteId),
    })),
  clearLiveNotes: () => set({ liveNotes: [] }),
  updateAudioLevel: (level) => set({ audioLevel: level }),
  setRecordingError: (error) => set({ recordingError: error }),
  setSessionStartTime: (time) => set({ sessionStartTime: time }),
  setSelectedSttModel: (model) => {
    if (!isSupportedSttModel(model)) return;
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(STT_MODEL_STORAGE_KEY, model);
    }
    set({ selectedSttModel: model });
  },
  showSavedToast: (label) => set({ savedSessionToast: label }),

  dismissSavedToast: () => set({ savedSessionToast: null }),

  deleteSession: (id) =>
    set((s) => ({
      sessions: s.sessions.filter((sess) => sess.id !== id),
    })),

  getSessionById: (id) => get().sessions.find((s) => s.id === id),

  updateSession: (id, updates) =>
    set((s) => ({
      sessions: s.sessions.map((sess) =>
        sess.id === id ? { ...sess, ...updates } : sess
      ),
    })),

  updateSessionTranscription: (sessionId, transcriptionId, newText) =>
    set((s) => ({
      sessions: s.sessions.map((sess) =>
        sess.id === sessionId && sess.transcriptions
          ? {
              ...sess,
              transcriptions: sess.transcriptions.map((t) =>
                t.id === transcriptionId ? { ...t, rawText: newText } : t
              ),
            }
          : sess
      ),
    })),
}));
