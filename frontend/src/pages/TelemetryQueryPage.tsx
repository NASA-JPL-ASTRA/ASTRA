import { useEffect, useMemo, useState } from 'react';
import { Activity, ChevronRight, Loader2, Search } from 'lucide-react';
import {
  getTelemetryQueryInfo,
  listSessions,
  queryChannelRange,
  queryChannelValue,
  queryTelemetryEvents,
  searchTelemetryChannels,
} from '../services/api';
import type { BackendSession, TelemetryQueryResult } from '../services/api';

function nowUnix(): number {
  return Math.floor(Date.now() / 1000);
}

function formatJson(data: unknown): string {
  try {
    return JSON.stringify(data, null, 2);
  } catch {
    return String(data);
  }
}

function ResultBlock({
  title,
  loading,
  error,
  data,
}: {
  title: string;
  loading: boolean;
  error: string | null;
  data: unknown;
}) {
  return (
    <div className="rounded-xl border border-space-border bg-space-card overflow-hidden">
      <div className="px-4 py-2 border-b border-space-border text-xs font-semibold text-text-secondary uppercase tracking-wider">
        {title}
      </div>
      <div className="p-4 min-h-[120px]">
        {loading && (
          <div className="flex items-center gap-2 text-text-muted text-sm">
            <Loader2 className="w-4 h-4 animate-spin" />
            Running…
          </div>
        )}
        {!loading && error && (
          <p className="text-sm text-accent-red font-mono whitespace-pre-wrap">{error}</p>
        )}
        {!loading && !error && (
          <pre className="text-xs font-mono text-text-primary overflow-x-auto max-h-64 text-left">
            {formatJson(data)}
          </pre>
        )}
      </div>
    </div>
  );
}

const DOCS_HREF =
  typeof import.meta.env.VITE_OPENAPI_DOCS_URL === 'string' &&
  import.meta.env.VITE_OPENAPI_DOCS_URL.trim()
    ? import.meta.env.VITE_OPENAPI_DOCS_URL.trim()
    : `${window.location.protocol}//${window.location.hostname}:8000/docs`;

export default function TelemetryQueryPage() {
  const [sessions, setSessions] = useState<BackendSession[]>([]);
  const [sessionId, setSessionId] = useState('');
  const [channelName, setChannelName] = useState('motors.motor4_current');
  const [at, setAt] = useState(String(nowUnix()));
  const [t0, setT0] = useState(String(nowUnix() - 400));
  const [t1, setT1] = useState(String(nowUnix()));
  /** Independent window for GET /api/query/events (not tied to range t0/t1). */
  const [eventsT0, setEventsT0] = useState(String(nowUnix() - 400));
  const [eventsT1, setEventsT1] = useState(String(nowUnix()));
  const [severity, setSeverity] = useState('all');
  const [eventLimit, setEventLimit] = useState(20);
  const [searchQ, setSearchQ] = useState('motor temperature');
  const [searchK, setSearchK] = useState(5);

  const [apiInfo, setApiInfo] = useState<Record<string, unknown> | null>(null);

  const [chLoading, setChLoading] = useState(false);
  const [chErr, setChErr] = useState<string | null>(null);
  const [chData, setChData] = useState<unknown>(null);

  const [rangeLoading, setRangeLoading] = useState(false);
  const [rangeErr, setRangeErr] = useState<string | null>(null);
  const [rangeData, setRangeData] = useState<unknown>(null);

  const [evLoading, setEvLoading] = useState(false);
  const [evErr, setEvErr] = useState<string | null>(null);
  const [evData, setEvData] = useState<unknown>(null);

  const [searchLoading, setSearchLoading] = useState(false);
  const [searchErr, setSearchErr] = useState<string | null>(null);
  const [searchData, setSearchData] = useState<unknown>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [sess, info] = await Promise.all([
          listSessions(),
          getTelemetryQueryInfo(),
        ]);
        if (!cancelled) {
          setSessions(sess);
          setSessionId((prev) => (prev ? prev : sess[0]?.id ?? ''));
          setApiInfo(info);
        }
      } catch {
        if (!cancelled) setSessions([]);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const sessionOptions = useMemo(
    () =>
      sessions.map((s) => (
        <option key={s.id} value={s.id}>
          {s.name} ({s.id})
        </option>
      )),
    [sessions],
  );

  function unwrap<T>(r: TelemetryQueryResult<T>, empty: unknown): { err: string | null; data: unknown } {
    if (r.ok) return { err: null, data: r.data };
    return { err: `${r.status}: ${r.message}`, data: empty };
  }

  async function runChannel() {
    setChLoading(true);
    setChErr(null);
    const atNum = Number(at);
    if (!sessionId.trim() || !channelName.trim() || Number.isNaN(atNum)) {
      setChErr('Session, channel name, and numeric “at” are required.');
      setChLoading(false);
      return;
    }
    const res = await queryChannelValue(sessionId.trim(), channelName.trim(), atNum);
    const { err, data } = unwrap(res, null);
    setChErr(err);
    setChData(data);
    setChLoading(false);
  }

  async function runRange() {
    setRangeLoading(true);
    setRangeErr(null);
    const a = Number(t0);
    const b = Number(t1);
    if (!sessionId.trim() || !channelName.trim() || Number.isNaN(a) || Number.isNaN(b)) {
      setRangeErr('Session, channel, t0, and t1 are required (numbers).');
      setRangeLoading(false);
      return;
    }
    const res = await queryChannelRange(sessionId.trim(), channelName.trim(), a, b);
    const { err, data } = unwrap(res, null);
    setRangeErr(err);
    setRangeData(data);
    setRangeLoading(false);
  }

  async function runEvents() {
    setEvLoading(true);
    setEvErr(null);
    const a = Number(eventsT0);
    const b = Number(eventsT1);
    if (!sessionId.trim() || Number.isNaN(a) || Number.isNaN(b)) {
      setEvErr('Session and numeric t0 / t1 are required.');
      setEvLoading(false);
      return;
    }
    const res = await queryTelemetryEvents(sessionId.trim(), a, b, {
      severity,
      limit: eventLimit,
    });
    const { err, data } = unwrap(res, []);
    setEvErr(err);
    setEvData(data);
    setEvLoading(false);
  }

  async function runSearch() {
    setSearchLoading(true);
    setSearchErr(null);
    const res = await searchTelemetryChannels(searchQ, searchK);
    const { err, data } = unwrap(res, []);
    setSearchErr(err);
    setSearchData(data);
    setSearchLoading(false);
  }

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-8 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-text-primary flex items-center gap-2">
            <Activity className="w-7 h-7 text-accent-cyan" />
            Telemetry query
          </h1>
          <p className="text-sm text-text-secondary mt-1 max-w-xl">
            Influx-backed queries (same Flux logic as{' '}
            <code className="text-xs font-mono text-accent-cyan">telemetry/query.py</code>) and TF-IDF
            channel search. Session ids must match Influx{' '}
            <code className="text-xs font-mono text-accent-cyan">session_id</code> tags (often not the
            same as ASTRA UI session ids unless you align them). See{' '}
            <a
              className="text-accent-cyan hover:underline"
              href={DOCS_HREF}
              target="_blank"
              rel="noreferrer"
            >
              OpenAPI
            </a>
            .
          </p>
        </div>
      </div>

      {apiInfo && (
        <div className="rounded-xl border border-space-border bg-space-panel px-4 py-3 text-xs font-mono text-text-muted">
          <span className="text-text-secondary font-sans font-semibold text-[10px] uppercase tracking-wider block mb-1">
            GET /api/query
          </span>
          {formatJson(apiInfo)}
        </div>
      )}

      <section
        className="rounded-xl border border-space-border bg-space-card/40 p-4 sm:p-5"
        aria-label="Shared query parameters"
      >
        <h2 className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mb-4">
          Shared parameters
        </h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-8 lg:items-start">
          <div className="min-w-0 space-y-2">
            <span className="block text-left text-xs font-medium text-text-secondary">
              Session (Influx <code className="text-[10px] font-mono text-accent-cyan/90">session_id</code>)
            </span>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-stretch min-w-0">
              <select
                value={sessionId}
                onChange={(e) => setSessionId(e.target.value)}
                className="min-h-[42px] w-full sm:w-auto sm:min-w-[12rem] sm:max-w-[15rem] shrink-0 rounded-lg border border-space-border bg-space-dark px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-cyan/40"
              >
                <option value="">— ASTRA session (optional) —</option>
                {sessionOptions}
              </select>
              <input
                type="text"
                value={sessionId}
                onChange={(e) => setSessionId(e.target.value)}
                placeholder="test_4_motor_stall"
                className="min-h-[42px] min-w-0 flex-1 rounded-lg border border-space-border bg-space-dark px-3 py-2 text-sm font-mono text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent-cyan/40"
              />
            </div>
            <p className="text-[10px] text-text-muted leading-relaxed">
              Set the Influx tag here; the dropdown only suggests ASTRA sessions.
            </p>
          </div>
          <div className="min-w-0 space-y-2 lg:border-l lg:border-space-border lg:pl-8">
            <span className="block text-left text-xs font-medium text-text-secondary">
              Channel name
            </span>
            <input
              type="text"
              value={channelName}
              onChange={(e) => setChannelName(e.target.value)}
              placeholder="motors.motor4_current"
              className="min-h-[42px] w-full min-w-0 max-w-full rounded-lg border border-space-border bg-space-dark px-3 py-2 text-sm font-mono text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent-cyan/40"
            />
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-8">
        <div className="min-w-0 space-y-3">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-text-primary">GET /api/query/channel</h2>
            <button
              type="button"
              onClick={runChannel}
              disabled={chLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30 text-xs font-semibold hover:bg-accent-cyan/25 disabled:opacity-50"
            >
              Run
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
          <label className="block space-y-1">
            <span className="text-[10px] text-text-muted uppercase">at (Unix sec)</span>
            <input
              type="text"
              inputMode="decimal"
              value={at}
              onChange={(e) => setAt(e.target.value)}
              className="w-full rounded-lg border border-space-border bg-space-dark px-3 py-2 text-sm font-mono"
            />
          </label>
          <ResultBlock title="Response" loading={chLoading} error={chErr} data={chData} />
        </div>

        <div className="min-w-0 space-y-3">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-text-primary">GET /api/query/range</h2>
            <button
              type="button"
              onClick={runRange}
              disabled={rangeLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30 text-xs font-semibold hover:bg-accent-cyan/25 disabled:opacity-50"
            >
              Run
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <label className="block space-y-1">
              <span className="text-[10px] text-text-muted uppercase">t0</span>
              <input
                type="text"
                value={t0}
                onChange={(e) => setT0(e.target.value)}
                className="w-full rounded-lg border border-space-border bg-space-dark px-3 py-2 text-sm font-mono"
              />
            </label>
            <label className="block space-y-1">
              <span className="text-[10px] text-text-muted uppercase">t1</span>
              <input
                type="text"
                value={t1}
                onChange={(e) => setT1(e.target.value)}
                className="w-full rounded-lg border border-space-border bg-space-dark px-3 py-2 text-sm font-mono"
              />
            </label>
          </div>
          <ResultBlock title="Response" loading={rangeLoading} error={rangeErr} data={rangeData} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-8">
        <div className="min-w-0 space-y-3">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-text-primary">GET /api/query/events</h2>
            <button
              type="button"
              onClick={runEvents}
              disabled={evLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30 text-xs font-semibold hover:bg-accent-cyan/25 disabled:opacity-50"
            >
              Run
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
          <p className="text-xs text-text-muted">
            Empty list is normal when no events exist in Influx for this session. The time window here
            is independent of GET /api/query/range.
          </p>
          <div className="grid grid-cols-2 gap-2">
            <label className="block space-y-1">
              <span className="text-[10px] text-text-muted uppercase">t0 (Unix sec)</span>
              <input
                type="text"
                value={eventsT0}
                onChange={(e) => setEventsT0(e.target.value)}
                className="w-full rounded-lg border border-space-border bg-space-dark px-3 py-2 text-sm font-mono"
              />
            </label>
            <label className="block space-y-1">
              <span className="text-[10px] text-text-muted uppercase">t1 (Unix sec)</span>
              <input
                type="text"
                value={eventsT1}
                onChange={(e) => setEventsT1(e.target.value)}
                className="w-full rounded-lg border border-space-border bg-space-dark px-3 py-2 text-sm font-mono"
              />
            </label>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <label className="block space-y-1">
              <span className="text-[10px] text-text-muted uppercase">severity</span>
              <select
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
                className="w-full rounded-lg border border-space-border bg-space-dark px-3 py-2 text-sm"
              >
                <option value="all">all</option>
                <option value="warning">warning</option>
                <option value="activity_hi">activity_hi</option>
                <option value="activity_lo">activity_lo</option>
                <option value="command">command</option>
              </select>
            </label>
            <label className="block space-y-1">
              <span className="text-[10px] text-text-muted uppercase">limit</span>
              <input
                type="number"
                min={1}
                max={500}
                value={eventLimit}
                onChange={(e) => setEventLimit(Number(e.target.value))}
                className="w-full rounded-lg border border-space-border bg-space-dark px-3 py-2 text-sm font-mono"
              />
            </label>
          </div>
          <ResultBlock title="Response" loading={evLoading} error={evErr} data={evData} />
        </div>

        <div className="min-w-0 space-y-3">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-text-primary flex items-center gap-1.5">
              <Search className="w-4 h-4 text-accent-cyan" />
              GET /api/query/search
            </h2>
            <button
              type="button"
              onClick={runSearch}
              disabled={searchLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30 text-xs font-semibold hover:bg-accent-cyan/25 disabled:opacity-50"
            >
              Run
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
          <label className="block space-y-1">
            <span className="text-[10px] text-text-muted uppercase">q</span>
            <input
              type="text"
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              className="w-full rounded-lg border border-space-border bg-space-dark px-3 py-2 text-sm"
            />
          </label>
          <label className="block space-y-1">
            <span className="text-[10px] text-text-muted uppercase">k</span>
            <input
              type="number"
              min={1}
              max={50}
              value={searchK}
              onChange={(e) => setSearchK(Number(e.target.value))}
              className="w-full rounded-lg border border-space-border bg-space-dark px-3 py-2 text-sm font-mono"
            />
          </label>
          <ResultBlock title="Response" loading={searchLoading} error={searchErr} data={searchData} />
        </div>
      </div>
    </div>
  );
}
