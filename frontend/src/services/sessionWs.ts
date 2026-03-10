import { SESSION_WS_URL } from '../config/env';

export interface SessionWsMessage {
  event: string;
  session_id: string;
  data: unknown;
}

interface SessionWsHandlers {
  onOpen?: () => void;
  onMessage?: (message: SessionWsMessage) => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
}

export interface SessionWsConnection {
  close: () => void;
}

export function connectSessionWs(
  sessionId: string,
  handlers: SessionWsHandlers = {}
): SessionWsConnection {
  const ws = new WebSocket(`${SESSION_WS_URL}/${sessionId}`);
  let pingTimer: number | null = null;

  ws.onopen = () => {
    handlers.onOpen?.();
    pingTimer = window.setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send('ping');
      }
    }, 30000);
  };

  ws.onmessage = (event) => {
    if (typeof event.data !== 'string') return;
    if (event.data === 'pong') return;

    try {
      const parsed = JSON.parse(event.data) as SessionWsMessage;
      handlers.onMessage?.(parsed);
    } catch {
      // Ignore non-JSON frames so UI does not crash.
    }
  };

  ws.onerror = (event) => {
    handlers.onError?.(event);
  };

  ws.onclose = () => {
    if (pingTimer) {
      window.clearInterval(pingTimer);
      pingTimer = null;
    }
    handlers.onClose?.();
  };

  return {
    close: () => {
      if (pingTimer) {
        window.clearInterval(pingTimer);
        pingTimer = null;
      }
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
    },
  };
}

