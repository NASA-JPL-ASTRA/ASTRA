import { useState } from 'react';
import {
  Activity,
  Loader2,
  Send,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { useStore } from '../../store/useStore';
import type { VoiceTelemetryQuery } from '../../types';
import { queryVoiceTelemetry } from '../../services/api';

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

export default function VoiceTelemetryPanel() {
  const {
    voiceTelemetryQueries,
    backendSessionId,
    telemetryScenarios,
    defaultTelemetryScenario,
    addPendingVoiceTelemetryQuery,
    resolveVoiceTelemetryQuery,
    failVoiceTelemetryQuery,
    setRecordingError,
  } = useStore();

  const [manualText, setManualText] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = manualText.trim();
    if (!text || !backendSessionId || submitting) return;

    const pendingId = addPendingVoiceTelemetryQuery(text);
    setSubmitting(true);
    setManualText('');

    try {
      const result = await queryVoiceTelemetry(backendSessionId, text);
      resolveVoiceTelemetryQuery(pendingId, result);
    } catch (err) {
      failVoiceTelemetryQuery(
        pendingId,
        err instanceof Error ? err.message : 'Telemetry query failed',
      );
      setRecordingError(
        err instanceof Error ? err.message : 'Telemetry query failed',
      );
    } finally {
      setSubmitting(false);
    }
  };

  const queries = [...voiceTelemetryQueries].reverse();
  const hasPending = voiceTelemetryQueries.some((q) => q.status === 'pending');

  return (
    <div className="flex flex-col h-full rounded-xl border border-space-border bg-space-panel overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-space-border shrink-0">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-accent-cyan" />
          <h2 className="text-sm font-semibold text-text-primary">Telemetry Queries</h2>
        </div>
        {hasPending && (
          <Loader2 className="w-3.5 h-3.5 text-accent-cyan animate-spin" />
        )}
      </div>

      <div className="px-4 py-2 border-b border-space-border shrink-0">
        <p className="text-[10px] text-text-muted leading-relaxed">
          Voice commands are parsed and answered from{' '}
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
      </div>

      <form
        onSubmit={handleManualSubmit}
        className="px-4 py-3 border-b border-space-border shrink-0 flex gap-2"
      >
        <input
          type="text"
          value={manualText}
          onChange={(e) => setManualText(e.target.value)}
          placeholder="Type a telemetry question…"
          disabled={!backendSessionId || submitting}
          className="flex-1 min-w-0 rounded-lg border border-space-border bg-space-dark px-3 py-2 text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-cyan/40 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!backendSessionId || !manualText.trim() || submitting}
          className="shrink-0 p-2 rounded-lg border border-accent-cyan/30 bg-accent-cyan/10 text-accent-cyan hover:bg-accent-cyan/20 disabled:opacity-40 transition-colors"
          aria-label="Send telemetry query"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {queries.length === 0 ? (
          <div className="text-center py-8 text-text-muted text-xs">
            <Activity className="w-8 h-8 mx-auto mb-2 opacity-30" />
            <p>Ask about events or channel signals while recording.</p>
            <p className="mt-1 opacity-70">
              e.g. &ldquo;terrain bumps in test 4&rdquo; or &ldquo;motor1 current in test 1&rdquo;
            </p>
          </div>
        ) : (
          queries.map((q) => <QueryCard key={q.id} query={q} />)
        )}
      </div>
    </div>
  );
}
