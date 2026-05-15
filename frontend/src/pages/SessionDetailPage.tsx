import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ReactMarkdown, { defaultUrlTransform } from 'react-markdown';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Activity,
  ArrowLeft,
  ChevronDown,
  ChevronRight,
  Check,
  FileCode2,
  FileJson,
  FileText,
  Download,
  Mic,
  Pause,
  Pencil,
  Play,
  Loader2,
  MessageSquareText,
  RotateCcw,
  Save,
  Send,
  Sparkles,
  Square,
  X,
} from 'lucide-react';
import {
  askTelemetryQuestion,
  autoUpdateStructureNoteTestSummary,
  chatWithSummaryAssistant,
  getSession,
  getStructureNote,
  listNotes,
  updateStructureNoteTestSummary,
} from '../services/api';
import type { BackendSession, TelemetryAskResponse } from '../services/api';
import { connectSessionWs } from '../services/sessionWs';
import {
  DEFAULT_SUMMARY_MODEL,
  SUMMARY_MODEL_OPTIONS,
  getSummaryModelLabel,
} from '../config/summaryModels';
import { useRecording } from '../contexts/RecordingContext';
import { useStore } from '../store/useStore';
import type { BackendNote, StructureNoteDetailParagraph, StructureNoteDocument } from '../types';

const MAX_PASTED_IMAGE_BYTES = 5 * 1024 * 1024;

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

const DEMO_STRUCTURE_NOTE: StructureNoteDocument = {
  schema_version: '0.1',
  session_id: 'preview',
  updated_at: '2026-04-27T15:53:35+00:00',
  telemetry_time_format: 'ISO 8601 with timezone (e.g. 2026-05-07T12:01:16+00:00)',
  test_summary: {
    status: 'ready',
    generated_at: '2026-04-27T15:53:40+00:00',
    content_markdown:
      'Dry run completed: microphone capture, transcript grouping, and structure note layout validated.',
  },
  anomalies: [
    {
      id: 'anom_demo',
      recorded_at: '2026-04-27T15:50:00+00:00',
      user_utterance_raw: '幫我記下來，右後輪有異音',
      title: '右後輪異音',
      description: '使用者口述異常，待後續確認。',
      severity: 'med',
    },
  ],
  detail_notes: {
    paragraphs: [
      {
        id: 'para_demo_1',
        updated_at: '2026-04-27T15:49:00+00:00',
        time_anchor: '2026-04-27T15:49:00+00:00',
        bullet_markdown: '• 2026-04-27T15:49:00+00:00 完成麥克風與轉寫路徑測試',
        source_transcript_excerpt: 'Hi everyone, my name is Ryan...',
      },
      {
        id: 'para_demo_2',
        updated_at: '2026-04-27T15:52:00+00:00',
        time_anchor: '2026-04-27T15:52:00+00:00',
        bullet_markdown: '• 2026-04-27T15:52:00+00:00 討論 structured note 與逐字稿分離顯示',
        source_transcript_excerpt: 'We should summarize action items...',
      },
    ],
  },
};

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

type ExportFormat = 'markdown' | 'html' | 'json';

interface SpeechRecognitionResultLike {
  readonly isFinal: boolean;
  readonly length: number;
  [index: number]: { transcript: string };
}

interface SpeechRecognitionEventLike extends Event {
  readonly resultIndex: number;
  readonly results: {
    readonly length: number;
    [index: number]: SpeechRecognitionResultLike;
  };
}

type BrowserSpeechRecognition = EventTarget & {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: Event & { error?: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};

type SpeechRecognitionWindow = Window & {
  SpeechRecognition?: new () => BrowserSpeechRecognition;
  webkitSpeechRecognition?: new () => BrowserSpeechRecognition;
};

const SUMMARY_MODEL_STORAGE_KEY = 'astra.summary.model';

function autoUpdateCursorStorageKey(sessionId: string): string {
  return `astra.summary.autoUpdateCursor.${sessionId}`;
}

function stripLiveTranscriptUpdates(markdown: string): string {
  return markdown
    .replace(/(^|\n)#{2,6}\s+Live transcript updates\s*\n[\s\S]*?(?=\n#{1,6}\s+\S|$)/gi, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
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

function formatJson(data: unknown): string {
  try {
    return JSON.stringify(data, null, 2);
  } catch {
    return String(data);
  }
}

function defaultTelemetryWindow(session: BackendSession | null): { t0: number; t1: number } {
  const anchor = session?.telemetry_mock_test1_path
    ? session.started_at
    : session?.ended_at || new Date().toISOString();
  const end = Math.floor(new Date(anchor).getTime() / 1000);
  const t1 = Number.isFinite(end) ? end : Math.floor(Date.now() / 1000);
  return { t0: t1 - 400, t1 };
}

/** Backend may still emit a duplicate heading; the page already shows "Test summary". */
function stripDuplicateSummaryHeading(markdown: string): string {
  return markdown.replace(/^\s*#{1,6}\s*test\s*summary\s*(\([^)]*\))?\s*\n+/i, '').trimStart();
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function detailNoteTimestamp(p: Pick<StructureNoteDetailParagraph, 'time_anchor' | 'updated_at'>): string {
  return (p.time_anchor || p.updated_at || '').trim();
}

/**
 * Single body line for UI: prefer raw excerpt; otherwise strip "• {ISO} —" from bullet_markdown.
 */
function detailNoteBodyText(p: StructureNoteDetailParagraph): string {
  const excerpt = (p.source_transcript_excerpt || '').trim();
  if (excerpt) return excerpt;
  const anchor = (p.time_anchor || '').trim();
  const bullet = (p.bullet_markdown || '').trim();
  if (anchor && bullet) {
    const prefixRe = new RegExp(
      `^\\s*[•\\-*]\\s*${escapeRegExp(anchor)}\\s*(?:[—:]\\s*|\\s+-\\s+)?`,
      'u',
    );
    const stripped = bullet.replace(prefixRe, '').trim();
    if (stripped) return stripped;
  }
  return bullet
    .replace(/^\s*[•*-]\s*/, '')
    .replace(
      /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})\s*(?:[—:]\s*)?/i,
      '',
    )
    .trim();
}

const STRUCTURE_MD_BODY_CLASS =
  'structure-md text-[15px] leading-7 text-text-secondary [&_p]:mb-3 [&_p:last-child]:mb-0 [&_ul]:my-2 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:my-2 [&_ol]:list-decimal [&_ol]:pl-5 [&_strong]:font-semibold [&_strong]:text-text-primary [&_a]:text-accent-cyan [&_a]:underline [&_code]:rounded [&_code]:bg-space-black/50 [&_code]:px-1 [&_h1]:mb-2 [&_h1]:text-lg [&_h1]:font-semibold [&_h1]:text-text-primary [&_h2]:mb-2 [&_h2]:text-base [&_h2]:font-semibold [&_h2]:text-text-primary [&_h3]:mb-1 [&_h3]:text-sm [&_h3]:font-semibold [&_h3]:text-text-primary [&_img]:my-3 [&_img]:max-h-[520px] [&_img]:max-w-full [&_img]:rounded-md [&_img]:border [&_img]:border-space-border/60';

function structureMarkdownUrlTransform(value: string, key: string): string {
  if (key === 'src' && /^data:image\/(?:png|jpe?g|gif|webp);base64,/i.test(value)) {
    return value;
  }
  return defaultUrlTransform(value);
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function sanitizeFileName(value: string): string {
  const cleaned = value
    .trim()
    .replace(/[\\/:*?"<>|]+/g, '-')
    .replace(/\s+/g, ' ')
    .slice(0, 80);
  return cleaned || 'structured-note';
}

function downloadTextFile(text: string, fileName: string, mimeType: string) {
  const blob = new Blob([text], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fileName;
  a.click();
  URL.revokeObjectURL(url);
}

function buildStructuredNoteMarkdown(
  title: string,
  session: BackendSession,
  sn: StructureNoteDocument,
  transcriptBlocks: TranscriptBlock[],
): string {
  const parts = [
    `# ${title}`,
    '',
    `**Session ID:** ${session.id}`,
    `**Started:** ${session.started_at}`,
    session.ended_at ? `**Ended:** ${session.ended_at}` : '',
    `**Status:** ${session.status}`,
    '',
    '## 1. Test summary',
    sn.test_summary.content_markdown || '(empty)',
    '',
    '## 2. Anomalies',
    sn.anomalies.length
      ? sn.anomalies
          .map((a) => `- **${a.title || 'Issue'}** (${a.recorded_at}): ${a.description}`)
          .join('\n')
      : 'No anomaly entries.',
    '',
    '## 3. Detail notes',
    sn.detail_notes.paragraphs.length
      ? sn.detail_notes.paragraphs
          .map((p) => {
            const ts = detailNoteTimestamp(p);
            const body = detailNoteBodyText(p) || '(empty)';
            return `### ${ts}\n\n${body}`;
          })
          .join('\n\n')
      : 'No detail notes.',
    '',
    '## Transcript',
    transcriptBlocks.length
      ? transcriptBlocks
          .map((block) => `### ${formatTime(block.timestamp)} ${block.speaker}\n\n${block.content}`)
          .join('\n\n')
      : 'No transcript entries.',
  ];

  return parts.filter((part) => part !== '').join('\n\n');
}

async function renderMarkdownForExport(markdown: string): Promise<string> {
  const { renderToStaticMarkup } = await import('react-dom/server');
  return renderToStaticMarkup(
    <ReactMarkdown urlTransform={structureMarkdownUrlTransform}>
      {stripDuplicateSummaryHeading(markdown)}
    </ReactMarkdown>,
  );
}

async function buildStructuredNoteHtml(
  title: string,
  session: BackendSession,
  sn: StructureNoteDocument,
  transcriptBlocks: TranscriptBlock[],
): Promise<string> {
  const summaryHtml = await renderMarkdownForExport(sn.test_summary.content_markdown || '(empty)');
  const anomaliesHtml = sn.anomalies.length
    ? `<ol>${sn.anomalies
        .map(
          (a) =>
            `<li><strong>${escapeHtml(a.title || 'Issue')}</strong> <span class="muted">${escapeHtml(
              a.recorded_at,
            )}</span><p>${escapeHtml(a.description || '')}</p></li>`,
        )
        .join('')}</ol>`
    : '<p class="muted">No anomaly entries.</p>';
  const detailsHtml = sn.detail_notes.paragraphs.length
    ? sn.detail_notes.paragraphs
        .map(
          (p) =>
            `<article><h3>${escapeHtml(detailNoteTimestamp(p))}</h3><p>${escapeHtml(
              detailNoteBodyText(p) || '(empty)',
            )}</p></article>`,
        )
        .join('')
    : '<p class="muted">No detail notes.</p>';
  const transcriptHtml = transcriptBlocks.length
    ? transcriptBlocks
        .map(
          (block) =>
            `<article><h3>${escapeHtml(formatTime(block.timestamp))} ${escapeHtml(
              block.speaker,
            )}</h3><p>${escapeHtml(block.content)}</p></article>`,
        )
        .join('')
    : '<p class="muted">No transcript entries.</p>';

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${escapeHtml(title)}</title>
  <style>
    :root { color: #172033; background: #f6f8fb; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; padding: 40px; }
    main { max-width: 920px; margin: 0 auto; background: white; border: 1px solid #dce3ee; border-radius: 12px; padding: 40px; box-shadow: 0 24px 80px rgba(22, 34, 51, 0.08); }
    h1 { margin: 0 0 8px; font-size: 30px; line-height: 1.15; }
    h2 { margin-top: 36px; padding-top: 24px; border-top: 1px solid #e4e9f2; font-size: 18px; }
    h3 { margin: 18px 0 6px; font-size: 14px; color: #31415f; }
    p, li { line-height: 1.65; }
    img { display: block; max-width: 100%; max-height: 720px; margin: 16px 0; border: 1px solid #dce3ee; border-radius: 8px; }
    code { background: #eef3f8; padding: 2px 5px; border-radius: 4px; }
    article { break-inside: avoid; }
    .meta { margin: 0; color: #647086; font-size: 13px; }
    .muted { color: #647086; }
    @media print { body { padding: 0; background: white; } main { border: 0; box-shadow: none; border-radius: 0; } }
  </style>
</head>
<body>
  <main>
    <h1>${escapeHtml(title)}</h1>
    <p class="meta">Session ID: ${escapeHtml(session.id)} · Started: ${escapeHtml(session.started_at)} · Status: ${escapeHtml(session.status)}</p>
    <section>
      <h2>1. Test summary</h2>
      ${summaryHtml}
    </section>
    <section>
      <h2>2. Anomalies</h2>
      ${anomaliesHtml}
    </section>
    <section>
      <h2>3. Detail notes</h2>
      ${detailsHtml}
    </section>
    <section>
      <h2>Transcript</h2>
      ${transcriptHtml}
    </section>
  </main>
</body>
</html>`;
}

function imageFileToMarkdown(file: File, index: number): Promise<string> {
  if (file.size > MAX_PASTED_IMAGE_BYTES) {
    throw new Error('Pasted image is too large. Use an image under 5 MB.');
  }

  const alt = (file.name || `pasted-image-${index + 1}`)
    .replace(/\.[^.]+$/, '')
    .replace(/[[\]\n\r]/g, ' ')
    .trim() || `pasted-image-${index + 1}`;

  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(`![${alt}](${String(reader.result)})`);
    reader.onerror = () => reject(new Error('Could not read the pasted image.'));
    reader.readAsDataURL(file);
  });
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

export default function SessionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const {
    pauseRecording,
    resumeRecording,
    stopRecording,
    isRecording,
    isPaused,
  } = useRecording();
  const { backendSessionId } = useStore();
  const workspaceRef = useRef<HTMLElement>(null);
  const sidebarRef = useRef<HTMLElement>(null);
  const summaryTextareaRef = useRef<HTMLTextAreaElement>(null);
  const telemetryRecognitionRef = useRef<BrowserSpeechRecognition | null>(null);

  const [session, setSession] = useState<BackendSession | null>(null);
  const [notes, setNotes] = useState<BackendNote[]>([]);
  const [structureNote, setStructureNote] = useState<StructureNoteDocument | null>(null);
  const [title, setTitle] = useState('');
  const [aiPrompt, setAiPrompt] = useState('');
  const [telemetrySessionId, setTelemetrySessionId] = useState('');
  const [telemetryQuestion, setTelemetryQuestion] = useState('');
  const [telemetryResult, setTelemetryResult] = useState<TelemetryAskResponse | null>(null);
  const [telemetryError, setTelemetryError] = useState<string | null>(null);
  const [telemetryLoading, setTelemetryLoading] = useState(false);
  const [telemetryVoiceListening, setTelemetryVoiceListening] = useState(false);
  const [selectedSummaryModel, setSelectedSummaryModel] = useState(() => {
    if (typeof window === 'undefined') return DEFAULT_SUMMARY_MODEL;
    return window.localStorage.getItem(SUMMARY_MODEL_STORAGE_KEY) || DEFAULT_SUMMARY_MODEL;
  });
  const [pendingSummaryPreview, setPendingSummaryPreview] = useState<string | null>(null);
  const [lastAppliedSummaryBackup, setLastAppliedSummaryBackup] = useState<string | null>(null);
  const [isSummaryEditing, setIsSummaryEditing] = useState(false);
  const [summaryDraft, setSummaryDraft] = useState('');
  const [summaryEditError, setSummaryEditError] = useState<string | null>(null);
  const [summarySaveState, setSummarySaveState] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [lastAutoUpdateNoteCursor, setLastAutoUpdateNoteCursor] = useState<string | null>(null);
  const [exportMenuOpen, setExportMenuOpen] = useState(false);
  const [aiBusy, setAiBusy] = useState(false);
  const [applyingPreview, setApplyingPreview] = useState(false);
  const [autoUpdatingSummary, setAutoUpdatingSummary] = useState(false);
  const [savingSummaryEdit, setSavingSummaryEdit] = useState(false);
  const [revertingSummary, setRevertingSummary] = useState(false);
  const [summaryWidth, setSummaryWidth] = useState(58);
  const [transcriptHeight, setTranscriptHeight] = useState(55);
  const [aiMessages, setAiMessages] = useState<AiDebugMessage[]>([
    {
      id: 'assistant_initial',
      role: 'assistant',
      content:
        'Ask for a rewrite, shorter version, action-focused summary, or translation. Review the preview before applying it.',
    },
  ]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
        setPendingSummaryPreview(null);
        setLastAppliedSummaryBackup(null);
        setIsSummaryEditing(loadedSession.status === 'active');
        setSummaryEditError(null);
        setSummarySaveState('idle');
        const storedCursor =
          typeof window === 'undefined' || isPreview
            ? null
            : window.localStorage.getItem(autoUpdateCursorStorageKey(sessionId));
        setLastAutoUpdateNoteCursor(storedCursor);
        if (isPreview) {
          setStructureNote(DEMO_STRUCTURE_NOTE);
          setSummaryDraft(DEMO_STRUCTURE_NOTE.test_summary.content_markdown || '');
        } else {
          try {
            const sn = await getStructureNote(sessionId);
            if (!cancelled) {
              setStructureNote(sn);
              setSummaryDraft(sn.test_summary.content_markdown || '');
            }
          } catch {
            if (!cancelled) {
              setStructureNote(null);
              setSummaryDraft('');
            }
          }
        }
      } catch (err) {
        if (!cancelled) {
          const raw = err instanceof Error ? err.message : 'Failed to load session';
          const is404 = /\b404\b/.test(raw) || raw.toLowerCase().includes('not found');
          setError(
            is404
              ? 'Session not found (HTTP 404). The dev server stores data in memory — after a backend restart, open Home and start a new recording.'
              : raw,
          );
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

  useEffect(() => {
    if (!id || id === 'preview') return;
    const conn = connectSessionWs(id, {
      onMessage: (msg) => {
        if (msg.event === 'structure_note.updated') {
          getStructureNote(id)
            .then((sn) => {
              setStructureNote(sn);
              setSummaryDraft((draft) =>
                draft.trim() ? draft : sn.test_summary.content_markdown || '',
              );
            })
            .catch(() => {});
        } else if (msg.event === 'note.created') {
          const note = msg.data as BackendNote;
          setNotes((prev) =>
            prev.some((item) => item.id === note.id) ? prev : [...prev, note],
          );
        } else if (msg.event === 'note.updated') {
          const note = msg.data as BackendNote;
          setNotes((prev) => prev.map((item) => (item.id === note.id ? note : item)));
        } else if (msg.event === 'note.deleted') {
          const deleted = msg.data as { id?: string };
          setNotes((prev) => prev.filter((item) => item.id !== deleted.id));
        }
      },
    });
    return () => conn.close();
  }, [id]);

  useEffect(() => {
    if (session?.id && id !== 'preview') {
      setTelemetrySessionId(session.id);
    }
  }, [id, session?.id]);

  useEffect(() => {
    return () => {
      telemetryRecognitionRef.current?.stop();
      telemetryRecognitionRef.current = null;
    };
  }, []);

  const transcriptBlocks = useMemo(() => groupTranscript(notes), [notes]);
  const telemetryWindow = useMemo(() => defaultTelemetryWindow(session), [session]);
  const currentSummaryMarkdown = structureNote?.test_summary.content_markdown || '';
  const activeSummaryMarkdown = isSummaryEditing ? summaryDraft : currentSummaryMarkdown;
  const isActiveRecordingNote = Boolean(isRecording && backendSessionId && id === backendSessionId);

  const canEditSummary = Boolean(session) && !savingSummaryEdit;

  const replaceTestSummary = useCallback(
    async (contentMarkdown: string): Promise<StructureNoteDocument> => {
      if (!id) throw new Error('Missing session id');
      if (id === 'preview') {
        const next: StructureNoteDocument = {
          ...(structureNote ?? DEMO_STRUCTURE_NOTE),
          updated_at: new Date().toISOString(),
          test_summary: {
            ...(structureNote ?? DEMO_STRUCTURE_NOTE).test_summary,
            status: 'ready',
            generated_at: new Date().toISOString(),
            content_markdown: contentMarkdown,
            error: null,
          },
        };
        setStructureNote(next);
        return next;
      }
      const updated = await updateStructureNoteTestSummary(id, contentMarkdown);
      setStructureNote(updated);
      return updated;
    },
    [id, structureNote],
  );

  useEffect(() => {
    if (!isSummaryEditing) {
      setSummaryDraft(currentSummaryMarkdown);
    }
  }, [currentSummaryMarkdown, isSummaryEditing]);

  useEffect(() => {
    if (!isSummaryEditing || !id || autoUpdatingSummary) return;
    if (!summaryDraft.trim() || summaryDraft === currentSummaryMarkdown) return;

    let cancelled = false;
    const timeout = window.setTimeout(async () => {
      setSummarySaveState('saving');
      setSummaryEditError(null);
      try {
        await replaceTestSummary(summaryDraft);
        if (!cancelled) setSummarySaveState('saved');
      } catch (err) {
        if (!cancelled) {
          setSummarySaveState('error');
          setSummaryEditError(err instanceof Error ? err.message : 'Could not autosave the summary.');
        }
      }
    }, 900);

    return () => {
      cancelled = true;
      window.clearTimeout(timeout);
    };
  }, [
    autoUpdatingSummary,
    currentSummaryMarkdown,
    id,
    isSummaryEditing,
    replaceTestSummary,
    summaryDraft,
  ]);

  const handleTitleChange = (value: string) => {
    setTitle(value);
  };

  const handleSummaryModelChange = (value: string) => {
    setSelectedSummaryModel(value);
    window.localStorage.setItem(SUMMARY_MODEL_STORAGE_KEY, value);
  };

  const handleTelemetryAsk = useCallback(async () => {
    const question = telemetryQuestion.trim();
    if (!question || telemetryLoading) return;
    setTelemetryLoading(true);
    setTelemetryError(null);
    try {
      const result = await askTelemetryQuestion({
        question,
        session: telemetrySessionId.trim() || undefined,
        t0: telemetryWindow.t0,
        t1: telemetryWindow.t1,
        at: telemetryWindow.t1,
        severity: 'all',
        limit: 20,
      });
      setTelemetryResult(result);
      if (result.error) {
        setTelemetryError(result.error);
      }
    } catch (err) {
      setTelemetryError(err instanceof Error ? err.message : 'Telemetry query failed.');
    } finally {
      setTelemetryLoading(false);
    }
  }, [telemetryLoading, telemetryQuestion, telemetrySessionId, telemetryWindow.t0, telemetryWindow.t1]);

  const handleTelemetryVoiceInput = useCallback(() => {
    if (telemetryVoiceListening) {
      telemetryRecognitionRef.current?.stop();
      setTelemetryVoiceListening(false);
      return;
    }

    const SpeechRecognitionCtor =
      (window as SpeechRecognitionWindow).SpeechRecognition ??
      (window as SpeechRecognitionWindow).webkitSpeechRecognition;
    if (!SpeechRecognitionCtor) {
      setTelemetryError('Voice input is not supported in this browser.');
      return;
    }

    const recognition = new SpeechRecognitionCtor();
    recognition.lang = navigator.language || 'en-US';
    recognition.interimResults = true;
    recognition.continuous = false;
    recognition.onresult = (event) => {
      let transcript = '';
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        transcript += event.results[i]?.[0]?.transcript ?? '';
      }
      if (transcript.trim()) {
        setTelemetryQuestion(transcript.trim());
      }
    };
    recognition.onerror = (event) => {
      setTelemetryError(event.error ? `Voice input failed: ${event.error}` : 'Voice input failed.');
    };
    recognition.onend = () => {
      setTelemetryVoiceListening(false);
      telemetryRecognitionRef.current = null;
    };

    telemetryRecognitionRef.current = recognition;
    setTelemetryVoiceListening(true);
    setTelemetryError(null);
    try {
      recognition.start();
    } catch (err) {
      telemetryRecognitionRef.current = null;
      setTelemetryVoiceListening(false);
      setTelemetryError(err instanceof Error ? err.message : 'Voice input could not start.');
    }
  }, [telemetryVoiceListening]);

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

  const handleAiPromptSubmit = async () => {
    const prompt = aiPrompt.trim();
    if (!prompt || !id || aiBusy) return;

    const userMessage: AiDebugMessage = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: prompt,
    };

    setAiMessages((prev) => [
      ...prev,
      userMessage,
    ]);
    setAiPrompt('');
    setAiBusy(true);

    try {
      if (id === 'preview') {
        const draft = [
          stripDuplicateSummaryHeading(activeSummaryMarkdown) || 'Dry run completed.',
          '',
          `Requested change (${getSummaryModelLabel(selectedSummaryModel)}): ${prompt}`,
        ].join('\n');
        setPendingSummaryPreview(draft);
        setAiMessages((prev) => [
          ...prev,
          {
            id: `assistant_${Date.now()}`,
            role: 'assistant',
            content: 'I prepared a preview draft. Review it below, then apply or discard it.',
          },
        ]);
        return;
      }

      const result = await chatWithSummaryAssistant(id, {
        prompt,
        title,
        summary: activeSummaryMarkdown,
        manual_summary: activeSummaryMarkdown,
        model: selectedSummaryModel,
        messages: aiMessages.map((message) => ({
          role: message.role,
          content: message.content,
        })),
      });

      if (result.updated_summary) {
        setPendingSummaryPreview(result.updated_summary);
      }
      setAiMessages((prev) => [
        ...prev,
        {
          id: `assistant_${Date.now()}`,
          role: 'assistant',
          content: result.updated_summary
            ? `${result.message}\n\nPreview is ready. Apply it when it looks right.`
            : result.message,
        },
      ]);
    } catch (err) {
      setAiMessages((prev) => [
        ...prev,
        {
          id: `assistant_${Date.now()}`,
          role: 'assistant',
          content: err instanceof Error ? err.message : 'Summary assistant failed.',
        },
      ]);
    } finally {
      setAiBusy(false);
    }
  };

  const handleApplySummaryPreview = async () => {
    if (!pendingSummaryPreview || applyingPreview) return;
    setApplyingPreview(true);
    try {
      setLastAppliedSummaryBackup(currentSummaryMarkdown);
      await replaceTestSummary(pendingSummaryPreview);
      setPendingSummaryPreview(null);
      setAiMessages((prev) => [
        ...prev,
        {
          id: `assistant_${Date.now()}`,
          role: 'assistant',
          content: 'Applied the preview to the Test summary. You can revert to the previous version.',
        },
      ]);
    } catch (err) {
      setLastAppliedSummaryBackup(null);
      setAiMessages((prev) => [
        ...prev,
        {
          id: `assistant_${Date.now()}`,
          role: 'assistant',
          content: err instanceof Error ? err.message : 'Could not apply the preview.',
        },
      ]);
    } finally {
      setApplyingPreview(false);
    }
  };

  const handleStartSummaryEdit = () => {
    setSummaryDraft(currentSummaryMarkdown);
    setSummaryEditError(null);
    setSummarySaveState('idle');
    setIsSummaryEditing(true);
  };

  const handleCancelSummaryEdit = () => {
    setSummaryDraft(currentSummaryMarkdown);
    setSummaryEditError(null);
    setSummarySaveState('idle');
    setIsSummaryEditing(false);
  };

  const handleSummaryPaste = async (event: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const imageFiles = Array.from(event.clipboardData.files).filter((file) =>
      file.type.startsWith('image/'),
    );
    if (imageFiles.length === 0) return;

    event.preventDefault();
    setSummaryEditError(null);
    setSummarySaveState('idle');

    const textarea = event.currentTarget;
    const current = textarea.value;
    const selectionStart = textarea.selectionStart;
    const selectionEnd = textarea.selectionEnd;

    try {
      const markdownImages = await Promise.all(imageFiles.map(imageFileToMarkdown));
      const insertion = markdownImages.join('\n\n');
      const needsPrefix = selectionStart > 0 && !current.slice(0, selectionStart).endsWith('\n');
      const needsSuffix = selectionEnd < current.length && !current.slice(selectionEnd).startsWith('\n');
      const prefix = needsPrefix ? '\n\n' : '';
      const suffix = needsSuffix ? '\n\n' : '';
      const next =
        current.slice(0, selectionStart) +
        prefix +
        insertion +
        suffix +
        current.slice(selectionEnd);
      const cursorPosition = selectionStart + prefix.length + insertion.length;

      setSummaryDraft(next);
      requestAnimationFrame(() => {
        summaryTextareaRef.current?.focus();
        summaryTextareaRef.current?.setSelectionRange(cursorPosition, cursorPosition);
      });
    } catch (err) {
      setSummaryEditError(err instanceof Error ? err.message : 'Could not paste the image.');
    }
  };

  const handleSaveSummaryEdit = async () => {
    if (!canEditSummary) return;
    setSavingSummaryEdit(true);
    setSummaryEditError(null);
    setSummarySaveState('saving');
    try {
      setLastAppliedSummaryBackup(currentSummaryMarkdown);
      await replaceTestSummary(summaryDraft);
      setPendingSummaryPreview(null);
      setSummarySaveState('saved');
      setIsSummaryEditing(false);
      setAiMessages((prev) => [
        ...prev,
        {
          id: `assistant_${Date.now()}`,
          role: 'assistant',
          content: 'Saved your manual edit to the Test summary.',
        },
      ]);
    } catch (err) {
      setLastAppliedSummaryBackup(null);
      setSummarySaveState('error');
      setSummaryEditError(err instanceof Error ? err.message : 'Could not save the summary.');
    } finally {
      setSavingSummaryEdit(false);
    }
  };

  const handleAutoUpdateSummary = async () => {
    if (!id || autoUpdatingSummary) return;
    const manualSummary = isSummaryEditing ? summaryDraft : currentSummaryMarkdown;
    const isEndedSession = session?.status === 'ended';
    let processedNoteCount = 0;
    setAutoUpdatingSummary(true);
    setSummaryEditError(null);
    setSummarySaveState('saving');
    setLastAppliedSummaryBackup(manualSummary);

    try {
      if (id === 'preview') {
        const sortedNotes = [...notes].sort(
          (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
        );
        const cursorIndex =
          !isEndedSession && lastAutoUpdateNoteCursor
            ? sortedNotes.findIndex((note) => note.id === lastAutoUpdateNoteCursor)
            : -1;
        const notesToProcess = isEndedSession
          ? sortedNotes
          : cursorIndex >= 0
            ? sortedNotes.slice(cursorIndex + 1)
            : sortedNotes;
        const newTranscriptBlocks = groupTranscript(notesToProcess);
        const recentTranscript = newTranscriptBlocks
          .map((block) => `${block.speaker}: ${block.content}`)
          .join('\n');
        const merged =
          isEndedSession
            ? [
                stripLiveTranscriptUpdates(manualSummary),
                '## Organized session summary',
                'The session captured the recorded discussion and organized it into a final note summary.',
                recentTranscript ? `\nKey transcript context:\n${recentTranscript}` : '',
              ]
                .filter(Boolean)
                .join('\n\n')
            : recentTranscript
              ? [
                  manualSummary.trim() || 'Live summary draft.',
                  '',
                  '## Live transcript updates',
                  recentTranscript,
                ].join('\n')
              : manualSummary.trim() || currentSummaryMarkdown || 'No summary content is available yet.';
        await replaceTestSummary(merged);
        setSummaryDraft(merged);
        const nextCursor = sortedNotes.at(-1)?.id ?? lastAutoUpdateNoteCursor;
        setLastAutoUpdateNoteCursor(nextCursor);
        processedNoteCount = notesToProcess.length;
      } else {
        const result = await autoUpdateStructureNoteTestSummary(
          id,
          manualSummary,
          lastAutoUpdateNoteCursor,
        );
        const updated = result.document;
        const merged = updated.test_summary.content_markdown;
        setStructureNote(updated);
        setSummaryDraft(merged);
        const nextCursor = result.last_note_id ?? lastAutoUpdateNoteCursor;
        setLastAutoUpdateNoteCursor(nextCursor);
        if (nextCursor) {
          window.localStorage.setItem(autoUpdateCursorStorageKey(id), nextCursor);
        }
        processedNoteCount = result.processed_note_count;
      }
      setPendingSummaryPreview(null);
      setIsSummaryEditing(false);
      setSummarySaveState('saved');
      setAiMessages((prev) => [
        ...prev,
        {
          id: `assistant_${Date.now()}`,
          role: 'assistant',
          content:
            isEndedSession
              ? 'Generated the organized Test summary from the completed session.'
              : processedNoteCount > 0
              ? `Auto-updated the Test summary with ${processedNoteCount} new transcript item(s).`
              : 'No new transcript since the last Auto update. The summary was left unchanged.',
        },
      ]);
    } catch (err) {
      setSummarySaveState('error');
      setSummaryEditError(err instanceof Error ? err.message : 'Could not auto update the summary.');
    } finally {
      setAutoUpdatingSummary(false);
    }
  };

  const handleRevertSummary = async () => {
    if (lastAppliedSummaryBackup === null || revertingSummary) return;
    setRevertingSummary(true);
    try {
      await replaceTestSummary(lastAppliedSummaryBackup);
      setLastAppliedSummaryBackup(null);
      setPendingSummaryPreview(null);
      setAiMessages((prev) => [
        ...prev,
        {
          id: `assistant_${Date.now()}`,
          role: 'assistant',
          content: 'Reverted the Test summary to the previous version.',
        },
      ]);
    } catch (err) {
      setAiMessages((prev) => [
        ...prev,
        {
          id: `assistant_${Date.now()}`,
          role: 'assistant',
          content: err instanceof Error ? err.message : 'Could not revert the summary.',
        },
      ]);
    } finally {
      setRevertingSummary(false);
    }
  };

  const handleExport = useCallback(
    async (format: ExportFormat) => {
      if (!id || !session) return;
      const sourceNote = id === 'preview' ? structureNote ?? DEMO_STRUCTURE_NOTE : structureNote;
      if (!sourceNote) return;
      const sn: StructureNoteDocument = {
        ...sourceNote,
        test_summary: {
          ...sourceNote.test_summary,
          content_markdown:
            activeSummaryMarkdown || sourceNote.test_summary.content_markdown || '',
        },
      };
      const baseName = sanitizeFileName(`${session.name || title}-structured-note`);

      try {
        if (format === 'html') {
          downloadTextFile(
            await buildStructuredNoteHtml(title, session, sn, transcriptBlocks),
            `${baseName}.html`,
            'text/html;charset=utf-8',
          );
        } else if (format === 'json') {
          downloadTextFile(
            JSON.stringify(
              {
                exported_at: new Date().toISOString(),
                title,
                session,
                structure_note: sn,
                transcript: transcriptBlocks,
                notes,
              },
              null,
              2,
            ),
            `${baseName}.json`,
            'application/json;charset=utf-8',
          );
        } else {
          downloadTextFile(
            buildStructuredNoteMarkdown(title, session, sn, transcriptBlocks),
            `${baseName}.md`,
            'text/markdown;charset=utf-8',
          );
        }
      } catch (err) {
        console.error('Export failed:', err);
      } finally {
        setExportMenuOpen(false);
      }
    },
    [activeSummaryMarkdown, id, notes, session, structureNote, title, transcriptBlocks],
  );

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
            {structureNote && (
              <span className="hidden text-xs text-text-muted sm:inline">
                Structure note updated: {structureNote.updated_at}
              </span>
            )}
            {isActiveRecordingNote && (
              <div className="flex items-center gap-2 rounded-lg border border-space-border bg-space-card px-1.5 py-1">
                {isPaused ? (
                  <button
                    type="button"
                    onClick={resumeRecording}
                    className="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm font-medium text-accent-green transition-colors hover:bg-accent-green/10"
                  >
                    <Play className="h-4 w-4" />
                    Resume
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={pauseRecording}
                    className="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm font-medium text-accent-amber transition-colors hover:bg-accent-amber/10"
                  >
                    <Pause className="h-4 w-4" />
                    Pause
                  </button>
                )}
                <button
                  type="button"
                  onClick={stopRecording}
                  className="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm font-medium text-accent-red transition-colors hover:bg-accent-red/10"
                >
                  <Square className="h-4 w-4" />
                  Stop
                </button>
              </div>
            )}
            <button
              type="button"
              onClick={() => navigate('/session')}
              className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-text-secondary transition-colors hover:bg-space-card hover:text-text-primary"
            >
              <Mic className="h-4 w-4" />
              Active Session
            </button>
            <div
              className="relative"
              onBlur={(event) => {
                const nextFocus = event.relatedTarget;
                if (!(nextFocus instanceof Node) || !event.currentTarget.contains(nextFocus)) {
                  setExportMenuOpen(false);
                }
              }}
            >
              <button
                type="button"
                onClick={() => setExportMenuOpen((open) => !open)}
                className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-text-secondary transition-colors hover:bg-space-card hover:text-text-primary"
                aria-expanded={exportMenuOpen}
              >
                <Download className="h-4 w-4" />
                Export
                <ChevronDown className="h-3.5 w-3.5" />
              </button>
              {exportMenuOpen && (
                <div className="absolute right-0 top-full z-30 mt-2 w-52 overflow-hidden rounded-lg border border-space-border bg-space-panel py-1 shadow-xl shadow-black/30">
                  <button
                    type="button"
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => handleExport('html')}
                    className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-text-primary transition-colors hover:bg-space-card"
                  >
                    <FileCode2 className="h-4 w-4 text-accent-cyan" />
                    HTML with images
                  </button>
                  <button
                    type="button"
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => handleExport('markdown')}
                    className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-text-secondary transition-colors hover:bg-space-card hover:text-text-primary"
                  >
                    <FileText className="h-4 w-4 text-text-muted" />
                    Markdown
                  </button>
                  <button
                    type="button"
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => handleExport('json')}
                    className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-text-secondary transition-colors hover:bg-space-card hover:text-text-primary"
                  >
                    <FileJson className="h-4 w-4 text-text-muted" />
                    JSON data
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      <main
        ref={workspaceRef}
        className="grid min-h-0 flex-1"
        style={{ gridTemplateColumns: `${summaryWidth}% 6px minmax(190px, 1fr)` }}
      >
        <section className="min-h-0 overflow-y-scroll bg-space-black px-6 py-7">
          <div className="mx-auto max-w-4xl space-y-10 pb-16">
            <p className="text-[11px] font-medium uppercase tracking-wider text-text-muted">
              Structured note
            </p>

            <div>
              <div className="mb-2 flex items-center justify-between gap-3">
                <h2 className="text-sm font-semibold text-text-primary">1. Test summary</h2>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={handleAutoUpdateSummary}
                    disabled={autoUpdatingSummary}
                    className="flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-accent-cyan transition-colors hover:bg-accent-cyan/10 disabled:opacity-40"
                  >
                    {autoUpdatingSummary ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Sparkles className="h-3.5 w-3.5" />
                    )}
                    Auto update
                  </button>
                  {!isSummaryEditing && (
                    <button
                      type="button"
                      onClick={handleStartSummaryEdit}
                      className="flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-text-secondary transition-colors hover:bg-space-card hover:text-text-primary"
                    >
                      <Pencil className="h-3.5 w-3.5" />
                      {session.status === 'active' ? 'Live edit' : 'Edit'}
                    </button>
                  )}
                </div>
              </div>
              {isSummaryEditing ? (
                <div className="rounded-lg border border-accent-cyan/40 bg-space-card/30">
                  <textarea
                    ref={summaryTextareaRef}
                    value={summaryDraft}
                    onChange={(event) => {
                      setSummaryDraft(event.target.value);
                      setSummarySaveState('idle');
                    }}
                    onPaste={handleSummaryPaste}
                    placeholder={
                      session.status === 'active'
                        ? 'Write live notes while recording...'
                        : 'Write the Test summary in Markdown...'
                    }
                    className="min-h-[260px] w-full resize-y rounded-t-lg border-0 bg-transparent px-4 py-3 font-mono text-sm leading-6 text-text-primary outline-none placeholder:text-text-muted"
                  />
                  {summaryEditError && (
                    <p className="border-t border-red-500/30 px-4 py-2 text-xs text-red-200">
                      {summaryEditError}
                    </p>
                  )}
                  <div className="flex items-center justify-between gap-3 border-t border-space-border/60 px-4 py-3">
                    <p className="text-xs text-text-muted">
                      {autoUpdatingSummary
                        ? 'Updating from transcript...'
                        : summarySaveState === 'saving'
                        ? 'Autosaving...'
                        : summarySaveState === 'saved'
                          ? 'Saved'
                          : summarySaveState === 'error'
                            ? 'Autosave failed'
                            : session.status === 'active'
                              ? 'Autosaves while you type'
                              : 'Markdown and pasted images are supported'}
                    </p>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={handleCancelSummaryEdit}
                        disabled={savingSummaryEdit}
                        className="rounded-md px-3 py-1.5 text-sm text-text-secondary transition-colors hover:bg-space-card hover:text-text-primary disabled:opacity-40"
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        onClick={handleSaveSummaryEdit}
                        disabled={!canEditSummary}
                        className="flex items-center gap-1.5 rounded-md bg-accent-cyan px-3 py-1.5 text-sm font-medium text-space-black transition-opacity hover:opacity-90 disabled:opacity-40"
                      >
                        {savingSummaryEdit ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Save className="h-4 w-4" />
                        )}
                        Save
                      </button>
                    </div>
                  </div>
                </div>
              ) : structureNote?.test_summary.status === 'ready' ? (
                <div
                  className={`rounded-lg border border-space-border/60 bg-space-card/30 px-4 py-3 ${STRUCTURE_MD_BODY_CLASS}`}
                >
                  <ReactMarkdown urlTransform={structureMarkdownUrlTransform}>
                    {stripDuplicateSummaryHeading(
                      structureNote.test_summary.content_markdown || '',
                    )}
                  </ReactMarkdown>
                </div>
              ) : session.status !== 'ended' ? (
                <div className="rounded-lg border border-space-border/60 bg-space-card/40 px-4 py-3 text-sm text-text-muted">
                  Recording still active. Use Live edit to write the summary as the session runs.
                </div>
              ) : structureNote?.test_summary.status === 'generating' ? (
                <div className="flex items-center gap-2 rounded-lg border border-space-border/60 bg-space-card/40 px-4 py-3 text-sm text-text-muted">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Generating test summary…
                </div>
              ) : structureNote?.test_summary.status === 'error' ? (
                <div className="rounded-lg border border-red-500/40 bg-red-950/20 px-4 py-3 text-sm text-red-200">
                  {structureNote.test_summary.error || 'Generation failed'}
                </div>
              ) : (
                <div className="rounded-lg border border-space-border/60 bg-space-card/40 px-4 py-3 text-sm text-text-muted">
                  Waiting for summary — if you just ended the session, it should appear shortly.
                </div>
              )}
            </div>

            <div>
              <h2 className="mb-2 text-sm font-semibold text-text-primary">2. Anomalies</h2>
              {!structureNote || structureNote.anomalies.length === 0 ? (
                <p className="text-sm text-text-muted">No anomaly entries yet.</p>
              ) : (
                <ol className="ml-5 list-decimal space-y-4 pl-1 text-[15px] leading-snug text-text-secondary marker:font-medium marker:text-text-primary">
                  {structureNote.anomalies.map((a) => {
                    const desc = (a.description || '').trim();
                    const title = (a.title || '').trim();
                    const showSecondLine = desc.length > 0 && desc !== title;
                    return (
                      <li key={a.id} className="pl-1">
                        <div className="text-text-primary">
                          <span className="font-medium">{title || 'Issue'}</span>
                          <span className="text-text-muted">, time: {a.recorded_at}</span>
                        </div>
                        {showSecondLine ? (
                          <div className="mt-1 whitespace-pre-wrap text-sm text-text-secondary">
                            {desc}
                          </div>
                        ) : null}
                      </li>
                    );
                  })}
                </ol>
              )}
            </div>

            <div>
              <h2 className="mb-2 text-sm font-semibold text-text-primary">3. Detail notes</h2>
              {!structureNote || structureNote.detail_notes.paragraphs.length === 0 ? (
                <p className="text-sm text-text-muted">
                  No paragraphs yet — they accumulate when STT chunks are processed.
                </p>
              ) : (
                <ul className="space-y-4 text-[15px] leading-7 text-text-secondary">
                  {structureNote.detail_notes.paragraphs.map((p) => (
                    <li key={p.id} className="rounded-lg border border-space-border/50 bg-space-card/20 px-3 py-2">
                      <time
                        className="mb-1.5 block text-xs tabular-nums tracking-tight text-text-muted"
                        dateTime={p.time_anchor || undefined}
                      >
                        {detailNoteTimestamp(p)}
                      </time>
                      <div className="whitespace-pre-wrap text-[15px] leading-7 text-text-primary">
                        {detailNoteBodyText(p)}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
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
            <div className="mb-3 flex items-start justify-between gap-3">
              <div>
                <h2 className="flex items-center gap-1.5 text-sm font-medium text-text-primary">
                  <Activity className="h-4 w-4 text-accent-cyan" />
                  Telemetry data query
                </h2>
                <p className="mt-1 text-xs text-text-muted">
                  {telemetrySessionId || 'No session tag'} · {telemetryWindow.t0} to {telemetryWindow.t1}
                </p>
              </div>
            </div>

            <label className="mb-3 block">
              <span className="mb-1 block text-[10px] font-medium uppercase tracking-wider text-text-muted">
                Influx session
              </span>
              <input
                value={telemetrySessionId}
                onChange={(event) => setTelemetrySessionId(event.target.value)}
                className="w-full rounded-md border border-space-border/70 bg-space-black px-2.5 py-2 font-mono text-xs text-text-primary outline-none transition-colors placeholder:text-text-muted focus:border-accent-cyan/50"
                placeholder="session_id"
              />
            </label>

            <div className="rounded-lg border border-space-border/70 bg-space-black/40">
              <textarea
                value={telemetryQuestion}
                onChange={(event) => setTelemetryQuestion(event.target.value)}
                onKeyDown={(event) => {
                  if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
                    void handleTelemetryAsk();
                  }
                }}
                placeholder="Ask telemetry..."
                className="min-h-[76px] w-full resize-none rounded-t-lg border-0 bg-transparent px-3 py-2 text-sm leading-5 text-text-primary outline-none placeholder:text-text-muted"
              />
              <div className="flex items-center justify-between gap-2 border-t border-space-border/60 px-2.5 py-2">
                <button
                  type="button"
                  onClick={handleTelemetryVoiceInput}
                  className={`flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs transition-colors ${
                    telemetryVoiceListening
                      ? 'bg-accent-red/10 text-accent-red'
                      : 'text-text-secondary hover:bg-space-card hover:text-text-primary'
                  }`}
                >
                  <Mic className="h-3.5 w-3.5" />
                  {telemetryVoiceListening ? 'Listening' : 'Voice'}
                </button>
                <button
                  type="button"
                  onClick={() => void handleTelemetryAsk()}
                  disabled={telemetryLoading || !telemetryQuestion.trim()}
                  className="flex items-center gap-1.5 rounded-md bg-accent-cyan px-3 py-1.5 text-xs font-medium text-space-black transition-opacity hover:opacity-90 disabled:opacity-40"
                >
                  {telemetryLoading ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <ChevronRight className="h-3.5 w-3.5" />
                  )}
                  Query
                </button>
              </div>
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
            {telemetryLoading ? (
              <div className="flex h-full flex-col items-center justify-center text-center text-text-muted">
                <Loader2 className="mb-3 h-8 w-8 animate-spin text-accent-cyan" />
                <p className="text-sm">Querying telemetry...</p>
              </div>
            ) : telemetryResult ? (
              <div className="space-y-4">
                <section>
                  <h3 className="mb-1 text-xs font-medium uppercase tracking-wider text-text-muted">
                    Answer
                  </h3>
                  <p className="text-sm leading-6 text-text-primary">{telemetryResult.answer}</p>
                  {(telemetryError || telemetryResult.error) && (
                    <p className="mt-2 rounded-md border border-red-500/30 bg-red-950/20 px-3 py-2 text-xs text-red-200">
                      {telemetryError || telemetryResult.error}
                    </p>
                  )}
                </section>
                <section>
                  <h3 className="mb-1 text-xs font-medium uppercase tracking-wider text-text-muted">
                    Plan
                  </h3>
                  <pre className="max-h-32 overflow-auto rounded-md border border-space-border/60 bg-space-black/50 p-2 text-[11px] leading-5 text-text-secondary">
                    {formatJson(telemetryResult.plan)}
                  </pre>
                </section>
                <section>
                  <h3 className="mb-1 text-xs font-medium uppercase tracking-wider text-text-muted">
                    Result
                  </h3>
                  <pre className="max-h-56 overflow-auto rounded-md border border-space-border/60 bg-space-black/50 p-2 text-[11px] leading-5 text-text-secondary">
                    {formatJson(telemetryResult.data)}
                  </pre>
                </section>
              </div>
            ) : (
              <div className="flex h-full flex-col items-center justify-center text-center text-text-muted">
                <Activity className="mb-3 h-10 w-10 opacity-20" />
                <p className="text-sm">Telemetry results will appear here</p>
                {telemetryError && (
                  <p className="mt-2 max-w-xs text-xs text-red-200">{telemetryError}</p>
                )}
              </div>
            )}
          </div>

          <div
            onMouseDown={startSidebarResize}
            className="h-1.5 cursor-row-resize border-y border-space-border/60 bg-space-black transition-colors hover:bg-accent-cyan/20"
            title="Resize telemetry query"
          />

          <div
            className="flex min-h-[220px] flex-col overflow-y-scroll px-5 py-4"
            style={{
              height: `${100 - transcriptHeight}%`,
              scrollbarGutter: 'stable',
            }}
          >
            <div className="mb-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="flex items-center gap-1.5 text-sm font-medium text-text-primary">
                    <Sparkles className="h-4 w-4 text-accent-cyan" />
                    Note AI
                  </h2>
                  <p className="mt-1 text-xs text-text-muted">Draft changes before applying</p>
                </div>
                <select
                  value={selectedSummaryModel}
                  onChange={(event) => handleSummaryModelChange(event.target.value)}
                  className="max-w-[150px] rounded-md border border-space-border/70 bg-space-black px-2 py-1 text-xs text-text-primary outline-none transition-colors hover:border-accent-cyan/50"
                  aria-label="Summary AI model"
                >
                  {SUMMARY_MODEL_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="min-h-0 flex-1 space-y-3 overflow-y-scroll pr-1" style={{ scrollbarGutter: 'stable' }}>
              {pendingSummaryPreview && (
                <section className="rounded-md border border-accent-cyan/40 bg-accent-cyan/5">
                  <div className="flex items-center justify-between gap-2 border-b border-accent-cyan/20 px-3 py-2">
                    <div>
                      <h3 className="text-xs font-medium text-text-primary">Preview</h3>
                      <p className="mt-0.5 text-[11px] text-text-muted">
                        Generated with {getSummaryModelLabel(selectedSummaryModel)}
                      </p>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => setPendingSummaryPreview(null)}
                        className="rounded-md p-1.5 text-text-muted transition-colors hover:bg-space-card hover:text-text-primary"
                        aria-label="Discard preview"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={handleApplySummaryPreview}
                        disabled={applyingPreview}
                        className="rounded-md p-1.5 text-accent-cyan transition-colors hover:bg-accent-cyan/10 disabled:opacity-40"
                        aria-label="Apply preview"
                      >
                        {applyingPreview ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <Check className="h-3.5 w-3.5" />
                        )}
                      </button>
                    </div>
                  </div>
                  <div className={`max-h-64 overflow-y-auto px-3 py-2 ${STRUCTURE_MD_BODY_CLASS}`}>
                    <ReactMarkdown urlTransform={structureMarkdownUrlTransform}>
                      {stripDuplicateSummaryHeading(pendingSummaryPreview)}
                    </ReactMarkdown>
                  </div>
                </section>
              )}

              {lastAppliedSummaryBackup !== null && (
                <section className="flex items-center justify-between gap-3 rounded-md border border-space-border/70 bg-space-card/30 px-3 py-2">
                  <div>
                    <p className="text-xs font-medium text-text-primary">Previous version saved</p>
                    <p className="mt-0.5 text-[11px] text-text-muted">
                      Revert will restore the summary from before your last apply.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={handleRevertSummary}
                    disabled={revertingSummary}
                    className="flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-text-secondary transition-colors hover:bg-space-card hover:text-text-primary disabled:opacity-40"
                  >
                    {revertingSummary ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <RotateCcw className="h-3.5 w-3.5" />
                    )}
                    Revert
                  </button>
                </section>
              )}

              {aiMessages.map((message) => (
                <div
                  key={message.id}
                  className={
                    message.role === 'user'
                      ? 'ml-5 rounded-md bg-space-card/70 px-3 py-2 text-sm leading-5 text-text-primary'
                      : 'mr-5 whitespace-pre-wrap text-sm leading-5 text-text-secondary'
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
                disabled={!aiPrompt.trim() || aiBusy}
                className="rounded-md p-2 text-text-muted transition-colors hover:bg-space-card hover:text-text-primary disabled:opacity-30"
                aria-label="Send AI prompt"
              >
                {aiBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </button>
            </div>
          </div>
        </aside>
      </main>
    </div>
  );
}
