import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity,
  Loader2,
  Mic,
  Send,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { useStore } from '../../store/useStore';
import type { VoiceTelemetryQuery } from '../../types';
import {
  getLogTelemetryScenarios,
  listVoiceTelemetryQueries,
  queryVoiceTelemetry,
  queryVoiceTelemetryAudio,
} from '../../services/api';

const MAX_VOICE_QUERY_MS = 12_000;

function QueryCard({ query }: { query: VoiceTelemetryQuery }) {
  const [expanded, setExpanded] = useState(true);
  const time = new Date(query.created_at).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

  return (
    <div
      className={`rounded-lg border p-3 ${
        query.is_telemetry_query
          ? 'border-accent-cyan/25 bg-accent-cyan/5'
          : 'border-space-border bg-space-card/50'
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex-1 min-w-0">
          <p className="text-[10px] font-mono text-text-muted uppercase tracking-wide">
            {time}
            {query.scenario ? ` · ${query.scenario}` : ''}
            {query.action && query.action !== 'unknown' ? ` · ${query.action}` : ''}
          </p>
          <p className="text-xs text-text-secondary mt-1 italic line-clamp-2">
            &ldquo;{query.transcript}&rdquo;
          </p>
        </div>
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="p-1 rounded text-text-muted hover:text-text-primary shrink-0"
          aria-label={expanded ? 'Collapse answer' : 'Expand answer'}
        >
          {expanded ? (
            <ChevronUp className="w-3.5 h-3.5" />
          ) : (
            <ChevronDown className="w-3.5 h-3.5" />
          )}
        </button>
      </div>

      {query.status === 'pending' ? (
        <div className="flex items-center gap-2 text-xs text-accent-cyan mt-2">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          Querying telemetry logs…
        </div>
      ) : expanded ? (
        <pre className="mt-2 text-xs text-text-primary font-mono whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto">
          {query.answer}
        </pre>
      ) : null}
    </div>
  );
}

interface VoiceTelemetryPanelProps {
  sessionId?: string | null;
  className?: string;
  variant?: 'card' | 'embedded';
}

function pendingQuery(transcript: string, scenario: string): VoiceTelemetryQuery {
  return {
    id: `vtq_local_${Math.random().toString(36).slice(2, 10)}`,
    transcript,
    action: 'unknown',
    scenario,
    answer: '',
    is_telemetry_query: false,
    created_at: new Date().toISOString(),
    status: 'pending',
  };
}

export default function VoiceTelemetryPanel({
  sessionId,
  className = '',
  variant = 'card',
}: VoiceTelemetryPanelProps) {
  const {
    backendSessionId,
    selectedSttModel,
    setRecordingError,
  } = useStore();

  const targetSessionId = sessionId === undefined ? backendSessionId : sessionId;
  const [queries, setQueries] = useState<VoiceTelemetryQuery[]>([]);
  const [telemetryScenarios, setTelemetryScenarios] = useState<string[]>([]);
  const [defaultTelemetryScenario, setDefaultTelemetryScenario] = useState('');
  const [loadError, setLoadError] = useState<string | null>(null);
  const [manualText, setManualText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [voiceListening, setVoiceListening] = useState(false);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const voiceStreamRef = useRef<MediaStream | null>(null);
  const voiceChunksRef = useRef<Blob[]>([]);
  const voiceStopTimerRef = useRef<ReturnType<typeof window.setTimeout> | null>(null);

  useEffect(() => {
    let cancelled = false;
    getLogTelemetryScenarios()
      .then((info) => {
        if (cancelled) return;
        setTelemetryScenarios(info.scenarios);
        setDefaultTelemetryScenario(info.default_scenario);
      })
      .catch(() => {
        if (!cancelled) {
          setTelemetryScenarios([]);
          setDefaultTelemetryScenario('');
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!targetSessionId) {
      setQueries([]);
      return;
    }

    let cancelled = false;
    setLoadError(null);
    listVoiceTelemetryQueries(targetSessionId)
      .then((items) => {
        if (cancelled) return;
        setQueries(items.map((item) => ({ ...item, status: item.status ?? 'done' })));
      })
      .catch((err) => {
        if (cancelled) return;
        setQueries([]);
        setLoadError(err instanceof Error ? err.message : 'Failed to load telemetry queries');
      });

    return () => {
      cancelled = true;
    };
  }, [targetSessionId]);

  const visibleQueries = useMemo(() => [...queries].reverse(), [queries]);
  const hasPending = queries.some((q) => q.status === 'pending');
  const embedded = variant === 'embedded';

  const runQuery = useCallback(async (text: string) => {
    if (!text || !targetSessionId || submitting) return;

    const pending = pendingQuery(text, defaultTelemetryScenario);
    setQueries((items) => [...items, pending]);
    setSubmitting(true);
    setManualText('');
    setLoadError(null);

    try {
      const result = await queryVoiceTelemetry(targetSessionId, text);
      setQueries((items) =>
        items.map((item) =>
          item.id === pending.id ? { ...result, status: 'done' as const } : item,
        ),
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Telemetry query failed';
      setQueries((items) =>
        items.map((item) =>
          item.id === pending.id
            ? {
                ...item,
                status: 'failed' as const,
                answer: message,
                is_telemetry_query: false,
              }
            : item,
        ),
      );
      if (sessionId === undefined) {
        setRecordingError(message);
      }
    } finally {
      setSubmitting(false);
    }
  }, [defaultTelemetryScenario, sessionId, setRecordingError, submitting, targetSessionId]);

  const runAudioQuery = useCallback(async (audioBlob: Blob) => {
    if (!targetSessionId || submitting) return;

    const pending = pendingQuery('Voice query...', defaultTelemetryScenario);
    setQueries((items) => [...items, pending]);
    setSubmitting(true);
    setManualText('');
    setLoadError(null);

    try {
      const result = await queryVoiceTelemetryAudio(targetSessionId, audioBlob, {
        scenario: defaultTelemetryScenario || undefined,
        model: selectedSttModel,
      });
      setQueries((items) =>
        items.map((item) =>
          item.id === pending.id ? { ...result, status: 'done' as const } : item,
        ),
      );
      setManualText(result.transcript);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Voice telemetry query failed';
      setQueries((items) =>
        items.map((item) =>
          item.id === pending.id
            ? {
                ...item,
                status: 'failed' as const,
                answer: message,
                is_telemetry_query: false,
              }
            : item,
        ),
      );
      if (sessionId === undefined) {
        setRecordingError(message);
      }
      setLoadError(message);
    } finally {
      setSubmitting(false);
    }
  }, [
    defaultTelemetryScenario,
    selectedSttModel,
    sessionId,
    setRecordingError,
    submitting,
    targetSessionId,
  ]);

  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    void runQuery(manualText.trim());
  };

  const stopVoiceRecording = useCallback(() => {
    if (voiceStopTimerRef.current !== null) {
      window.clearTimeout(voiceStopTimerRef.current);
      voiceStopTimerRef.current = null;
    }
    if (recorderRef.current?.state === 'recording') {
      recorderRef.current.stop();
    }
  }, []);

  const handleVoiceQuery = async () => {
    if (voiceListening) {
      stopVoiceRecording();
      return;
    }

    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      setLoadError('Voice recording is not supported in this browser.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const preferredType = MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : '';
      const recorder = preferredType
        ? new MediaRecorder(stream, { mimeType: preferredType })
        : new MediaRecorder(stream);
      voiceStreamRef.current = stream;
      recorderRef.current = recorder;
      voiceChunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          voiceChunksRef.current.push(event.data);
        }
      };

      recorder.onerror = () => {
        setLoadError('Voice recording failed.');
      };

      recorder.onstop = () => {
        if (voiceStopTimerRef.current !== null) {
          window.clearTimeout(voiceStopTimerRef.current);
          voiceStopTimerRef.current = null;
        }
        const mimeType = recorder.mimeType || preferredType || 'audio/webm';
        const audioBlob = new Blob(voiceChunksRef.current, { type: mimeType });
        recorderRef.current = null;
        voiceStreamRef.current?.getTracks().forEach((track) => track.stop());
        voiceStreamRef.current = null;
        voiceChunksRef.current = [];
        setVoiceListening(false);

        if (audioBlob.size > 0) {
          void runAudioQuery(audioBlob);
        } else {
          setLoadError('No voice audio was captured.');
        }
      };

      setVoiceListening(true);
      setLoadError(null);
      recorder.start();
      voiceStopTimerRef.current = window.setTimeout(() => {
        stopVoiceRecording();
      }, MAX_VOICE_QUERY_MS);
    } catch (err) {
      voiceStreamRef.current?.getTracks().forEach((track) => track.stop());
      voiceStreamRef.current = null;
      recorderRef.current = null;
      setVoiceListening(false);
      setLoadError(err instanceof Error ? err.message : 'Voice recording could not start.');
    }
  };

  useEffect(() => {
    return () => {
      if (voiceStopTimerRef.current !== null) {
        window.clearTimeout(voiceStopTimerRef.current);
      }
      if (recorderRef.current?.state === 'recording') {
        recorderRef.current.stop();
      }
      voiceStreamRef.current?.getTracks().forEach((track) => track.stop());
      recorderRef.current = null;
      voiceStreamRef.current = null;
    };
  }, []);

  return (
    <div
      className={`flex h-full flex-col overflow-hidden ${
        embedded
          ? 'bg-transparent'
          : 'rounded-xl border border-space-border bg-space-panel'
      } ${className}`}
    >
      <div
        className={`flex items-center justify-between border-b border-space-border/60 ${
          embedded ? 'px-5 py-4' : 'px-4 py-3'
        } shrink-0`}
      >
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-accent-cyan" />
          <div>
            <h2 className="text-sm font-semibold text-text-primary">Telemetry Queries</h2>
            {embedded && (
              <p className="mt-0.5 text-xs text-text-muted">Search session event and channel logs</p>
            )}
          </div>
        </div>
        {hasPending && (
          <Loader2 className="w-3.5 h-3.5 text-accent-cyan animate-spin" />
        )}
      </div>

      <div
        className={`border-b border-space-border/60 ${
          embedded ? 'px-5 py-3' : 'px-4 py-2'
        } shrink-0`}
      >
        <p className="text-[10px] text-text-muted leading-relaxed">
          Queries are answered from{' '}
          <span className="font-mono text-text-secondary">event.log</span> /{' '}
          <span className="font-mono text-text-secondary">channel.log</span>
          {defaultTelemetryScenario ? (
            <>
              {' '}
              (default scenario:{' '}
              <span className="font-mono text-accent-cyan">{defaultTelemetryScenario}</span>)
            </>
          ) : null}
        </p>
        {telemetryScenarios.length > 0 && (
          <p className="text-[10px] text-text-muted mt-1 font-mono truncate" title={telemetryScenarios.join(', ')}>
            {telemetryScenarios.length} scenario(s) on disk
          </p>
        )}
        {loadError && (
          <p className="mt-1 text-[10px] leading-relaxed text-accent-red">
            {loadError}
          </p>
        )}
      </div>

      <form
        onSubmit={handleManualSubmit}
        className={`border-b border-space-border/60 shrink-0 flex gap-2 ${
          embedded ? 'px-5 py-3' : 'px-4 py-3'
        }`}
      >
        <input
          type="text"
          value={manualText}
          onChange={(e) => setManualText(e.target.value)}
          placeholder="Type a telemetry question…"
          disabled={!targetSessionId || submitting}
          className="min-h-9 flex-1 min-w-0 rounded-md border border-space-border/70 bg-space-black/45 px-3 py-2 text-xs text-text-primary placeholder:text-text-muted outline-none transition-colors focus:border-accent-cyan/50 disabled:opacity-50"
        />
        <button
          type="button"
          onClick={handleVoiceQuery}
          disabled={!targetSessionId || submitting}
          className={`min-h-9 shrink-0 rounded-md border px-2.5 transition-colors disabled:opacity-40 ${
            voiceListening
              ? 'border-accent-red/40 bg-accent-red/10 text-accent-red'
              : 'border-space-border/70 bg-space-black/35 text-text-secondary hover:border-accent-cyan/40 hover:text-accent-cyan'
          }`}
          aria-label={voiceListening ? 'Stop voice query' : 'Start voice query'}
          title={voiceListening ? 'Stop voice query' : 'Voice query'}
        >
          {voiceListening ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Mic className="h-4 w-4" />
          )}
        </button>
        <button
          type="submit"
          disabled={!targetSessionId || !manualText.trim() || submitting || voiceListening}
          className="min-h-9 shrink-0 rounded-md border border-accent-cyan/30 bg-accent-cyan/10 px-2.5 text-accent-cyan transition-colors hover:bg-accent-cyan/20 disabled:opacity-40"
          aria-label="Send telemetry query"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>

      <div className={`flex-1 overflow-y-auto space-y-3 ${embedded ? 'px-5 py-4' : 'p-4'}`}>
        {visibleQueries.length === 0 ? (
          <div className="flex h-full min-h-24 flex-col justify-center rounded-md border border-dashed border-space-border/50 bg-space-black/20 px-4 py-6 text-center text-xs text-text-muted">
            <Activity className="mx-auto mb-2 h-7 w-7 opacity-30" />
            <p>Ask about events or channel signals for this note.</p>
            <p className="mt-1 leading-relaxed opacity-70">
              e.g. &ldquo;terrain bumps in test 4&rdquo; or &ldquo;motor1 current in test 1&rdquo;
            </p>
          </div>
        ) : (
          visibleQueries.map((q) => <QueryCard key={q.id} query={q} />)
        )}
      </div>
    </div>
  );
}
