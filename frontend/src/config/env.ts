function getEnv(key: string): string | undefined {
  const value = import.meta.env[key];
  return typeof value === 'string' && value.trim() ? value : undefined;
}

export const API_URL = getEnv('VITE_API_URL') ?? 'http://localhost:8000/api';
export const SESSION_WS_URL =
  getEnv('VITE_SESSION_WS_URL') ?? 'ws://localhost:8000/ws/sessions';
