# ASTRA Frontend

React + TypeScript + Vite client for browser recording, live transcription,
structured notes, and session history.


> API reference: [`../backend/docs/api-contract.md`](../backend/docs/api-contract.md)

## Recording Path

```
browser microphone
  └─ POST /api/sessions/{sid}/stt/upload   (one HTTP request per audio chunk)
       └─ live updates over /ws/sessions/{sid}
            ├─ transcript.chunk.ready  (incremental deltas)
            ├─ stt.task.done           (final transcript)
            └─ note.created            (persisted note)
```

The legacy local `whisper/` dependency has been removed.

## Quick Start

```bash
npm install
cp .env.example .env.local    # adjust if backend is not on :8000
npm run dev                   # http://localhost:5173

npm run build                 # production bundle
npm run lint                  # eslint
```

## Environment Variables

```env
# .env.local — copy from .env.example
VITE_API_URL=http://localhost:8000/api
VITE_SESSION_WS_URL=ws://localhost:8000/ws/sessions
```

Both fall back to `window.location.host` if unset (see `src/config/env.ts`),
so production builds served from the same origin work without configuration.

## Runtime Flow

1. Operator clicks **Start** → `POST /api/sessions` → backend returns `sid`.
2. Frontend opens `WebSocket /ws/sessions/{sid}` for live events.
3. Microphone audio is chunked in the browser; each chunk is uploaded via
   `POST /api/sessions/{sid}/stt/upload`.
4. Backend streams `transcript.chunk.ready`, `stt.task.done`, and
   `note.created` events back through the WebSocket.
5. History / detail pages read canonical data from REST endpoints.
6. On stop, the frontend waits for queued chunk uploads to drain before
   `PATCH`-ing the session to `status: ended`.

## Key Files

```
src/
├── hooks/useWhisper.ts             Mic capture + chunked upload + WS handling
├── services/api.ts                 REST client
├── services/sessionWs.ts           Session-scoped WebSocket client
├── pages/SessionPage.tsx           Active recording UI
├── pages/HistoryPage.tsx           Session list
├── pages/SessionDetailPage.tsx     Notes for a single session
├── store/useStore.ts               UI state (live transcripts, not history)
└── config/env.ts                   Env var resolution
```

## Notes

- `transcriptions` in the store are live UI state, **not** canonical history.
- Canonical history comes from backend sessions and notes endpoints.
- On stop, the frontend waits for in-flight chunk uploads before ending the
  session, so no transcript is lost.
