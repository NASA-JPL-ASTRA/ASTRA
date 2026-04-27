import { useEffect, useState } from 'react';
import {
  Radio,
  MessageSquareText,
  FileText,
  Clock,
  Calendar,
  ChevronRight,
  Loader2,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { useStore } from '../store/useStore';
import { listSessions } from '../services/api';
import type { BackendSession } from '../services/api';

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatDuration(startStr: string, endStr?: string | null): string {
  const start = new Date(startStr);
  const end = endStr ? new Date(endStr) : new Date();
  const diffMs = end.getTime() - start.getTime();
  const hours = Math.floor(diffMs / 3600000);
  const minutes = Math.floor((diffMs % 3600000) / 60000);
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

export default function Dashboard() {
  const { isRecording } = useStore();
  const [sessions, setSessions] = useState<BackendSession[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await listSessions();
        if (!cancelled) setSessions(data);
      } catch {
        // Silently fail — dashboard still usable
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  const totalNotes = sessions.reduce((sum, session) => sum + session.note_count, 0);

  return (
    <div className="p-6 space-y-8 animate-fade-in">
      {/* Welcome */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">ASTRA Dashboard</h1>
          <p className="text-sm text-text-secondary mt-1">
            Start a recording session or browse your structured notes
          </p>
        </div>
        <Link
          to="/session"
          className="flex items-center gap-2 px-5 py-2.5 bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30 rounded-xl text-sm font-semibold hover:bg-accent-cyan/25 transition-all"
        >
          <Radio className="w-4 h-4" />
          {isRecording ? 'Go to Active Session' : 'New Recording'}
        </Link>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="rounded-xl border border-accent-cyan/20 bg-accent-cyan/5 p-5">
          <MessageSquareText className="w-5 h-5 text-accent-cyan mb-3" />
          <p className="text-2xl font-bold text-accent-cyan font-mono">
            {loading ? '—' : totalNotes}
          </p>
          <p className="text-xs text-text-muted mt-1">Saved Notes</p>
        </div>
        <div className="rounded-xl border border-accent-green/20 bg-accent-green/5 p-5">
          <FileText className="w-5 h-5 text-accent-green mb-3" />
          <p className="text-2xl font-bold text-accent-green font-mono">
            {loading ? '—' : sessions.length}
          </p>
          <p className="text-xs text-text-muted mt-1">Total Sessions</p>
        </div>
        <div className="rounded-xl border border-space-border bg-space-panel p-5">
          <Radio
            className={`w-5 h-5 ${isRecording ? 'text-accent-red' : 'text-text-muted'} mb-3`}
          />
          <p
            className={`text-2xl font-bold font-mono ${isRecording ? 'text-accent-red' : 'text-text-muted'}`}
          >
            {isRecording ? 'Active' : 'Idle'}
          </p>
          <p className="text-xs text-text-muted mt-1">Session Status</p>
        </div>
      </div>

      {/* Recent Sessions */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-text-primary">Recent Sessions</h2>
          {sessions.length > 0 && (
            <Link
              to="/history"
              className="text-xs text-accent-cyan hover:underline flex items-center gap-1"
            >
              View all <ChevronRight className="w-3 h-3" />
            </Link>
          )}
        </div>

        {loading ? (
          <div className="rounded-xl border border-space-border bg-space-panel p-8 flex items-center justify-center">
            <Loader2 className="w-5 h-5 animate-spin text-accent-cyan mr-2" />
            <span className="text-sm text-text-muted">Loading sessions...</span>
          </div>
        ) : sessions.length === 0 ? (
          <div className="rounded-xl border border-space-border bg-space-panel p-8 text-center">
            <MessageSquareText className="w-12 h-12 mx-auto mb-3 text-text-muted opacity-20" />
            <p className="text-sm text-text-muted">No sessions yet</p>
            <p className="text-xs text-text-muted mt-1">
              Start a recording session — notes are auto-saved when you stop
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {sessions.slice(0, 5).map((session) => (
              <Link
                key={session.id}
                to={`/history/${session.id}`}
                className="flex items-center justify-between p-4 rounded-xl border border-space-border bg-space-panel hover:border-accent-cyan/20 transition-all group"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="p-1.5 rounded-lg bg-accent-cyan/10 shrink-0">
                    <MessageSquareText className="w-4 h-4 text-accent-cyan" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-sm font-semibold font-mono text-text-primary group-hover:text-accent-cyan transition-colors truncate">
                      {session.name}
                    </h3>
                    <p className="text-xs text-text-muted truncate">
                      {session.description || 'No description'}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-4 text-xs text-text-muted shrink-0 ml-4">
                  <div className="flex items-center gap-1.5">
                    <Calendar className="w-3 h-3" />
                    {formatDate(session.started_at)}
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Clock className="w-3 h-3" />
                    {formatDuration(session.started_at, session.ended_at)}
                  </div>
                  <div className="flex items-center gap-1.5">
                    <MessageSquareText className="w-3 h-3" />
                    {session.note_count} note{session.note_count !== 1 ? 's' : ''}
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-medium ${
                      session.status === 'active'
                        ? 'bg-accent-green/10 text-accent-green'
                        : 'bg-space-card text-text-muted'
                    }`}
                  >
                    {session.status}
                  </span>
                  <ChevronRight className="w-4 h-4 text-text-muted group-hover:text-accent-cyan" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
