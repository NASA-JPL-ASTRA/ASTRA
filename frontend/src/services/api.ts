import { API_URL } from '../config/env';

export interface BackendSession {
  id: string;
  name: string;
  description: string | null;
  status: 'active' | 'ended';
  started_at: string;
  ended_at: string | null;
}

interface CreateSessionPayload {
  name: string;
  description?: string;
}

interface EndSessionPayload {
  status: 'ended';
}

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

export function createSession(
  name: string,
  description?: string
): Promise<BackendSession> {
  const payload: CreateSessionPayload = { name };
  if (description) payload.description = description;

  return request<BackendSession>('/sessions', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function endSession(sessionId: string): Promise<BackendSession> {
  const payload: EndSessionPayload = { status: 'ended' };

  return request<BackendSession>(`/sessions/${sessionId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function listSessions(): Promise<BackendSession[]> {
  return request<BackendSession[]>('/sessions', { method: 'GET' });
}

