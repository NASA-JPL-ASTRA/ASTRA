import { useState, useRef, useEffect, useMemo } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
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
  AlertTriangle,
  CheckCircle2,
  Zap,
} from 'lucide-react';
import { useStore } from '../store/useStore';
import { getSession } from '../services/api';
import type { SavedTranscription, Session } from '../types';

const SPEAKER_COLORS = [
  { color: '#00d4ff', name: 'Speaker A', initials: 'SA' },
  { color: '#00e676', name: 'Speaker B', initials: 'SB' },
  { color: '#b388ff', name: 'Speaker C', initials: 'SC' },
  { color: '#ffab00', name: 'Speaker D', initials: 'SD' },
  { color: '#ff5252', name: 'Speaker E', initials: 'SE' },
];

function formatDate(date: Date): string {
  return date.toLocaleDateString('en-US', {
    weekday: 'short',
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
  const seconds = Math.floor((diffMs % 60000) / 1000);
  if (hours > 0) return `${hours}h ${minutes}m ${seconds}s`;
  return `${minutes}m ${seconds}s`;
}

function formatElapsed(sessionStart: Date, entryTimestamp: string): string {
  const offsetSec = Math.max(
    0,
    Math.floor((new Date(entryTimestamp).getTime() - sessionStart.getTime()) / 1000)
  );
  const m = Math.floor(offsetSec / 60);
  const s = offsetSec % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

/* ─── Keyword extraction helpers ─── */

function matchesIssue(text: string) {
  return /anomal|issue|oscillat|drift|error|fault|grounding|noise|warning|problem/i.test(text);
}
function matchesConfirmation(text: string) {
  return /confirm|complete|passed|nominal|stable|clean|improved|excellent|good|looking good/i.test(text);
}
function matchesAction(text: string) {
  return /initiat|switch|begin|start|adjust|mark|log|running|proceed|setting|replacing|test/i.test(text);
}

/* ─── Speaker helper ─── */

function getSpeakerInfo(speakerId: string, speakerMap: Map<string, number>) {
  if (!speakerMap.has(speakerId)) {
    speakerMap.set(speakerId, speakerMap.size);
  }
  const idx = speakerMap.get(speakerId)!;
  return SPEAKER_COLORS[idx % SPEAKER_COLORS.length];
}

/* ─── Auto-generated summary text ─── */

function generateAutoSummary(
  transcriptions: SavedTranscription[],
  uniqueSpeakerCount: number,
  duration: string,
  issueCount: number,
  confirmCount: number
): string {
  let text = `Recording session with ${uniqueSpeakerCount} speaker${uniqueSpeakerCount !== 1 ? 's' : ''} and ${transcriptions.length} transcription entries over ${duration}.`;
  if (issueCount > 0) {
    text += ` ${issueCount} issue${issueCount !== 1 ? 's' : ''} / anomal${issueCount !== 1 ? 'ies' : 'y'} detected.`;
  }
  if (confirmCount > 0) {
    text += ` ${confirmCount} confirmation${confirmCount !== 1 ? 's' : ''} recorded.`;
  }
  return text;
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

function backendToSession(s: import('../services/api').BackendSession): Session {
  const notes = s.notes ?? [];
  return {
    id: s.id,
    name: s.name,
    description: s.description ?? 'No description',
    startTime: new Date(s.started_at),
    endTime: s.ended_at ? new Date(s.ended_at) : undefined,
    status: s.status === 'ended' ? 'completed' : 'active',
    operators: [],
    logCount: notes.length,
    telemetryStreams: 0,
    testbed: 'Backend Session',
    transcriptions: notes.map((n) => ({
      id: n.id,
      timestamp: n.timestamp,
      speakerId: n.speaker ?? 'speaker_0',
      rawText: n.content,
      confidence: n.confidence ?? 0.9,
      isFinal: true,
    })),
  };
}

export default function SessionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { sessions, deleteSession, updateSession, updateSessionTranscription } = useStore();
  const [fetchedSession, setFetchedSession] = useState<Session | null>(null);

  // Use session from navigation state (HistoryPage), from store, or fetch from API
  const sessionFromState = (location.state as { session?: Session } | null)?.session;
  const sessionFromStore = sessions.find((s) => s.id === id);

  useEffect(() => {
    if (!sessionFromState && !sessionFromStore && id) {
      getSession(id)
        .then(backendToSession)
        .then(setFetchedSession)
        .catch(() => setFetchedSession(null));
    } else {
      setFetchedSession(null);
    }
  }, [id, sessionFromState, sessionFromStore]);

  const session = sessionFromState ?? sessionFromStore ?? fetchedSession;

  // Editing state for name & description
  const [editingName, setEditingName] = useState(false);
  const [editingDesc, setEditingDesc] = useState(false);
  const [nameValue, setNameValue] = useState('');
  const [descValue, setDescValue] = useState('');

  // Editing state for summary
  const [editingSummary, setEditingSummary] = useState(false);
  const [summaryValue, setSummaryValue] = useState('');

  const nameInputRef = useRef<HTMLInputElement>(null);
  const descInputRef = useRef<HTMLTextAreaElement>(null);
  const summaryInputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (editingName && nameInputRef.current) {
      nameInputRef.current.focus();
      nameInputRef.current.select();
    }
  }, [editingName]);

  useEffect(() => {
    if (editingDesc && descInputRef.current) {
      descInputRef.current.focus();
      descInputRef.current.select();
    }
  }, [editingDesc]);

  useEffect(() => {
    if (editingSummary && summaryInputRef.current) {
      summaryInputRef.current.focus();
    }
  }, [editingSummary]);

  // Stable speaker map
  const speakerMap = useMemo(() => new Map<string, number>(), []);

  if (!session) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-3.5rem)] text-text-muted">
        <MessageSquareText className="w-16 h-16 mb-4 opacity-20" />
        <p className="text-base font-medium mb-2">Session not found</p>
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

  const allTranscriptions = session.transcriptions || [];
  const transcriptions = allTranscriptions.filter((t) => t.confidence >= 0.5);

  // Pre-populate speaker map
  transcriptions.forEach((t) => getSpeakerInfo(t.speakerId, speakerMap));

  const uniqueSpeakerIds = [...new Set(transcriptions.map((t) => t.speakerId))];

  // Group by speaker
  const speakerGroups = useMemo(() => {
    const groups = new Map<string, SavedTranscription[]>();
    for (const t of transcriptions) {
      if (!groups.has(t.speakerId)) groups.set(t.speakerId, []);
      groups.get(t.speakerId)!.push(t);
    }
    return groups;
  }, [transcriptions]);

  // Key observations
  const issues = useMemo(
    () => transcriptions.filter((t) => matchesIssue(t.rawText)),
    [transcriptions]
  );
  const confirmations = useMemo(
    () => transcriptions.filter((t) => matchesConfirmation(t.rawText)),
    [transcriptions]
  );
  const actions = useMemo(
    () => transcriptions.filter((t) => matchesAction(t.rawText)),
    [transcriptions]
  );

  const durationStr = formatDuration(session.startTime, session.endTime);
  const autoSummary = generateAutoSummary(
    transcriptions,
    uniqueSpeakerIds.length,
    durationStr,
    issues.length,
    confirmations.length
  );
  const displaySummary = session.summary || autoSummary;

  // ─── Editing handlers ───

  const startEditName = () => {
    setNameValue(session.name);
    setEditingName(true);
  };
  const saveName = () => {
    const trimmed = nameValue.trim();
    if (trimmed && trimmed !== session.name) updateSession(session.id, { name: trimmed });
    setEditingName(false);
  };
  const cancelEditName = () => setEditingName(false);

  const startEditDesc = () => {
    setDescValue(session.description);
    setEditingDesc(true);
  };
  const saveDesc = () => {
    const trimmed = descValue.trim();
    if (trimmed !== session.description) updateSession(session.id, { description: trimmed });
    setEditingDesc(false);
  };
  const cancelEditDesc = () => setEditingDesc(false);

  const startEditSummary = () => {
    setSummaryValue(displaySummary);
    setEditingSummary(true);
  };
  const saveSummary = () => {
    const trimmed = summaryValue.trim();
    if (trimmed && trimmed !== displaySummary) updateSession(session.id, { summary: trimmed });
    setEditingSummary(false);
  };
  const cancelEditSummary = () => setEditingSummary(false);

  const handleSaveTranscription = (transcriptionId: string, newText: string) => {
    updateSessionTranscription(session.id, transcriptionId, newText);
  };

  // ─── Export handlers ───

  const handleExport = () => {
    const lines: string[] = [];
    lines.push(`# ${session.name}`);
    lines.push(`# ${session.description}`);
    lines.push(`# Start: ${session.startTime.toISOString()}`);
    if (session.endTime) lines.push(`# End: ${session.endTime.toISOString()}`);
    lines.push(`# Testbed: ${session.testbed}`);
    lines.push(`# Entries: ${transcriptions.length}`);
    lines.push('');
    lines.push('## Summary');
    lines.push(displaySummary);
    lines.push('');

    if (issues.length > 0) {
      lines.push('## Issues & Anomalies');
      for (const t of issues) {
        const speaker = getSpeakerInfo(t.speakerId, speakerMap);
        lines.push(`  - [${speaker.name}] ${t.rawText}`);
      }
      lines.push('');
    }
    if (confirmations.length > 0) {
      lines.push('## Confirmations');
      for (const t of confirmations) {
        const speaker = getSpeakerInfo(t.speakerId, speakerMap);
        lines.push(`  - [${speaker.name}] ${t.rawText}`);
      }
      lines.push('');
    }

    lines.push('## Full Transcript');
    for (const t of transcriptions) {
      const elapsed = formatElapsed(session.startTime, t.timestamp);
      const speaker = getSpeakerInfo(t.speakerId, speakerMap);
      lines.push(`[${elapsed}] ${speaker.name}: ${t.rawText}`);
    }

    const blob = new Blob([lines.join('\n')], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${session.name}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportJSON = () => {
    const data = {
      session: {
        id: session.id,
        name: session.name,
        description: session.description,
        summary: displaySummary,
        startTime: session.startTime.toISOString(),
        endTime: session.endTime?.toISOString(),
        testbed: session.testbed,
      },
      transcriptions,
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${session.name}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDelete = () => {
    if (window.confirm(`Delete "${session.name}"? This action cannot be undone.`)) {
      deleteSession(session.id);
      navigate('/history');
    }
  };

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

          {/* Editable name */}
          {editingName ? (
            <div className="flex items-center gap-2 mb-1">
              <input
                ref={nameInputRef}
                value={nameValue}
                onChange={(e) => setNameValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') saveName();
                  if (e.key === 'Escape') cancelEditName();
                }}
                onBlur={saveName}
                className="text-2xl font-bold font-mono text-text-primary bg-space-card border border-accent-cyan/30 rounded-lg px-3 py-1 focus:outline-none focus:border-accent-cyan/60 w-full max-w-lg"
              />
            </div>
          ) : (
            <div className="flex items-center gap-2 group/name mb-1">
              <h1 className="text-2xl font-bold font-mono text-text-primary">
                {session.name}
              </h1>
              <button
                onClick={startEditName}
                className="p-1 rounded text-text-muted opacity-0 group-hover/name:opacity-100 hover:text-accent-cyan hover:bg-accent-cyan/10 transition-all"
                title="Edit name"
              >
                <Pencil className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* Editable description */}
          {editingDesc ? (
            <div className="mt-1">
              <textarea
                ref={descInputRef}
                value={descValue}
                onChange={(e) => setDescValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    saveDesc();
                  }
                  if (e.key === 'Escape') cancelEditDesc();
                }}
                onBlur={saveDesc}
                rows={2}
                className="text-sm text-text-secondary bg-space-card border border-accent-cyan/30 rounded-lg px-3 py-2 focus:outline-none focus:border-accent-cyan/60 w-full max-w-lg resize-none"
              />
            </div>
          ) : (
            <div className="flex items-center gap-2 group/desc mt-1">
              <p className="text-sm text-text-secondary">{session.description}</p>
              <button
                onClick={startEditDesc}
                className="p-1 rounded text-text-muted opacity-0 group-hover/desc:opacity-100 hover:text-accent-cyan hover:bg-accent-cyan/10 transition-all shrink-0"
                title="Edit description"
              >
                <Pencil className="w-3 h-3" />
              </button>
            </div>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={handleExport}
            className="flex items-center gap-2 px-4 py-2 bg-space-card border border-space-border rounded-lg text-sm text-text-secondary hover:border-accent-cyan/30 hover:text-accent-cyan transition-all"
          >
            <Download className="w-4 h-4" />
            TXT
          </button>
          <button
            onClick={handleExportJSON}
            className="flex items-center gap-2 px-4 py-2 bg-space-card border border-space-border rounded-lg text-sm text-text-secondary hover:border-accent-cyan/30 hover:text-accent-cyan transition-all"
          >
            <Download className="w-4 h-4" />
            JSON
          </button>
          <button
            onClick={handleDelete}
            className="flex items-center gap-2 px-4 py-2 bg-space-card border border-space-border rounded-lg text-sm text-text-secondary hover:border-accent-red/30 hover:text-accent-red transition-all"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Session Meta */}
      <div className="flex items-center gap-6 text-xs text-text-muted">
        <div className="flex items-center gap-1.5">
          <Calendar className="w-3.5 h-3.5" />
          {formatDate(session.startTime)}
        </div>
        <div className="flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5" />
          {durationStr}
        </div>
        <div className="flex items-center gap-1.5">
          <FileText className="w-3.5 h-3.5" />
          {transcriptions.length} entries
        </div>
        <div className="flex items-center gap-1.5">
          <Users className="w-3.5 h-3.5" />
          {uniqueSpeakerIds.length} speaker{uniqueSpeakerIds.length !== 1 ? 's' : ''}
        </div>
        <span className="px-2 py-0.5 rounded bg-space-card border border-space-border">
          {session.testbed}
        </span>
      </div>

      {/* ═══════════════ Two-column Layout ═══════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-5 items-start">
        {/* ─── Left: Structured Document ─── */}
        <div className="space-y-5 min-w-0">
          {/* Editable Summary Card */}
          <div className="rounded-xl border border-space-border bg-space-panel p-5">
            <h2 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
              <FileText className="w-4 h-4 text-accent-cyan" />
              Summary
            </h2>
            {editingSummary ? (
              <div>
                <textarea
                  ref={summaryInputRef}
                  value={summaryValue}
                  onChange={(e) => setSummaryValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      saveSummary();
                    }
                    if (e.key === 'Escape') cancelEditSummary();
                  }}
                  onBlur={saveSummary}
                  rows={4}
                  className="w-full text-sm text-text-secondary leading-relaxed bg-space-card border border-accent-cyan/30 rounded-lg px-3 py-2 focus:outline-none focus:border-accent-cyan/60 resize-none"
                />
                <div className="flex items-center gap-2 mt-2">
                  <button
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={saveSummary}
                    className="flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-medium bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/20 hover:bg-accent-cyan/20 transition-all"
                  >
                    <Check className="w-3 h-3" />
                    Save
                  </button>
                  <button
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={cancelEditSummary}
                    className="flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-medium text-text-muted hover:text-text-primary transition-all"
                  >
                    <X className="w-3 h-3" />
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className="group/summary">
                <p
                  onClick={startEditSummary}
                  className="text-sm text-text-secondary leading-relaxed cursor-pointer rounded px-1 -mx-1 py-1 hover:bg-accent-cyan/5 transition-colors"
                >
                  {displaySummary}
                  <Pencil className="w-3 h-3 text-text-muted opacity-0 group-hover/summary:opacity-60 inline ml-1.5 transition-opacity" />
                </p>
              </div>
            )}
          </div>

          {/* Key Observations (editable entries) */}
          {(issues.length > 0 || confirmations.length > 0 || actions.length > 0) && (
            <div className="rounded-xl border border-space-border bg-space-panel p-5">
              <h2 className="text-sm font-semibold text-text-primary mb-4 flex items-center gap-2">
                <Zap className="w-4 h-4 text-accent-cyan" />
                Key Observations
                <span className="text-[10px] text-text-muted font-normal ml-auto">
                  Click text to edit
                </span>
              </h2>
              <div className="space-y-4">
                {/* Issues */}
                {issues.length > 0 && (
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <AlertTriangle className="w-3.5 h-3.5 text-accent-amber" />
                      <span className="text-xs font-semibold text-accent-amber">
                        Issues & Anomalies ({issues.length})
                      </span>
                    </div>
                    <div className="space-y-1.5 pl-5">
                      {issues.map((t) => {
                        const speaker = getSpeakerInfo(t.speakerId, speakerMap);
                        return (
                          <div
                            key={`obs-issue-${t.id}`}
                            className="text-xs text-text-secondary leading-relaxed flex gap-2"
                          >
                            <span
                              className="font-semibold shrink-0"
                              style={{ color: speaker.color }}
                            >
                              {speaker.name}:
                            </span>
                            <EditableText
                              text={t.rawText}
                              onSave={(newText) => handleSaveTranscription(t.id, newText)}
                              className="text-xs text-text-secondary leading-relaxed"
                              textareaClassName="w-full text-xs leading-relaxed text-text-primary bg-space-card border border-accent-cyan/30 rounded-lg px-2 py-1.5 focus:outline-none focus:border-accent-cyan/60 resize-none"
                              rows={2}
                            />
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Confirmations */}
                {confirmations.length > 0 && (
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <CheckCircle2 className="w-3.5 h-3.5 text-accent-green" />
                      <span className="text-xs font-semibold text-accent-green">
                        Confirmations ({confirmations.length})
                      </span>
                    </div>
                    <div className="space-y-1.5 pl-5">
                      {confirmations.map((t) => {
                        const speaker = getSpeakerInfo(t.speakerId, speakerMap);
                        return (
                          <div
                            key={`obs-conf-${t.id}`}
                            className="text-xs text-text-secondary leading-relaxed flex gap-2"
                          >
                            <span
                              className="font-semibold shrink-0"
                              style={{ color: speaker.color }}
                            >
                              {speaker.name}:
                            </span>
                            <EditableText
                              text={t.rawText}
                              onSave={(newText) => handleSaveTranscription(t.id, newText)}
                              className="text-xs text-text-secondary leading-relaxed"
                              textareaClassName="w-full text-xs leading-relaxed text-text-primary bg-space-card border border-accent-cyan/30 rounded-lg px-2 py-1.5 focus:outline-none focus:border-accent-cyan/60 resize-none"
                              rows={2}
                            />
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Actions */}
                {actions.length > 0 && (
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <Zap className="w-3.5 h-3.5 text-accent-cyan" />
                      <span className="text-xs font-semibold text-accent-cyan">
                        Actions & Commands ({actions.length})
                      </span>
                    </div>
                    <div className="space-y-1.5 pl-5">
                      {actions.map((t) => {
                        const speaker = getSpeakerInfo(t.speakerId, speakerMap);
                        return (
                          <div
                            key={`obs-act-${t.id}`}
                            className="text-xs text-text-secondary leading-relaxed flex gap-2"
                          >
                            <span
                              className="font-semibold shrink-0"
                              style={{ color: speaker.color }}
                            >
                              {speaker.name}:
                            </span>
                            <EditableText
                              text={t.rawText}
                              onSave={(newText) => handleSaveTranscription(t.id, newText)}
                              className="text-xs text-text-secondary leading-relaxed"
                              textareaClassName="w-full text-xs leading-relaxed text-text-primary bg-space-card border border-accent-cyan/30 rounded-lg px-2 py-1.5 focus:outline-none focus:border-accent-cyan/60 resize-none"
                              rows={2}
                            />
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Full Transcript (editable entries) */}
          <div className="rounded-xl border border-space-border bg-space-panel overflow-hidden">
            <div className="px-5 py-3 border-b border-space-border flex items-center justify-between">
              <div className="flex items-center gap-2">
                <MessageSquareText className="w-4 h-4 text-accent-cyan" />
                <h2 className="text-sm font-semibold text-text-primary">Full Transcript</h2>
              </div>
              <span className="text-[10px] text-text-muted">Click text to edit</span>
            </div>

            {transcriptions.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-text-muted">
                <FileText className="w-12 h-12 mb-3 opacity-20" />
                <p className="text-sm font-medium">No transcription data</p>
              </div>
            ) : (
              <div className="divide-y divide-space-border">
                {transcriptions.map((entry) => {
                  const speaker = getSpeakerInfo(entry.speakerId, speakerMap);
                  const elapsed = formatElapsed(session.startTime, entry.timestamp);

                  return (
                    <div
                      key={entry.id}
                      className="px-5 py-3.5 hover:bg-space-card/30 transition-colors"
                    >
                      <div className="flex items-start gap-3">
                        {/* Elapsed time */}
                        <span className="text-[11px] text-text-muted font-mono bg-space-card px-1.5 py-0.5 rounded shrink-0 mt-0.5">
                          {elapsed}
                        </span>

                        {/* Speaker */}
                        <span
                          className="text-xs font-semibold shrink-0 mt-0.5"
                          style={{ color: speaker.color }}
                        >
                          {speaker.name}
                        </span>

                        {/* Editable text */}
                        <div className="flex-1 min-w-0">
                          <EditableText
                            text={entry.rawText}
                            onSave={(newText) => handleSaveTranscription(entry.id, newText)}
                            className="text-sm text-text-primary leading-relaxed"
                          />
                        </div>

                        {/* Confidence (0–50% red, 50–85% yellow, 85–100% green) */}
                        <div className="flex items-center gap-1 shrink-0 mt-0.5">
                          <div
                            className={`w-1.5 h-1.5 rounded-full ${
                              entry.confidence >= 0.85
                                ? 'bg-accent-green'
                                : entry.confidence >= 0.5
                                  ? 'bg-accent-amber'
                                  : 'bg-accent-red'
                            }`}
                          />
                          <span className="text-[10px] text-text-muted font-mono">
                            {(entry.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* ─── Right: Speaker Sidebar (editable entries) ─── */}
        <div className="space-y-4 lg:sticky lg:top-4">
          <div className="rounded-xl border border-space-border bg-space-panel p-4">
            <h2 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
              <Users className="w-4 h-4 text-accent-cyan" />
              Speakers
            </h2>

            <div className="space-y-4">
              {uniqueSpeakerIds.map((speakerId) => {
                const speaker = getSpeakerInfo(speakerId, speakerMap);
                const entries = speakerGroups.get(speakerId) || [];

                return (
                  <div key={speakerId}>
                    {/* Speaker header */}
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
                          {entries.length} entr{entries.length !== 1 ? 'ies' : 'y'}
                        </span>
                      </div>
                    </div>

                    {/* Speaker's entries (editable) */}
                    <div className="space-y-1.5 pl-9">
                      {entries.map((entry) => {
                        const elapsed = formatElapsed(session.startTime, entry.timestamp);
                        return (
                          <div
                            key={`sidebar-${entry.id}`}
                            className="text-xs text-text-secondary leading-relaxed"
                          >
                            <span className="text-[10px] text-text-muted font-mono mr-1.5">
                              {elapsed}
                            </span>
                            <EditableText
                              text={entry.rawText}
                              onSave={(newText) => handleSaveTranscription(entry.id, newText)}
                              className="text-xs text-text-secondary leading-relaxed"
                              textareaClassName="w-full text-xs leading-relaxed text-text-primary bg-space-card border border-accent-cyan/30 rounded-lg px-2 py-1.5 focus:outline-none focus:border-accent-cyan/60 resize-none"
                              rows={2}
                            />
                          </div>
                        );
                      })}
                    </div>

                    {/* Separator */}
                    {speakerId !== uniqueSpeakerIds[uniqueSpeakerIds.length - 1] && (
                      <div className="border-b border-space-border mt-3" />
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
