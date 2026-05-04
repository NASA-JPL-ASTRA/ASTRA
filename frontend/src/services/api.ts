import { API_URL } from '../config/env';
import type { BackendNote, NoteType } from '../types';

// ── Session types ──

export interface BackendSession {
  id: string;
  name: string;
  description: string | null;
  status: 'active' | 'ended';
  started_at: string;
  ended_at: string | null;
  note_count: number;
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
