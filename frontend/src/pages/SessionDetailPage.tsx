import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  Check,
  Download,
  Loader2,
  MessageSquareText,
  Pencil,
  Search,
  Send,
} from 'lucide-react';
import { exportNotes, getSession, listNotes } from '../services/api';
import type { BackendSession } from '../services/api';
import type { BackendNote } from '../types';

const SPEAKER_COLORS = ['#00d4ff', '#00e676', '#b388ff', '#ffab00', '#ff5252'];

const DEMO_SESSION: BackendSession = {
  id: 'preview',
  name: 'REC-20260427-084923',
  description: 'Preview of the structured meeting note layout.',
  status: 'ended',
  started_at: '2026-04-27T15:49:23Z',
  ended_at: '2026-04-27T15:53:35Z',
  note_count: 6,
};

const DEMO_NOTES: BackendNote[] = [
  {
    id: 'note_preview_1',
    session_id: 'preview',
    timestamp: '2026-04-27T15:49:23Z',
    speaker: 'Speaker 1',
    content: 'Hi everyone, my name is Ryan.',
    type: 'observation',
    tags: ['auto-transcription', 'diarized'],
    telemetry_snapshot: null,
    created_at: '2026-04-27T15:49:23Z',
    updated_at: '2026-04-27T15:49:23Z',
  },
  {
    id: 'note_preview_2',
    session_id: 'preview',
    timestamp: '2026-04-27T15:49:26Z',
    speaker: 'Speaker 1',
    content: 'Hello, and this is the test through the OpenAI GPT transcriber model.',
    type: 'observation',
    tags: ['auto-transcription', 'diarized'],
    telemetry_snapshot: null,
    created_at: '2026-04-27T15:49:26Z',
    updated_at: '2026-04-27T15:49:26Z',
  },
  {
    id: 'note_preview_3',
    session_id: 'preview',
    timestamp: '2026-04-27T15:50:14Z',
    speaker: 'Speaker 2',
    content: 'The goal is to keep the final notes readable while preserving the raw transcript on the side.',
    type: 'observation',
    tags: ['auto-transcription', 'diarized'],
    telemetry_snapshot: null,
    created_at: '2026-04-27T15:50:14Z',
    updated_at: '2026-04-27T15:50:14Z',
  },
  {
    id: 'note_preview_4',
    session_id: 'preview',
    timestamp: '2026-04-27T15:51:02Z',
    speaker: 'Speaker 1',
    content: 'We should summarize action items, decisions, and any issues separately from the transcript.',
    type: 'observation',
    tags: ['auto-transcription', 'diarized'],
    telemetry_snapshot: null,
    created_at: '2026-04-27T15:51:02Z',
    updated_at: '2026-04-27T15:51:02Z',
  },
  {
    id: 'note_preview_5',
    session_id: 'preview',
    timestamp: '2026-04-27T15:52:11Z',
    speaker: 'Speaker 2',
    content: 'Agreed. The transcript should be compact, searchable, and easy to quote into the summary.',
    type: 'observation',
    tags: ['auto-transcription', 'diarized'],
    telemetry_snapshot: null,
    created_at: '2026-04-27T15:52:11Z',
    updated_at: '2026-04-27T15:52:11Z',
  },
  {
    id: 'note_preview_6',
    session_id: 'preview',
    timestamp: '2026-04-27T15:53:10Z',
    speaker: 'Speaker 1',
    content: 'Next step is to connect this editor to a real structured note document in the backend.',
    type: 'observation',
    tags: ['auto-transcription', 'diarized'],
    telemetry_snapshot: null,
    created_at: '2026-04-27T15:53:10Z',
    updated_at: '2026-04-27T15:53:10Z',
  },
];

interface TranscriptBlock {
  id: string;
  speaker: string;
  timestamp: string;
  content: string;
  noteIds: string[];
}

interface AiDebugMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
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
  const diffMs = Math.max(0, end.getTime() - start.getTime());
  const minutes = Math.floor(diffMs / 60000);
  const seconds = Math.floor((diffMs % 60000) / 1000);
  return `${minutes}m ${seconds}s`;
}

function formatTime(dateStr: string): string {
  return new Date(dateStr).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function speakerColor(speaker: string, speakers: string[]): string {
  const idx = Math.max(0, speakers.indexOf(speaker));
  return SPEAKER_COLORS[idx % SPEAKER_COLORS.length];
}

function groupTranscript(notes: BackendNote[]): TranscriptBlock[] {
  const blocks: TranscriptBlock[] = [];
  const sorted = [...notes].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
  );

  for (const note of sorted) {
    const speaker = note.speaker || 'Unknown';
    const previous = blocks[blocks.length - 1];
    if (previous && previous.speaker === speaker) {
      previous.content = `${previous.content} ${note.content}`.trim();
      previous.noteIds.push(note.id);
    } else {
      blocks.push({
        id: note.id,
        speaker,
        timestamp: note.timestamp,
        content: note.content,
        noteIds: [note.id],
      });
    }
  }
  return blocks;
}

function buildInitialSummary(notes: BackendNote[]): string {
  if (notes.length === 0) {
    return [
      'Overview',
      '',
      'No transcript content is available yet.',
      '',
      'Key Points',
      '',
      '- ',
      '',
      'Decisions',
      '',
      '- ',
      '',
      'Action Items',
      '',
      '- ',
    ].join('\n');
  }

  const firstSpeaker = notes[0].speaker || 'Unknown';
  return [
    'Overview',
    '',
    `This session captured a short discussion led by ${firstSpeaker}. The raw transcript is preserved on the right, while this area is intended for the cleaned meeting summary.`,
    '',
    'Key Points',
    '',
    '- The session tested browser microphone transcription and structured note review.',
    '- The desired workflow separates polished notes from raw transcript text.',
    '',
    'Decisions',
    '',
    '- Use a document-style meeting summary as the primary editing surface.',
    '- Keep transcript material available as source context instead of displaying every note as a large row.',
    '',
    'Action Items',
    '',
    '- Connect this editor to a persistent structured-note backend model.',
    '- Add quote-from-transcript interactions after the layout is approved.',
  ].join('\n');
}

export default function SessionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const workspaceRef = useRef<HTMLElement>(null);
  const sidebarRef = useRef<HTMLElement>(null);

  const [session, setSession] = useState<BackendSession | null>(null);
  const [notes, setNotes] = useState<BackendNote[]>([]);
  const [title, setTitle] = useState('');
  const [summary, setSummary] = useState('');
  const [query, setQuery] = useState('');
  const [aiPrompt, setAiPrompt] = useState('');
  const [summaryWidth, setSummaryWidth] = useState(58);
  const [transcriptHeight, setTranscriptHeight] = useState(55);
  const [aiMessages, setAiMessages] = useState<AiDebugMessage[]>([
    {
      id: 'assistant_initial',
      role: 'assistant',
      content: 'Ask me to rewrite, shorten, extract action items, or check the summary against the transcript.',
    },
  ]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(true);

  useEffect(() => {
    if (!id) return;
    const sessionId = id;
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const isPreview = sessionId === 'preview';
        const [loadedSession, loadedNotes] = isPreview
          ? [DEMO_SESSION, DEMO_NOTES]
          : await Promise.all([getSession(sessionId), listNotes(sessionId)]);

        if (cancelled) return;
        setSession(loadedSession);
        setNotes(loadedNotes);
        setTitle(`${loadedSession.name} Meeting Summary`);
        setSummary(buildInitialSummary(loadedNotes));
        setSaved(true);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load session');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [id]);

  const speakers = useMemo(
    () => [...new Set(notes.map((note) => note.speaker || 'Unknown'))],
    [notes],
  );

  const transcriptBlocks = useMemo(() => groupTranscript(notes), [notes]);
  const filteredTranscript = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return transcriptBlocks;
    return transcriptBlocks.filter(
      (block) =>
        block.content.toLowerCase().includes(normalized) ||
        block.speaker.toLowerCase().includes(normalized),
    );
  }, [query, transcriptBlocks]);

  const handleTitleChange = (value: string) => {
    setTitle(value);
    setSaved(false);
  };

  const handleSummaryChange = (value: string) => {
    setSummary(value);
    setSaved(false);
  };

  const handleMarkSaved = () => {
    setSaved(true);
  };

  const startColumnResize = (event: React.MouseEvent<HTMLDivElement>) => {
    event.preventDefault();

    const handleMove = (moveEvent: MouseEvent) => {
      const rect = workspaceRef.current?.getBoundingClientRect();
      if (!rect) return;
      const next = ((moveEvent.clientX - rect.left) / rect.width) * 100;
      setSummaryWidth(Math.min(78, Math.max(42, next)));
    };

    const stop = () => {
      window.removeEventListener('mousemove', handleMove);
      window.removeEventListener('mouseup', stop);
    };

    window.addEventListener('mousemove', handleMove);
    window.addEventListener('mouseup', stop);
  };

  const startSidebarResize = (event: React.MouseEvent<HTMLDivElement>) => {
    event.preventDefault();

    const handleMove = (moveEvent: MouseEvent) => {
      const rect = sidebarRef.current?.getBoundingClientRect();
      if (!rect) return;
      const next = ((moveEvent.clientY - rect.top) / rect.height) * 100;
      setTranscriptHeight(Math.min(75, Math.max(35, next)));
    };

    const stop = () => {
      window.removeEventListener('mousemove', handleMove);
      window.removeEventListener('mouseup', stop);
    };

    window.addEventListener('mousemove', handleMove);
    window.addEventListener('mouseup', stop);
  };

  const handleAiPromptSubmit = () => {
    const prompt = aiPrompt.trim();
    if (!prompt) return;

    setAiMessages((prev) => [
      ...prev,
      {
        id: `user_${Date.now()}`,
        role: 'user',
        content: prompt,
      },
      {
        id: `assistant_${Date.now()}`,
        role: 'assistant',
        content:
          'Debug preview: this will call the summary assistant endpoint later. For now, use this box to test prompt flow and layout.',
      },
    ]);
    setAiPrompt('');
  };

  const handleExportMarkdown = useCallback(async () => {
    if (!id) return;
    if (id === 'preview') {
      const text = `# ${title}\n\n${summary}\n\n## Transcript\n\n${transcriptBlocks
        .map((block) => `### ${formatTime(block.timestamp)} ${block.speaker}\n\n${block.content}`)
        .join('\n\n')}`;
      const blob = new Blob([text], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'structured-note-preview.md';
      a.click();
      URL.revokeObjectURL(url);
      return;
    }

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
  }, [id, session?.name, summary, title, transcriptBlocks]);

  if (loading) {
    return (
      <div className="flex h-[calc(100vh-3.5rem)] flex-col items-center justify-center text-text-muted">
        <Loader2 className="mb-4 h-8 w-8 animate-spin text-accent-cyan" />
        <p className="text-sm">Loading session...</p>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="flex h-[calc(100vh-3.5rem)] flex-col items-center justify-center text-text-muted">
        <MessageSquareText className="mb-4 h-16 w-16 opacity-20" />
        <p className="mb-2 text-base font-medium">{error || 'Session not found'}</p>
        <button
          onClick={() => navigate('/history')}
          className="flex items-center gap-2 text-sm text-accent-cyan hover:underline"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Structured Notes
        </button>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col overflow-hidden animate-fade-in">
      <header className="shrink-0 border-b border-space-border/70 bg-space-black px-6 py-4">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <button
              onClick={() => navigate('/history')}
              className="mb-3 flex items-center gap-1.5 text-xs text-text-muted transition-colors hover:text-text-primary"
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </button>
            <input
              value={title}
              onChange={(event) => handleTitleChange(event.target.value)}
              className="w-full border-0 bg-transparent text-2xl font-medium leading-tight text-text-primary outline-none placeholder:text-text-muted"
              placeholder="Untitled meeting summary"
            />
            <p className="mt-2 text-xs text-text-muted">
              {session.name} · {formatDate(session.started_at)} · {formatDuration(session.started_at, session.ended_at)}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <div
              className={`flex items-center gap-1.5 px-2 py-1 text-xs ${
                saved
                  ? 'text-accent-green'
                  : 'text-accent-amber'
              }`}
            >
              {saved ? <Check className="h-3.5 w-3.5" /> : <Pencil className="h-3.5 w-3.5" />}
              {saved ? 'Saved' : 'Unsaved'}
            </div>
            <button
              onClick={handleMarkSaved}
              className="rounded-md px-3 py-1.5 text-sm text-text-secondary transition-colors hover:bg-space-card hover:text-text-primary"
            >
              Save
            </button>
            <button
              onClick={handleExportMarkdown}
              className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-text-secondary transition-colors hover:bg-space-card hover:text-text-primary"
            >
              <Download className="h-4 w-4" />
              Export
            </button>
          </div>
        </div>
      </header>

      <main
        ref={workspaceRef}
        className="grid min-h-0 flex-1"
        style={{ gridTemplateColumns: `${summaryWidth}% 6px minmax(190px, 1fr)` }}
      >
        <section className="min-h-0 overflow-y-scroll bg-space-black px-6 py-7">
          <div className="mx-auto max-w-4xl">
            <label className="mb-5 block text-[11px] font-medium uppercase tracking-wider text-text-muted">
              Meeting Summary
            </label>

            <textarea
              value={summary}
              onChange={(event) => handleSummaryChange(event.target.value)}
              spellCheck
              className="min-h-[calc(100vh-18rem)] w-full resize-none border-0 bg-transparent text-[15px] leading-8 text-text-primary outline-none placeholder:text-text-muted"
              placeholder="Write the meeting summary here..."
            />
          </div>
        </section>

        <div
          onMouseDown={startColumnResize}
          className="cursor-col-resize border-x border-space-border/60 bg-space-black transition-colors hover:bg-accent-cyan/20"
          title="Drag to resize"
        />

        <aside
          ref={sidebarRef}
          className="min-h-0 overflow-y-scroll bg-space-dark/40"
          style={{ scrollbarGutter: 'stable' }}
        >
          <div className="shrink-0 border-b border-space-border/60 px-5 py-4">
            <div className="mb-4">
              <div>
                <h2 className="text-sm font-medium text-text-primary">Transcript</h2>
                <p className="mt-1 text-xs text-text-muted">
                  {notes.length} notes · {speakers.length} speakers
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 border-b border-space-border/70 pb-2">
              <Search className="h-4 w-4 text-text-muted" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search transcript..."
                className="min-w-0 flex-1 bg-transparent text-sm text-text-primary outline-none placeholder:text-text-muted"
              />
            </div>
          </div>

          <div
            className="overflow-y-scroll px-5 py-5"
            style={{
              height: `${transcriptHeight}%`,
              minHeight: 160,
              scrollbarGutter: 'stable',
            }}
          >
            {filteredTranscript.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center text-center text-text-muted">
                <MessageSquareText className="mb-3 h-10 w-10 opacity-20" />
                <p className="text-sm">No transcript matches your search</p>
              </div>
            ) : (
              <div className="space-y-6">
                {filteredTranscript.map((block) => {
                  const color = speakerColor(block.speaker, speakers);
                  return (
                    <article key={block.id} className="group">
                      <div className="mb-2 flex items-center gap-2">
                        <span
                          className="text-xs font-medium"
                          style={{
                            color,
                          }}
                        >
                          {block.speaker}
                        </span>
                        <span className="text-[11px] text-text-muted">
                          {formatTime(block.timestamp)}
                        </span>
                      </div>
                      <p className="text-sm leading-6 text-text-secondary transition-colors group-hover:text-text-primary">
                        {block.content}
                      </p>
                    </article>
                  );
                })}
              </div>
            )}
          </div>

          <div
            onMouseDown={startSidebarResize}
            className="h-1.5 cursor-row-resize border-y border-space-border/60 bg-space-black transition-colors hover:bg-accent-cyan/20"
            title="Drag to resize"
          />

          <div
            className="flex min-h-[220px] flex-col overflow-y-scroll px-5 py-4"
            style={{
              height: `${100 - transcriptHeight}%`,
              scrollbarGutter: 'stable',
            }}
          >
            <div className="mb-3">
              <h2 className="text-sm font-medium text-text-primary">AI Summary Debug</h2>
              <p className="mt-1 text-xs text-text-muted">
                Test prompts before wiring the summary endpoint
              </p>
            </div>

            <div className="min-h-0 flex-1 space-y-3 overflow-y-scroll pr-1" style={{ scrollbarGutter: 'stable' }}>
              {aiMessages.map((message) => (
                <div
                  key={message.id}
                  className={
                    message.role === 'user'
                      ? 'ml-5 rounded-md bg-space-card/70 px-3 py-2 text-sm leading-5 text-text-primary'
                      : 'mr-5 text-sm leading-5 text-text-secondary'
                  }
                >
                  {message.content}
                </div>
              ))}
            </div>

            <div className="mt-3 flex items-end gap-2 border-t border-space-border/60 pt-3">
              <textarea
                value={aiPrompt}
                onChange={(event) => setAiPrompt(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault();
                    handleAiPromptSubmit();
                  }
                }}
                placeholder="Ask AI to improve the summary..."
                rows={2}
                className="min-h-10 flex-1 resize-none bg-transparent text-sm leading-5 text-text-primary outline-none placeholder:text-text-muted"
              />
              <button
                onClick={handleAiPromptSubmit}
                disabled={!aiPrompt.trim()}
                className="rounded-md p-2 text-text-muted transition-colors hover:bg-space-card hover:text-text-primary disabled:opacity-30"
                aria-label="Send AI prompt"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        </aside>
      </main>
    </div>
  );
}
