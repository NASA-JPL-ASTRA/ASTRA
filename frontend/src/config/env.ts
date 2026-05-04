function getEnv(key: string): string | undefined {
  const value = import.meta.env[key];
  return typeof value === 'string' && value.trim() ? value : undefined;
}

const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';

export const API_URL = getEnv('VITE_API_URL') ?? '/api';
export const SESSION_WS_URL =
  getEnv('VITE_SESSION_WS_URL') ?? `${wsProtocol}//${window.location.host}/ws/sessions`;
