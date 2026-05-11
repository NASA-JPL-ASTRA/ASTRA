import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Calendar,
  Clock,
  FileText,
  Download,
  Search,
  ChevronRight,
  MessageSquareText,
} from 'lucide-react';
import {
  exportNotes,
  listSessions,
  type BackendSession,
} from '../services/api';

interface HistorySession extends BackendSession {
  startTime: Date;
  endTime?: Date;
}

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

export default function HistoryPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [sessions, setSessions] = useState<HistorySession[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadSessions() {
      try {
        setLoadError(null);
        const apiSessions = await listSessions();
        if (cancelled) return;

        const mapped: HistorySession[] = apiSessions.map((s) => ({
          ...s,
          startTime: new Date(s.started_at),
          endTime: s.ended_at ? new Date(s.ended_at) : undefined,
        }));

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
      (s.description ?? '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.id.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  const totalNotes = filteredSessions.reduce((sum, session) => sum + session.note_count, 0);

  const handleExport = async (session: HistorySession) => {
    try {
      const text = await exportNotes(session.id, 'markdown');
      const blob = new Blob([text], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${session.name}-notes.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : 'Failed to export notes');
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
          {totalNotes} note{totalNotes !== 1 ? 's' : ''}
        </div>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search by name, description, or session id..."
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
                        {session.note_count} note{session.note_count !== 1 ? 's' : ''}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 shrink-0 ml-4">
                    <span className="text-xs text-text-muted px-3 py-1.5 rounded-lg bg-space-card border border-space-border">
                      {session.id}
                    </span>
                    <ChevronRight className="w-5 h-5 text-text-muted group-hover:text-accent-cyan transition-colors" />
                  </div>
                </Link>

                {/* Action buttons (non-clickable area) */}
                <div className="flex items-center gap-1 pr-4 opacity-0 group-hover:opacity-100 transition-all">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      void handleExport(session);
                    }}
                    className="p-2 rounded-lg text-text-muted hover:text-accent-cyan hover:bg-accent-cyan/10 transition-all"
                    title="Export backend notes as Markdown"
                  >
                    <Download className="w-4 h-4" />
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
