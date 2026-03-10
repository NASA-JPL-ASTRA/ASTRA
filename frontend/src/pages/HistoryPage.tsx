import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Calendar,
  Clock,
  FileText,
  Users,
  Download,
  Search,
  Trash2,
  ChevronRight,
  MessageSquareText,
} from 'lucide-react';
import { listSessions } from '../services/api';
import type { Session } from '../types';

function formatDate(date: Date): string {
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatDuration(start: Date, end?: Date): string {
  const endTime = end || new Date();
  const diffMs = endTime.getTime() - start.getTime();
  const hours = Math.floor(diffMs / 3600000);
  const minutes = Math.floor((diffMs % 3600000) / 60000);
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

function exportSession(session: Session) {
  const lines: string[] = [];
  lines.push(`# ${session.name}`);
  lines.push(`# ${session.description}`);
  lines.push(`# Start: ${session.startTime.toISOString()}`);
  if (session.endTime) lines.push(`# End: ${session.endTime.toISOString()}`);
  lines.push(`# Testbed: ${session.testbed}`);
  lines.push(`# Entries: ${session.logCount}`);
  lines.push('');

  const filteredTranscriptions = (session.transcriptions || []).filter(
    (t) => t.confidence >= 0.5,
  );
  if (filteredTranscriptions.length > 0) {
    lines.push('Timestamp | Speaker | Confidence | Text');
    lines.push('----------|---------|------------|-----');
    for (const t of filteredTranscriptions) {
      const time = new Date(t.timestamp).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
      const conf = `${(t.confidence * 100).toFixed(0)}%`;
      lines.push(`${time} | ${t.speakerId} | ${conf} | ${t.rawText}`);
    }
  } else {
    lines.push('(No transcription data stored for this session)');
  }

  const blob = new Blob([lines.join('\n')], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${session.name}.txt`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function HistoryPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadSessions() {
      try {
        setLoadError(null);
        const apiSessions = await listSessions();
        if (cancelled) return;

        const mapped: Session[] = apiSessions.map((s) => {
          const notes = s.notes ?? [];
          const transcriptions = notes.map((n) => ({
            id: n.id,
            timestamp: n.timestamp,
            speakerId: n.speaker ?? 'speaker_0',
            rawText: n.content,
            confidence: n.confidence ?? 0.9,
            isFinal: true,
          }));
          return {
            id: s.id,
            name: s.name,
            description: s.description ?? 'No description',
            startTime: new Date(s.started_at),
            endTime: s.ended_at ? new Date(s.ended_at) : undefined,
            status: s.status === 'ended' ? 'completed' : 'active',
            operators: [],
            logCount: transcriptions.length,
            telemetryStreams: 0,
            testbed: 'Backend Session',
            transcriptions,
          };
        });

        setSessions(mapped);
      } catch (error) {
        if (cancelled) return;
        const message =
          error instanceof Error ? error.message : 'Failed to load sessions';
        setLoadError(message);
      }
    }

    loadSessions();
    return () => {
      cancelled = true;
    };
  }, []);

  const filteredSessions = sessions.filter(
    (s) =>
      searchQuery === '' ||
      s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.testbed.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  const handleDelete = (id: string) => {
    if (deletingId === id) {
      setSessions((prev) => prev.filter((sess) => sess.id !== id));
      setDeletingId(null);
    } else {
      setDeletingId(id);
      setTimeout(() => setDeletingId(null), 3000);
    }
  };

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Page Title */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Structured Notes</h1>
          <p className="text-sm text-text-secondary mt-1">
            Browse saved session recordings — click to view full transcription
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-text-muted">
          <MessageSquareText className="w-4 h-4" />
          {filteredSessions.length} note{filteredSessions.length !== 1 ? 's' : ''}
        </div>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search by name, description, or testbed..."
          className="w-full bg-space-card border border-space-border rounded-lg pl-10 pr-4 py-2.5 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-cyan/50 transition-all"
        />
      </div>

      {/* Sessions List */}
      {loadError && (
        <div className="rounded-lg border border-accent-red/30 bg-accent-red/10 px-4 py-3 text-sm text-accent-red">
          {loadError}
        </div>
      )}
      {filteredSessions.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-text-muted">
          <MessageSquareText className="w-16 h-16 mb-4 opacity-20" />
          <p className="text-base font-medium mb-1">No structured notes yet</p>
          <p className="text-sm">
            {searchQuery
              ? 'No notes match your search'
              : 'Start a recording session — it will be auto-saved here when you stop'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredSessions.map((session) => (
            <div
              key={session.id}
              className="rounded-xl border border-space-border bg-space-panel hover:border-accent-cyan/20 transition-all group"
            >
              <div className="flex items-center">
                {/* Clickable main area → detail page */}
                <Link
                  to={`/history/${session.id}`}
                  state={{ session }}
                  className="flex-1 p-5 flex items-start justify-between min-w-0"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                      <div className="p-1.5 rounded-lg bg-accent-cyan/10">
                        <MessageSquareText className="w-4 h-4 text-accent-cyan" />
                      </div>
                      <h3 className="text-base font-semibold font-mono text-text-primary group-hover:text-accent-cyan transition-colors">
                        {session.name}
                      </h3>
                    </div>
                    <p className="text-sm text-text-secondary mb-3 pl-10">
                      {session.description}
                    </p>

                    <div className="flex items-center gap-5 text-xs text-text-muted pl-10">
                      <div className="flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5" />
                        {formatDate(session.startTime)}
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Clock className="w-3.5 h-3.5" />
                        {formatDuration(session.startTime, session.endTime)}
                      </div>
                      <div className="flex items-center gap-1.5">
                        <FileText className="w-3.5 h-3.5" />
                        {session.logCount} entries
                      </div>
                      {session.operators.length > 0 && (
                        <div className="flex items-center gap-1.5">
                          <Users className="w-3.5 h-3.5" />
                          {session.operators.length} operators
                        </div>
                      )}
                      {session.transcriptions && session.transcriptions.length > 0 && (
                        <span className="text-accent-green font-medium">Has transcription data</span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-3 shrink-0 ml-4">
                    <span className="text-xs text-text-muted px-3 py-1.5 rounded-lg bg-space-card border border-space-border">
                      {session.testbed}
                    </span>
                    <ChevronRight className="w-5 h-5 text-text-muted group-hover:text-accent-cyan transition-colors" />
                  </div>
                </Link>

                {/* Action buttons (non-clickable area) */}
                <div className="flex items-center gap-1 pr-4 opacity-0 group-hover:opacity-100 transition-all">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      exportSession(session);
                    }}
                    className="p-2 rounded-lg text-text-muted hover:text-accent-cyan hover:bg-accent-cyan/10 transition-all"
                    title="Export as text file"
                  >
                    <Download className="w-4 h-4" />
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(session.id);
                    }}
                    className={`p-2 rounded-lg transition-all ${
                      deletingId === session.id
                        ? 'text-accent-red bg-accent-red/15'
                        : 'text-text-muted hover:text-accent-red hover:bg-accent-red/10'
                    }`}
                    title={deletingId === session.id ? 'Click again to confirm delete' : 'Delete'}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
