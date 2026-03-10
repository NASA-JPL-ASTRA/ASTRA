import { API_URL } from '../config/env';

/**
 * Create a WAV Blob from Int16 PCM.
 * @param pcm16 Int16Array of mono 16-bit PCM samples
 * @param sampleRate e.g. 16000
 */
function createWavBlob(pcm16: Int16Array, sampleRate: number): Blob {
  const numChannels = 1;
  const bitsPerSample = 16;
  const byteRate = sampleRate * numChannels * (bitsPerSample / 8);
  const blockAlign = numChannels * (bitsPerSample / 8);
  const dataSize = pcm16.length * 2; // 2 bytes per sample
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);

  // WAV header
  const writeStr = (offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
  };
  writeStr(0, 'RIFF');
  view.setUint32(4, 36 + dataSize, true);
  writeStr(8, 'WAVE');
  writeStr(12, 'fmt ');
  view.setUint32(16, 16, true); // chunk size
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, byteRate, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, bitsPerSample, true);
  writeStr(36, 'data');
  view.setUint32(40, dataSize, true);

  const pcmOffset = 44;
  for (let i = 0; i < pcm16.length; i++) {
    view.setInt16(pcmOffset + i * 2, pcm16[i], true);
  }

  return new Blob([buffer], { type: 'audio/wav' });
}

/**
 * Upload an audio chunk for STT.
 * Called when a chunk is flushed during recording.
 */
export async function uploadSttChunk(
  sessionId: string,
  pcm16: Int16Array,
  sampleRate: number = 16000,
  audioChunkId?: string
): Promise<void> {
  const blob = createWavBlob(pcm16, sampleRate);
  const formData = new FormData();
  formData.append('file', blob, 'chunk.wav');
  formData.append('audio_chunk_id', audioChunkId ?? `chunk_${Date.now()}`);
  formData.append('duration_seconds', String(pcm16.length / sampleRate));

  const url = `${API_URL}/sessions/${sessionId}/stt/upload`;
  const resp = await fetch(url, {
    method: 'POST',
    body: formData,
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`STT upload failed: ${resp.status} ${text}`);
  }
}

export interface BackendNote {
  id: string;
  session_id: string;
  timestamp: string;
  speaker: string | null;
  content: string;
  type: string;
  tags: string[];
  confidence?: number;
}

export interface BackendSession {
  id: string;
  name: string;
  description: string | null;
  status: 'active' | 'ended';
  started_at: string;
  ended_at: string | null;
  notes?: BackendNote[];
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

export function getSession(sessionId: string): Promise<BackendSession> {
  return request<BackendSession>(`/sessions/${sessionId}`, { method: 'GET' });
}

