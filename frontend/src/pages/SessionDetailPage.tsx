import { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Calendar,
  Clock,
  FileText,
  Download,
  Trash2,
  MessageSquareText,
  Users,
  Pencil,
  Check,
  X,
  Plus,
  Tag,
  Loader2,
} from 'lucide-react';
import {
  getSession,
  listNotes,
  updateNote,
  deleteNote,
  createNote,
  exportNotes,
} from '../services/api';
import type { BackendSession } from '../services/api';
import type { BackendNote, NoteType } from '../types';

const SPEAKER_COLORS = [
  { color: '#00d4ff', name: 'Speaker A', initials: 'SA' },
  { color: '#00e676', name: 'Speaker B', initials: 'SB' },
  { color: '#b388ff', name: 'Speaker C', initials: 'SC' },
  { color: '#ffab00', name: 'Speaker D', initials: 'SD' },
  { color: '#ff5252', name: 'Speaker E', initials: 'SE' },
];

const NOTE_TYPE_STYLES: Record<NoteType, { label: string; bg: string; text: string; border: string }> = {
  observation: { label: 'Observation', bg: 'bg-accent-cyan/10', text: 'text-accent-cyan', border: 'border-accent-cyan/20' },
  command: { label: 'Command', bg: 'bg-accent-amber/10', text: 'text-accent-amber', border: 'border-accent-amber/20' },
  system: { label: 'System', bg: 'bg-accent-purple/10', text: 'text-accent-purple', border: 'border-accent-purple/20' },
};

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
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
  const seconds = Math.floor((diffMs % 60000) / 1000);
  if (hours > 0) return `${hours}h ${minutes}m ${seconds}s`;
  return `${minutes}m ${seconds}s`;
}

function formatTime(dateStr: string): string {
  return new Date(dateStr).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function getSpeakerInfo(speaker: string | null, speakerMap: Map<string, number>) {
  const key = speaker || 'unknown';
  if (!speakerMap.has(key)) {
    speakerMap.set(key, speakerMap.size);
  }
  const idx = speakerMap.get(key)!;
  const info = SPEAKER_COLORS[idx % SPEAKER_COLORS.length];
  return { ...info, name: speaker || 'Unknown' };
}

/* ─── Inline editable text component ─── */

function EditableText({
  text,
  onSave,
  className,
  textareaClassName,
  rows = 3,
}: {
  text: string;
  onSave: (newText: string) => void;
  className?: string;
  textareaClassName?: string;
  rows?: number;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState('');
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (isEditing && ref.current) ref.current.focus();
  }, [isEditing]);

  const startEdit = () => {
    setEditValue(text);
    setIsEditing(true);
  };

  const save = () => {
    const trimmed = editValue.trim();
    if (trimmed && trimmed !== text) {
      onSave(trimmed);
    }
    setIsEditing(false);
  };

  const cancel = () => setIsEditing(false);

  if (isEditing) {
    return (
      <div>
        <textarea
          ref={ref}
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              save();
            }
            if (e.key === 'Escape') cancel();
          }}
          onBlur={save}
          rows={rows}
          className={
            textareaClassName ||
            'w-full text-sm leading-relaxed text-text-primary bg-space-card border border-accent-cyan/30 rounded-lg px-3 py-2 focus:outline-none focus:border-accent-cyan/60 resize-none'
          }
        />
        <div className="flex items-center gap-2 mt-1.5">
          <button
            onMouseDown={(e) => e.preventDefault()}
            onClick={save}
            className="flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/20 hover:bg-accent-cyan/20 transition-all"
          >
            <Check className="w-3 h-3" />
            Save
          </button>
          <button
            onMouseDown={(e) => e.preventDefault()}
            onClick={cancel}
            className="flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium text-text-muted hover:text-text-primary transition-all"
          >
            <X className="w-3 h-3" />
            Cancel
          </button>
        </div>
      </div>
    );
  }

  return (
    <span
      onClick={startEdit}
      className={`cursor-pointer rounded px-1 -mx-1 py-0.5 hover:bg-accent-cyan/5 transition-colors group/editable inline ${className || ''}`}
    >
      {text}
      <Pencil className="w-3 h-3 text-text-muted opacity-0 group-hover/editable:opacity-60 inline ml-1.5 transition-opacity" />
    </span>
  );
}

/* ─── New note form ─── */

function NewNoteForm({
  sessionId,
  onCreated,
}: {
  sessionId: string;
  onCreated: (note: BackendNote) => void;
}) {
  const [open, setOpen] = useState(false);
  const [content, setContent] = useState('');
  const [speaker, setSpeaker] = useState('');
  const [type, setType] = useState<NoteType>('observation');
  const [tagsInput, setTagsInput] = useState('');
  const [saving, setSaving] = useState(false);
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (open && ref.current) ref.current.focus();
  }, [open]);

  const reset = () => {
    setContent('');
    setSpeaker('');
    setType('observation');
    setTagsInput('');
    setOpen(false);
  };

  const handleSubmit = async () => {
    if (!content.trim()) return;
    setSaving(true);
    try {
      const tags = tagsInput
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean);
      const note = await createNote(sessionId, {
        timestamp: new Date().toISOString(),
        content: content.trim(),
        speaker: speaker.trim() || undefined,
        type,
        tags: tags.length > 0 ? tags : undefined,
      });
      onCreated(note);
      reset();
    } catch (err) {
      console.error('Failed to create note:', err);
    } finally {
      setSaving(false);
    }
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-2 px-4 py-2.5 w-full rounded-xl border border-dashed border-space-border text-sm text-text-muted hover:border-accent-cyan/30 hover:text-accent-cyan transition-all"
      >
        <Plus className="w-4 h-4" />
        Add a note manually
      </button>
    );
  }

  return (
    <div className="rounded-xl border border-accent-cyan/20 bg-space-panel p-4 space-y-3">
      <textarea
        ref={ref}
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="Note content..."
        rows={3}
        className="w-full text-sm text-text-primary bg-space-card border border-space-border rounded-lg px-3 py-2 focus:outline-none focus:border-accent-cyan/50 resize-none"
      />
      <div className="flex items-center gap-3 flex-wrap">
        <input
          value={speaker}
          onChange={(e) => setSpeaker(e.target.value)}
          placeholder="Speaker (optional)"
          className="text-xs bg-space-card border border-space-border rounded-lg px-3 py-1.5 text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-cyan/50 w-40"
        />
        <select
          value={type}
          onChange={(e) => setType(e.target.value as NoteType)}
          className="text-xs bg-space-card border border-space-border rounded-lg px-3 py-1.5 text-text-primary focus:outline-none focus:border-accent-cyan/50"
        >
          <option value="observation">Observation</option>
          <option value="command">Command</option>
          <option value="system">System</option>
        </select>
        <input
          value={tagsInput}
          onChange={(e) => setTagsInput(e.target.value)}
          placeholder="Tags (comma-separated)"
          className="text-xs bg-space-card border border-space-border rounded-lg px-3 py-1.5 text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-cyan/50 flex-1 min-w-[140px]"
        />
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={handleSubmit}
          disabled={saving || !content.trim()}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30 hover:bg-accent-cyan/25 disabled:opacity-40 transition-all"
        >
          {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Check className="w-3 h-3" />}
          Save Note
        </button>
        <button
          onClick={reset}
          className="px-3 py-1.5 rounded-lg text-xs font-medium text-text-muted hover:text-text-primary transition-all"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

/* ─── Main Page ─── */

export default function SessionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [session, setSession] = useState<BackendSession | null>(null);
  const [notes, setNotes] = useState<BackendNote[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingNoteId, setDeletingNoteId] = useState<string | null>(null);

  const speakerMap = useMemo(() => new Map<string, number>(), []);

  // Fetch session + notes from backend
  useEffect(() => {
    if (!id) return;
    let cancelled = false;

    async function load() {
      try {
        setLoading(true);
        setError(null);
        const [sess, notesList] = await Promise.all([
          getSession(id!),
          listNotes(id!),
        ]);
        if (cancelled) return;
        setSession(sess);
        setNotes(notesList);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : 'Failed to load session');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [id]);

  const handleEditNote = useCallback(
    async (noteId: string, newContent: string) => {
      if (!id) return;
      try {
        const updated = await updateNote(id, noteId, { content: newContent });
        setNotes((prev) => prev.map((n) => (n.id === noteId ? updated : n)));
      } catch (err) {
        console.error('Failed to update note:', err);
      }
    },
    [id],
  );

  const handleDeleteNote = useCallback(
    async (noteId: string) => {
      if (!id) return;
      if (deletingNoteId === noteId) {
        try {
          await deleteNote(id, noteId);
          setNotes((prev) => prev.filter((n) => n.id !== noteId));
        } catch (err) {
          console.error('Failed to delete note:', err);
        }
        setDeletingNoteId(null);
      } else {
        setDeletingNoteId(noteId);
        setTimeout(() => setDeletingNoteId(null), 3000);
      }
    },
    [id, deletingNoteId],
  );

  const handleNoteCreated = useCallback((note: BackendNote) => {
    setNotes((prev) => [...prev, note]);
  }, []);

  // Export via backend
  const handleExportMarkdown = useCallback(async () => {
    if (!id) return;
    try {
      const text = await exportNotes(id, 'markdown');
      const blob = new Blob([text], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${session?.name || 'session'}-notes.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export failed:', err);
    }
  }, [id, session?.name]);

  const handleExportJSON = useCallback(async () => {
    if (!id) return;
    try {
      const text = await exportNotes(id, 'json');
      const blob = new Blob([text], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${session?.name || 'session'}-notes.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export failed:', err);
    }
  }, [id, session?.name]);

  // Pre-populate speaker map
  notes.forEach((n) => getSpeakerInfo(n.speaker, speakerMap));
  const uniqueSpeakers = [...new Set(notes.map((n) => n.speaker || 'unknown'))];

  // Group by speaker
  const speakerGroups = useMemo(() => {
    const groups = new Map<string, BackendNote[]>();
    for (const n of notes) {
      const key = n.speaker || 'unknown';
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key)!.push(n);
    }
    return groups;
  }, [notes]);

  // ─── Loading / Error / Not Found ───

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-3.5rem)] text-text-muted">
        <Loader2 className="w-8 h-8 animate-spin mb-4 text-accent-cyan" />
        <p className="text-sm">Loading session...</p>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-3.5rem)] text-text-muted">
        <MessageSquareText className="w-16 h-16 mb-4 opacity-20" />
        <p className="text-base font-medium mb-2">{error || 'Session not found'}</p>
        <button
          onClick={() => navigate('/history')}
          className="flex items-center gap-2 text-sm text-accent-cyan hover:underline"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Structured Notes
        </button>
      </div>
    );
  }

  const durationStr = formatDuration(session.started_at, session.ended_at);

  return (
    <div className="p-6 space-y-5 animate-fade-in">
      {/* ─── Header ─── */}
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <button
            onClick={() => navigate('/history')}
            className="flex items-center gap-1.5 text-sm text-text-muted hover:text-accent-cyan transition-colors mb-3"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Structured Notes
          </button>

          <h1 className="text-2xl font-bold font-mono text-text-primary mb-1">
            {session.name}
          </h1>
          {session.description && (
            <p className="text-sm text-text-secondary">{session.description}</p>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={handleExportMarkdown}
            className="flex items-center gap-2 px-4 py-2 bg-space-card border border-space-border rounded-lg text-sm text-text-secondary hover:border-accent-cyan/30 hover:text-accent-cyan transition-all"
          >
            <Download className="w-4 h-4" />
            MD
          </button>
          <button
            onClick={handleExportJSON}
            className="flex items-center gap-2 px-4 py-2 bg-space-card border border-space-border rounded-lg text-sm text-text-secondary hover:border-accent-cyan/30 hover:text-accent-cyan transition-all"
          >
            <Download className="w-4 h-4" />
            JSON
          </button>
        </div>
      </div>

      {/* Session Meta */}
      <div className="flex items-center gap-6 text-xs text-text-muted">
        <div className="flex items-center gap-1.5">
          <Calendar className="w-3.5 h-3.5" />
          {formatDate(session.started_at)}
        </div>
        <div className="flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5" />
          {durationStr}
        </div>
        <div className="flex items-center gap-1.5">
          <FileText className="w-3.5 h-3.5" />
          {notes.length} note{notes.length !== 1 ? 's' : ''}
        </div>
        <div className="flex items-center gap-1.5">
          <Users className="w-3.5 h-3.5" />
          {uniqueSpeakers.length} speaker{uniqueSpeakers.length !== 1 ? 's' : ''}
        </div>
        <span
          className={`px-2 py-0.5 rounded text-[11px] font-medium ${
            session.status === 'active'
              ? 'bg-accent-green/10 text-accent-green border border-accent-green/20'
              : 'bg-space-card border border-space-border'
          }`}
        >
          {session.status}
        </span>
      </div>

      {/* ═══════════════ Two-column Layout ═══════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-5 items-start">
        {/* ─── Left: Notes List ─── */}
        <div className="space-y-5 min-w-0">
          {/* Add note form */}
          <NewNoteForm sessionId={session.id} onCreated={handleNoteCreated} />

          {/* Notes */}
          <div className="rounded-xl border border-space-border bg-space-panel overflow-hidden">
            <div className="px-5 py-3 border-b border-space-border flex items-center justify-between">
              <div className="flex items-center gap-2">
                <MessageSquareText className="w-4 h-4 text-accent-cyan" />
                <h2 className="text-sm font-semibold text-text-primary">Notes</h2>
              </div>
              <span className="text-[10px] text-text-muted">Click text to edit</span>
            </div>

            {notes.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-text-muted">
                <FileText className="w-12 h-12 mb-3 opacity-20" />
                <p className="text-sm font-medium">No notes yet</p>
                <p className="text-xs mt-1">
                  Notes will appear here as the AI model processes audio, or add one manually above.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-space-border">
                {notes.map((note) => {
                  const speaker = getSpeakerInfo(note.speaker, speakerMap);
                  const typeStyle = NOTE_TYPE_STYLES[note.type] || NOTE_TYPE_STYLES.observation;

                  return (
                    <div
                      key={note.id}
                      className="px-5 py-3.5 hover:bg-space-card/30 transition-colors group"
                    >
                      <div className="flex items-start gap-3">
                        {/* Timestamp */}
                        <span className="text-[11px] text-text-muted font-mono bg-space-card px-1.5 py-0.5 rounded shrink-0 mt-0.5">
                          {formatTime(note.timestamp)}
                        </span>

                        {/* Speaker */}
                        <span
                          className="text-xs font-semibold shrink-0 mt-0.5"
                          style={{ color: speaker.color }}
                        >
                          {speaker.name}
                        </span>

                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          <EditableText
                            text={note.content}
                            onSave={(newText) => handleEditNote(note.id, newText)}
                            className="text-sm text-text-primary leading-relaxed"
                          />

                          {/* Tags + Type badge */}
                          <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                            <span
                              className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${typeStyle.bg} ${typeStyle.text} ${typeStyle.border}`}
                            >
                              {typeStyle.label}
                            </span>
                            {note.tags.map((tag) => (
                              <span
                                key={tag}
                                className="text-[10px] text-text-muted px-1.5 py-0.5 rounded bg-space-card border border-space-border flex items-center gap-1"
                              >
                                <Tag className="w-2.5 h-2.5" />
                                {tag}
                              </span>
                            ))}
                          </div>
                        </div>

                        {/* Delete button */}
                        <button
                          onClick={() => handleDeleteNote(note.id)}
                          className={`p-1.5 rounded-lg shrink-0 opacity-0 group-hover:opacity-100 transition-all ${
                            deletingNoteId === note.id
                              ? 'text-accent-red bg-accent-red/15 opacity-100'
                              : 'text-text-muted hover:text-accent-red hover:bg-accent-red/10'
                          }`}
                          title={
                            deletingNoteId === note.id
                              ? 'Click again to confirm'
                              : 'Delete note'
                          }
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* ─── Right: Speaker Sidebar ─── */}
        <div className="space-y-4 lg:sticky lg:top-4">
          <div className="rounded-xl border border-space-border bg-space-panel p-4">
            <h2 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
              <Users className="w-4 h-4 text-accent-cyan" />
              Speakers
            </h2>

            {uniqueSpeakers.length === 0 ? (
              <p className="text-xs text-text-muted">No speakers yet</p>
            ) : (
              <div className="space-y-4">
                {uniqueSpeakers.map((spkKey) => {
                  const speaker = getSpeakerInfo(spkKey, speakerMap);
                  const entries = speakerGroups.get(spkKey) || [];

                  return (
                    <div key={spkKey}>
                      <div className="flex items-center gap-2.5 mb-2">
                        <div
                          className="w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0"
                          style={{
                            backgroundColor: speaker.color + '18',
                            color: speaker.color,
                            border: `1.5px solid ${speaker.color}30`,
                          }}
                        >
                          {speaker.initials}
                        </div>
                        <div className="min-w-0">
                          <span className="text-xs font-semibold" style={{ color: speaker.color }}>
                            {speaker.name}
                          </span>
                          <span className="text-[10px] text-text-muted ml-2">
                            {entries.length} note{entries.length !== 1 ? 's' : ''}
                          </span>
                        </div>
                      </div>

                      <div className="space-y-1.5 pl-9">
                        {entries.map((entry) => (
                          <div
                            key={`sidebar-${entry.id}`}
                            className="text-xs text-text-secondary leading-relaxed"
                          >
                            <span className="text-[10px] text-text-muted font-mono mr-1.5">
                              {formatTime(entry.timestamp)}
                            </span>
                            {entry.content.length > 80
                              ? entry.content.slice(0, 80) + '...'
                              : entry.content}
                          </div>
                        ))}
                      </div>

                      {spkKey !== uniqueSpeakers[uniqueSpeakers.length - 1] && (
                        <div className="border-b border-space-border mt-3" />
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
