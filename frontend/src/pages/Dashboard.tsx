import {
  Radio,
  MessageSquareText,
  FileText,
  Clock,
  Calendar,
  ChevronRight,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { useStore } from '../store/useStore';

function formatDate(date: Date): string {
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
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

export default function Dashboard() {
  const { sessions, isRecording } = useStore();

  const completedSessions = sessions.filter((s) => s.status === 'completed');
  const totalEntries = completedSessions.reduce(
    (acc, s) => acc + (s.transcriptions?.length || s.logCount),
    0
  );

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
            {completedSessions.length}
          </p>
          <p className="text-xs text-text-muted mt-1">Saved Notes</p>
        </div>
        <div className="rounded-xl border border-accent-green/20 bg-accent-green/5 p-5">
          <FileText className="w-5 h-5 text-accent-green mb-3" />
          <p className="text-2xl font-bold text-accent-green font-mono">{totalEntries}</p>
          <p className="text-xs text-text-muted mt-1">Total Entries</p>
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

      {/* Recent Notes */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-text-primary">Recent Notes</h2>
          {completedSessions.length > 0 && (
            <Link
              to="/history"
              className="text-xs text-accent-cyan hover:underline flex items-center gap-1"
            >
              View all <ChevronRight className="w-3 h-3" />
            </Link>
          )}
        </div>

        {completedSessions.length === 0 ? (
          <div className="rounded-xl border border-space-border bg-space-panel p-8 text-center">
            <MessageSquareText className="w-12 h-12 mx-auto mb-3 text-text-muted opacity-20" />
            <p className="text-sm text-text-muted">No notes yet</p>
            <p className="text-xs text-text-muted mt-1">
              Start a recording session — notes are auto-saved when you stop
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {completedSessions.slice(0, 5).map((session) => (
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
                      {session.description}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-4 text-xs text-text-muted shrink-0 ml-4">
                  <div className="flex items-center gap-1.5">
                    <Calendar className="w-3 h-3" />
                    {formatDate(session.startTime)}
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Clock className="w-3 h-3" />
                    {formatDuration(session.startTime, session.endTime)}
                  </div>
                  <span className="font-mono">
                    {session.transcriptions?.length || session.logCount} entries
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
