type AppMode = 'mock' | 'live';

function getEnv(key: string): string | undefined {
  const value = import.meta.env[key];
  return typeof value === 'string' && value.trim() ? value : undefined;
}

function getAppMode(): AppMode {
  const mode = getEnv('VITE_APP_MODE');
  return mode === 'live' ? 'live' : 'mock';
}

export const APP_MODE: AppMode = getAppMode();
export const API_URL = getEnv('VITE_API_URL') ?? 'http://localhost:8000/api';
export const SESSION_WS_URL =
  getEnv('VITE_SESSION_WS_URL') ?? 'ws://localhost:8000/ws/sessions';

