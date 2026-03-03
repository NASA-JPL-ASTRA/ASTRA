import { create } from 'zustand';
import type { Session, LogEntry, TelemetryStream, SavedTranscription, BackendNote } from '../types';
import {
  sessions as mockSessions,
  logEntries as mockLogs,
  telemetryStreams as mockTelemetry,
} from '../mock/data';

export interface LiveTranscription {
  id: string;
  timestamp: Date;
  speakerId: string;
  rawText: string;
  confidence: number;
  isFinal: boolean;
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

  // WebSocket
  wsConnected: boolean;

  // Live transcriptions from Whisper
  transcriptions: LiveTranscription[];

  // Live notes from backend (during active session)
  liveNotes: BackendNote[];

  // UI
  sidebarCollapsed: boolean;
  savedSessionToast: string | null;

  // Actions
  setCurrentSession: (id: string | null) => void;
  setBackendSessionId: (id: string | null) => void;
  setIsRecording: (value: boolean) => void;
  toggleRecording: () => void;
  setIsPaused: (value: boolean) => void;
  toggleMute: () => void;
  toggleSidebar: () => void;
  updateLog: (id: string, content: string) => void;
  addLog: (log: LogEntry) => void;
  setWsConnected: (connected: boolean) => void;
  addTranscription: (entry: LiveTranscription) => void;
  updateLiveTranscription: (id: string, newText: string) => void;
  clearTranscriptions: () => void;
  addLiveNote: (note: BackendNote) => void;
  updateLiveNote: (noteId: string, note: BackendNote) => void;
  removeLiveNote: (noteId: string) => void;
  clearLiveNotes: () => void;
  updateAudioLevel: (level: number) => void;
  setRecordingError: (error: string | null) => void;
  setSessionStartTime: (time: Date | null) => void;
  saveSessionToHistory: () => void;
  dismissSavedToast: () => void;
  deleteSession: (id: string) => void;
  getSessionById: (id: string) => Session | undefined;
  updateSession: (id: string, updates: { name?: string; description?: string; summary?: string }) => void;
  updateSessionTranscription: (sessionId: string, transcriptionId: string, newText: string) => void;
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

  wsConnected: false,

  transcriptions: [],
  liveNotes: [],

  sidebarCollapsed: false,
  savedSessionToast: null,

  setCurrentSession: (id) => set({ currentSessionId: id }),
  setBackendSessionId: (id) => set({ backendSessionId: id }),
  setIsRecording: (value) => set({ isRecording: value }),
  toggleRecording: () => set((s) => ({ isRecording: !s.isRecording })),
  setIsPaused: (value) => set({ isPaused: value }),
  toggleMute: () => set((s) => ({ isMuted: !s.isMuted })),
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
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

  saveSessionToHistory: () => {
    const state = get();
    if (state.transcriptions.length === 0) return;

    const now = new Date();
    const startTime = state.sessionStartTime || state.transcriptions[0].timestamp;
    const sessionId = `sess_${Date.now()}`;
    const sessionName = `REC-${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}-${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}`;

    const savedTranscriptions: SavedTranscription[] = state.transcriptions.map((t) => ({
      id: t.id,
      timestamp: t.timestamp.toISOString(),
      speakerId: t.speakerId,
      rawText: t.rawText,
      confidence: t.confidence,
      isFinal: t.isFinal,
    }));

    const newSession: Session = {
      id: sessionId,
      name: sessionName,
      description: `Auto-saved session with ${state.transcriptions.length} transcription entries`,
      startTime,
      endTime: now,
      status: 'completed',
      operators: [],
      logCount: state.transcriptions.length,
      telemetryStreams: 0,
      testbed: 'Active Testbed',
      transcriptions: savedTranscriptions,
    };

    set((s) => ({
      sessions: [newSession, ...s.sessions],
      savedSessionToast: sessionName,
      transcriptions: [],
      sessionStartTime: null,
    }));
  },

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
