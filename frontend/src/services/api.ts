import { API_URL } from '../config/env';
import type { BackendNote, NoteType, StructureNoteDocument } from '../types';

// ── Session types ──

export interface BackendSession {
  id: string;
  name: string;
  description: string | null;
  status: 'active' | 'ended';
  started_at: string;
  ended_at: string | null;
  note_count: number;
  /** After background job: mock test_1 logs for voice/telemetry demos (repo-relative path). */
  telemetry_mock_test1_path?: string | null;
}

// ── Generic request helper ──

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
    ...init,
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`API ${response.status}: ${body || response.statusText}`);
  }

  return response.json() as Promise<T>;
}

async function requestText(path: string, init?: RequestInit): Promise<string> {
  const response = await fetch(`${API_URL}${path}`, { ...init });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`API ${response.status}: ${body || response.statusText}`);
  }

  return response.text();
}

// ── Sessions ──

export function createSession(
  name: string,
  description?: string,
): Promise<BackendSession> {
  const payload: { name: string; description?: string } = { name };
  if (description) payload.description = description;

  return request<BackendSession>('/sessions', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function listSessions(): Promise<BackendSession[]> {
  return request<BackendSession[]>('/sessions', { method: 'GET' });
}

export function getSession(sessionId: string): Promise<BackendSession> {
  return request<BackendSession>(`/sessions/${sessionId}`, { method: 'GET' });
}

export function endSession(sessionId: string): Promise<BackendSession> {
  return request<BackendSession>(`/sessions/${sessionId}`, {
    method: 'PATCH',
    body: JSON.stringify({ status: 'ended' }),
  });
}

// ── Notes ──

export interface CreateNotePayload {
  timestamp: string;
  speaker?: string;
  content: string;
  type?: NoteType;
  tags?: string[];
  telemetry_snapshot?: Record<string, unknown>;
}

export interface UpdateNotePayload {
  content?: string;
  speaker?: string;
  type?: NoteType;
  tags?: string[];
}

export function listNotes(sessionId: string): Promise<BackendNote[]> {
  return request<BackendNote[]>(`/sessions/${sessionId}/notes`, { method: 'GET' });
}

export function createNote(
  sessionId: string,
  payload: CreateNotePayload,
): Promise<BackendNote> {
  return request<BackendNote>(`/sessions/${sessionId}/notes`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateNote(
  sessionId: string,
  noteId: string,
  payload: UpdateNotePayload,
): Promise<BackendNote> {
  return request<BackendNote>(`/sessions/${sessionId}/notes/${noteId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export function deleteNote(
  sessionId: string,
  noteId: string,
): Promise<{ message: string }> {
  return request<{ message: string }>(`/sessions/${sessionId}/notes/${noteId}`, {
    method: 'DELETE',
  });
}

export function exportNotes(
  sessionId: string,
  format: 'markdown' | 'json' = 'markdown',
): Promise<string> {
  return requestText(`/sessions/${sessionId}/notes/export?format=${format}`, {
    method: 'GET',
  });
}

// ── Structure note (per session) ──

export function getStructureNote(sessionId: string): Promise<StructureNoteDocument> {
  return request<StructureNoteDocument>(`/sessions/${sessionId}/structure-note`, {
    method: 'GET',
  });
}

export function postStructureNoteVoiceChunk(
  sessionId: string,
  payload: { transcript: string; request_anomaly_capture?: boolean },
): Promise<StructureNoteDocument> {
  return request<StructureNoteDocument>(`/sessions/${sessionId}/structure-note/voice-chunk`, {
    method: 'POST',
    body: JSON.stringify({
      transcript: payload.transcript,
      request_anomaly_capture: payload.request_anomaly_capture ?? false,
    }),
  });
}

export function updateStructureNoteTestSummary(
  sessionId: string,
  contentMarkdown: string,
): Promise<StructureNoteDocument> {
  return request<StructureNoteDocument>(`/sessions/${sessionId}/structure-note/test-summary`, {
    method: 'PUT',
    body: JSON.stringify({ content_markdown: contentMarkdown }),
  });
}

export interface StructureNoteAutoUpdateResponse {
  document: StructureNoteDocument;
  last_note_id: string | null;
  processed_note_count: number;
}

export function autoUpdateStructureNoteTestSummary(
  sessionId: string,
  manualSummary: string,
  sinceNoteId?: string | null,
): Promise<StructureNoteAutoUpdateResponse> {
  return request<StructureNoteAutoUpdateResponse>(
    `/sessions/${sessionId}/structure-note/test-summary/auto-update`,
    {
      method: 'POST',
      body: JSON.stringify({
        manual_summary: manualSummary,
        mode: 'merge',
        since_note_id: sinceNoteId ?? null,
      }),
    },
  );
}

// ── Summary assistant ──

export interface SummaryChatMessagePayload {
  role: 'user' | 'assistant';
  content: string;
}

export interface SummaryChatResponse {
  message: string;
  updated_summary: string | null;
}

export function chatWithSummaryAssistant(
  sessionId: string,
  payload: {
    prompt: string;
    title?: string;
    summary?: string;
    manual_summary?: string;
    model?: string;
    messages?: SummaryChatMessagePayload[];
  },
): Promise<SummaryChatResponse> {
  return request<SummaryChatResponse>(`/sessions/${sessionId}/summary/chat`, {
    method: 'POST',
    body: JSON.stringify({
      prompt: payload.prompt,
      title: payload.title,
      summary: payload.summary,
      manual_summary: payload.manual_summary,
      model: payload.model,
      messages: payload.messages ?? [],
    }),
  });
}

// ── STT Upload ──

export async function uploadAudioChunk(
  sessionId: string,
  wavBlob: Blob,
  chunkId?: string,
  durationSeconds?: number,
  model?: string,
): Promise<unknown> {
  const form = new FormData();
  form.append('file', wavBlob, `${chunkId ?? 'chunk'}.wav`);
  if (chunkId) form.append('audio_chunk_id', chunkId);
  if (durationSeconds !== undefined)
    form.append('duration_seconds', String(durationSeconds));
  if (model) form.append('model', model);

  const response = await fetch(
    `${API_URL}/sessions/${sessionId}/stt/upload`,
    { method: 'POST', body: form },
  );

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`STT upload ${response.status}: ${body || response.statusText}`);
  }

  return response.json();
}

// ── Telemetry query API (GET /api/query/… — Influx + channel search) ──

export type TelemetryQueryResult<T> =
  | { ok: true; data: T }
  | { ok: false; status: number; message: string };

function parseTelemetryError(status: number, text: string): string {
  if (!text) return `API ${status}`;
  try {
    const parsed = JSON.parse(text) as { detail?: unknown; error?: unknown };
    if (typeof parsed?.detail === 'string') return parsed.detail;
    if (Array.isArray(parsed?.detail) && parsed.detail[0]?.msg) {
      return String(parsed.detail[0].msg);
    }
    if (typeof parsed?.error === 'string') return parsed.error;
  } catch {
    // not JSON
  }
  return text;
}

export async function fetchTelemetryQuery<T>(
  path: string,
): Promise<TelemetryQueryResult<T>> {
  const response = await fetch(`${API_URL}${path}`);
  const text = await response.text();
  if (!response.ok) {
    return {
      ok: false,
      status: response.status,
      message: parseTelemetryError(response.status, text),
    };
  }
  if (!text) {
    return { ok: true, data: [] as T };
  }
  return { ok: true, data: JSON.parse(text) as T };
}

export interface ChannelValueResponse {
  channel: string;
  value: number;
  timestamp: number;
}

export interface ChannelRangeResponse {
  channel: string;
  session_id: string;
  start: number;
  end: number;
  min: number;
  max: number;
  mean: number;
  last: number;
}

export interface EvrEventRow {
  timestamp: number;
  evr_name: string | null;
  severity: string | null;
  message: string;
}

export interface ChannelSearchHit {
  channel: string;
  score: number;
}

export interface TelemetryAskResponse {
  answer: string;
  plan: Record<string, unknown>;
  data: unknown;
  error: string | null;
}

export function getTelemetryQueryInfo(): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>('/query', { method: 'GET' });
}

export function askTelemetryQuestion(payload: {
  question: string;
  session?: string;
  t0?: number;
  t1?: number;
  at?: number;
  severity?: string;
  limit?: number;
  model?: string;
}): Promise<TelemetryAskResponse> {
  return request<TelemetryAskResponse>('/query/ask', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function queryChannelValue(
  sessionId: string,
  name: string,
  at: number,
): Promise<TelemetryQueryResult<ChannelValueResponse>> {
  const q = new URLSearchParams({
    session: sessionId,
    name,
    at: String(at),
  });
  return fetchTelemetryQuery<ChannelValueResponse>(`/query/channel?${q}`);
}

export function queryChannelRange(
  sessionId: string,
  name: string,
  t0: number,
  t1: number,
): Promise<TelemetryQueryResult<ChannelRangeResponse>> {
  const q = new URLSearchParams({
    session: sessionId,
    name,
    t0: String(t0),
    t1: String(t1),
  });
  return fetchTelemetryQuery<ChannelRangeResponse>(`/query/range?${q}`);
}

export function queryTelemetryEvents(
  sessionId: string,
  t0: number,
  t1: number,
  options?: { severity?: string; limit?: number },
): Promise<TelemetryQueryResult<EvrEventRow[]>> {
  const q = new URLSearchParams({
    session: sessionId,
    t0: String(t0),
    t1: String(t1),
  });
  if (options?.severity) q.set('severity', options.severity);
  if (options?.limit != null) q.set('limit', String(options.limit));
  return fetchTelemetryQuery<EvrEventRow[]>(`/query/events?${q}`);
}

export function searchTelemetryChannels(
  q: string,
  k: number = 3,
): Promise<TelemetryQueryResult<ChannelSearchHit[]>> {
  const params = new URLSearchParams({ q, k: String(k) });
  return fetchTelemetryQuery<ChannelSearchHit[]>(`/query/search?${params}`);
}
