import { useRef, useEffect, useMemo, useState } from 'react';
import {
  AudioLines,
  Loader2,
  Wifi,
  WifiOff,
  Clock,
  Users,
  ChevronDown,
  Pause,
  Timer,
  Pencil,
  Check,
  X,
  Plus,
  Trash2,
  UserRound,
} from 'lucide-react';
import { useStore } from '../../store/useStore';
import type { LiveTranscription, SpeakerProfile } from '../../store/useStore';
import { getSttModelLabel } from '../../config/sttModels';

const COLOR_SWATCHES = [
  '#00d4ff',
  '#00e676',
  '#b388ff',
  '#ffab00',
  '#ff5252',
  '#4dd0e1',
  '#64ffda',
  '#f06292',
];

const FALLBACK_SPEAKER: SpeakerProfile = {
  id: 'unknown',
  name: 'Unknown',
  color: '#8899aa',
};

function getSpeakerInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return 'SP';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
}

function getSpeakerById(speakers: SpeakerProfile[], speakerId: string): SpeakerProfile {
  return speakers.find((speaker) => speaker.id === speakerId) ?? FALLBACK_SPEAKER;
}

function getSpeakerUsage(transcriptions: LiveTranscription[]): Map<string, number> {
  const usage = new Map<string, number>();
  for (const entry of transcriptions) {
    usage.set(entry.speakerId, (usage.get(entry.speakerId) ?? 0) + 1);
  }
  return usage;
}

function formatRecordingDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0)
    return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

/* ─── Audio level visualizer bar ─── */
function AudioVisualizer({ level, isActive }: { level: number; isActive: boolean }) {
  const bars = 40;
  return (
    <div className="flex items-end gap-[2px] h-10">
      {Array.from({ length: bars }).map((_, i) => {
        const shimmer = ((i * 17) % 7) / 100;
        const barLevel = isActive
          ? Math.max(
              0.05,
              level * (0.4 + 0.6 * Math.sin((i / bars) * Math.PI)) +
                shimmer
            )
          : 0.05;
        return (
          <div
            key={i}
            className="w-[3px] rounded-full transition-all duration-75"
            style={{
              height: `${Math.max(3, barLevel * 40)}px`,
              backgroundColor: isActive
                ? `rgba(0, 212, 255, ${0.3 + barLevel * 0.7})`
                : 'rgba(85, 102, 119, 0.3)',
            }}
          />
        );
      })}
    </div>
  );
}

/* ─── Typewriter animation (word-by-word reveal) ─── */
// Animates a local "displayed" string toward `target`, revealing ONE WORD at a
// time at a fixed cadence. A single persistent interval runs for the lifetime
// of the row; new deltas (target updates) just update `targetRef`, and the
// interval keeps walking forward until it catches up.
//
// This deliberately ignores how fast deltas arrive from the backend: even if
// OpenAI bursts 10 tokens in 300 ms, the user still sees one word pop up every
// WORD_INTERVAL_MS, producing a smooth "words appearing as I speak" feel.
const WORD_INTERVAL_MS = 90;

function findNextWordBoundary(text: string, fromIndex: number): number {
  let i = fromIndex;
  while (i < text.length && /\s/.test(text[i])) i++;
  while (i < text.length && !/\s/.test(text[i])) i++;
  return i;
}

function useTypewriter(target: string, isFinal: boolean): string {
  const [display, setDisplay] = useState(() => (isFinal ? target : ''));
  const displayRef = useRef(display);
  const targetRef = useRef(target);

  useEffect(() => {
    targetRef.current = target;
  }, [target]);

  useEffect(() => {
    const id = window.setInterval(() => {
      const latestTarget = targetRef.current;
      const current = displayRef.current;

      if (current === latestTarget) return;

      if (!latestTarget.startsWith(current)) {
        displayRef.current = latestTarget;
        setDisplay(latestTarget);
        return;
      }

      const nextLen = findNextWordBoundary(latestTarget, current.length);
      const next = latestTarget.slice(0, nextLen);
      displayRef.current = next;
      setDisplay(next);
    }, WORD_INTERVAL_MS);

    return () => window.clearInterval(id);
  }, []);

  return display;
}

/* ─── Single transcription entry (with inline editing) ─── */
function TranscriptionEntryRow({
  entry,
  speaker,
  speakers,
  elapsedStr,
  isEditing,
  editText,
  onStartEdit,
  onEditChange,
  onSave,
  onCancel,
  onSpeakerChange,
}: {
  entry: LiveTranscription;
  speaker: SpeakerProfile;
  speakers: SpeakerProfile[];
  elapsedStr: string;
  isEditing: boolean;
  editText: string;
  onStartEdit: () => void;
  onEditChange: (text: string) => void;
  onSave: () => void;
  onCancel: () => void;
  onSpeakerChange: (speakerId: string) => void;
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const displayText = useTypewriter(entry.rawText, entry.isFinal);
  const isTyping = displayText !== entry.rawText || !entry.isFinal;
  const speakerInitials = getSpeakerInitials(speaker.name);

  useEffect(() => {
    if (isEditing && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isEditing]);

  return (
    <div className="animate-slide-up group py-3 px-4 rounded-lg hover:bg-space-card/50 transition-colors">
      <div className="flex items-start gap-4">
        <div
          className="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold shrink-0 mt-0.5"
          style={{
            backgroundColor: speaker.color + '18',
            color: speaker.color,
            border: `1.5px solid ${speaker.color}30`,
          }}
        >
          {speakerInitials}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-1.5">
            <select
              value={entry.speakerId}
              onChange={(e) => onSpeakerChange(e.target.value)}
              className="min-w-0 max-w-40 rounded-md border border-transparent bg-transparent py-0.5 pr-5 text-xs font-semibold outline-none transition-colors hover:border-space-border focus:border-accent-cyan/50"
              style={{ color: speaker.color }}
              aria-label="Speaker"
            >
              {speakers.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.name}
                </option>
              ))}
            </select>
            <span className="text-[11px] text-accent-cyan/70 font-mono bg-accent-cyan/5 px-1.5 py-0.5 rounded">
              {elapsedStr}
            </span>
            {isTyping && (
              <span className="flex items-center gap-1 text-[10px] text-accent-amber">
                <Loader2 className="w-3 h-3 animate-spin" />
                processing
              </span>
            )}
          </div>

          {/* Editable text */}
          {isEditing ? (
            <div>
              <textarea
                ref={textareaRef}
                value={editText}
                onChange={(e) => onEditChange(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    onSave();
                  }
                  if (e.key === 'Escape') onCancel();
                }}
                rows={3}
                className="w-full text-[15px] leading-relaxed text-text-primary bg-space-card border border-accent-cyan/30 rounded-lg px-3 py-2 focus:outline-none focus:border-accent-cyan/60 resize-none"
              />
              <div className="flex items-center gap-2 mt-1.5">
                <button
                  onClick={onSave}
                  className="flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/20 hover:bg-accent-cyan/20 transition-all"
                >
                  <Check className="w-3 h-3" />
                  Save
                </button>
                <button
                  onClick={onCancel}
                  className="flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium text-text-muted hover:text-text-primary transition-all"
                >
                  <X className="w-3 h-3" />
                  Cancel
                </button>
                <span className="text-[10px] text-text-muted ml-1">
                  Enter to save · Esc to cancel
                </span>
              </div>
            </div>
          ) : (
            <p
              onClick={entry.isFinal && !isTyping ? onStartEdit : undefined}
              className={`text-[15px] leading-relaxed rounded px-1 -mx-1 py-0.5 transition-colors group/text ${
                entry.isFinal && !isTyping
                  ? 'text-text-primary cursor-pointer hover:bg-accent-cyan/5'
                  : 'text-text-secondary italic'
              }`}
            >
              {displayText}
              {isTyping && (
                <span className="inline-block w-[2px] h-3.5 bg-accent-cyan/70 ml-0.5 align-middle animate-pulse" />
              )}
              {entry.isFinal && !isTyping && (
                <Pencil className="w-3 h-3 text-text-muted opacity-0 group-hover/text:opacity-60 inline ml-1.5 transition-opacity" />
              )}
            </p>
          )}

          <div className="flex items-center gap-2 mt-2">
            <div className="flex items-center gap-1.5">
              <div
                className={`w-2 h-2 rounded-full ${
                  entry.confidence > 0.9
                    ? 'bg-accent-green'
                    : entry.confidence > 0.8
                      ? 'bg-accent-amber'
                      : 'bg-accent-red'
                }`}
              />
              <span className="text-[11px] text-text-muted font-mono">
                {(entry.confidence * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─── Live clock hook (drives recording timer) ─── */
function useLocalClock() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);
  return now;
}

function SpeakerRail({
  speakers,
  activeSpeakerId,
  transcriptions,
  onAddSpeaker,
  onActiveSpeakerChange,
  onSpeakerNameChange,
  onSpeakerColorChange,
  onRemoveSpeaker,
}: {
  speakers: SpeakerProfile[];
  activeSpeakerId: string;
  transcriptions: LiveTranscription[];
  onAddSpeaker: () => void;
  onActiveSpeakerChange: (speakerId: string) => void;
  onSpeakerNameChange: (speakerId: string, name: string) => void;
  onSpeakerColorChange: (speakerId: string, color: string) => void;
  onRemoveSpeaker: (speakerId: string) => void;
}) {
  const usage = useMemo(() => getSpeakerUsage(transcriptions), [transcriptions]);

  return (
    <aside className="flex w-full shrink-0 flex-col border-t border-space-border bg-space-dark/30 lg:w-80 lg:border-l lg:border-t-0">
      <div className="flex items-center justify-between border-b border-space-border px-4 py-3">
        <div className="flex items-center gap-2">
          <Users className="h-4 w-4 text-accent-cyan" />
          <h3 className="text-sm font-semibold text-text-primary">Speakers</h3>
          <span className="rounded-md bg-space-card px-1.5 py-0.5 font-mono text-[10px] text-text-muted">
            {speakers.length}
          </span>
        </div>
        <button
          type="button"
          onClick={onAddSpeaker}
          className="rounded-lg border border-accent-cyan/25 bg-accent-cyan/10 p-1.5 text-accent-cyan transition-colors hover:bg-accent-cyan/20"
          aria-label="Add speaker"
          title="Add speaker"
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>

      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
        {speakers.map((speaker, index) => {
          const isActive = speaker.id === activeSpeakerId;
          const entryCount = usage.get(speaker.id) ?? 0;
          return (
            <div
              key={speaker.id}
              className={`rounded-lg border p-3 transition-colors ${
                isActive
                  ? 'border-accent-cyan/35 bg-accent-cyan/5'
                  : 'border-space-border bg-space-panel/60'
              }`}
            >
              <div className="flex items-center gap-2">
                <div
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-xs font-bold"
                  style={{
                    backgroundColor: `${speaker.color}18`,
                    border: `1.5px solid ${speaker.color}35`,
                    color: speaker.color,
                  }}
                >
                  {getSpeakerInitials(speaker.name)}
                </div>
                <input
                  value={speaker.name}
                  onChange={(e) => onSpeakerNameChange(speaker.id, e.target.value)}
                  onBlur={(e) =>
                    onSpeakerNameChange(
                      speaker.id,
                      e.target.value.trim() || `Speaker ${index + 1}`,
                    )
                  }
                  className="min-w-0 flex-1 rounded-md border border-space-border bg-space-card px-2 py-1.5 text-sm font-medium text-text-primary outline-none transition-colors focus:border-accent-cyan/50"
                  aria-label="Speaker name"
                />
                <button
                  type="button"
                  onClick={() => onActiveSpeakerChange(speaker.id)}
                  className={`rounded-md p-1.5 transition-colors ${
                    isActive
                      ? 'bg-accent-green/15 text-accent-green'
                      : 'text-text-muted hover:bg-space-hover hover:text-text-primary'
                  }`}
                  aria-label="Use speaker"
                  title="Use speaker"
                >
                  {isActive ? (
                    <Check className="h-3.5 w-3.5" />
                  ) : (
                    <UserRound className="h-3.5 w-3.5" />
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => onRemoveSpeaker(speaker.id)}
                  disabled={speakers.length <= 1}
                  className="rounded-md p-1.5 text-text-muted transition-colors hover:bg-accent-red/10 hover:text-accent-red disabled:cursor-not-allowed disabled:opacity-30"
                  aria-label="Remove speaker"
                  title="Remove speaker"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>

              <div className="mt-3 flex items-center justify-between gap-3">
                <div className="flex items-center gap-1.5">
                  {COLOR_SWATCHES.map((color) => (
                    <button
                      key={color}
                      type="button"
                      onClick={() => onSpeakerColorChange(speaker.id, color)}
                      className={`h-4 w-4 rounded-full border transition-transform hover:scale-110 ${
                        speaker.color === color
                          ? 'border-text-primary'
                          : 'border-space-border'
                      }`}
                      style={{ backgroundColor: color }}
                      aria-label="Set speaker color"
                      title="Set speaker color"
                    />
                  ))}
                </div>
                <span className="shrink-0 font-mono text-[10px] text-text-muted">
                  {entryCount} entries
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </aside>
  );
}

/* ─── Main panel ─── */
export default function TranscriptionPanel() {
  const {
    transcriptions,
    speakers,
    activeSpeakerId,
    isRecording,
    isPaused,
    wsConnected,
    audioLevel,
    sessionStartTime,
    selectedSttModel,
    updateLiveTranscription,
    setActiveSpeaker,
    addSpeaker,
    updateSpeaker,
    removeSpeaker,
    setTranscriptionSpeaker,
  } = useStore();
  const scrollRef = useRef<HTMLDivElement>(null);
  const isAtBottomRef = useRef(true);

  const now = useLocalClock();

  // Editing state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');

  // Auto-scroll — paused while editing
  useEffect(() => {
    if (editingId) return;
    if (scrollRef.current && isAtBottomRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [transcriptions, editingId]);

  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    isAtBottomRef.current = scrollHeight - scrollTop - clientHeight < 80;
  };

  const handleStartEdit = (id: string, text: string) => {
    setEditingId(id);
    setEditText(text);
  };

  const handleSave = () => {
    if (editingId && editText.trim()) {
      updateLiveTranscription(editingId, editText.trim());
    }
    setEditingId(null);
  };

  const handleCancel = () => {
    setEditingId(null);
  };

  const recordingSeconds =
    isRecording && sessionStartTime
      ? Math.max(0, Math.floor((now.getTime() - sessionStartTime.getTime()) / 1000))
      : 0;

  const uniqueSpeakers = new Set(transcriptions.map((t) => t.speakerId)).size || speakers.length;
  const isActivelyListening = isRecording && !isPaused;

  return (
    <div className="flex flex-col h-full rounded-xl border border-space-border bg-space-panel overflow-hidden">
      {/* ─── Header ─── */}
      <div className="px-5 py-4 border-b border-space-border shrink-0">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-accent-cyan/10">
              <AudioLines className="w-5 h-5 text-accent-cyan" />
            </div>
            <h2 className="text-lg font-semibold text-text-primary">Live Transcription</h2>
          </div>

          <div className="flex items-center gap-3">
            {/* Connection status */}
            <div
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium ${
                wsConnected
                  ? 'bg-accent-green/10 text-accent-green border border-accent-green/20'
                  : 'bg-space-card text-text-muted border border-space-border'
              }`}
            >
              {wsConnected ? (
                <Wifi className="w-3.5 h-3.5" />
              ) : (
                <WifiOff className="w-3.5 h-3.5" />
              )}
              {wsConnected ? 'Connected' : 'Disconnected'}
            </div>

            {/* Recording / Paused indicator */}
            {isRecording &&
              (isPaused ? (
                <div className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-accent-amber/10 border border-accent-amber/20">
                  <Pause className="w-3.5 h-3.5 text-accent-amber" />
                  <span className="text-xs font-semibold text-accent-amber">PAUSED</span>
                </div>
              ) : (
                <div className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-accent-red/10 border border-accent-red/20">
                  <div className="w-2 h-2 rounded-full bg-accent-red animate-pulse-glow" />
                  <span className="text-xs font-semibold text-accent-red">REC</span>
                </div>
              ))}
          </div>
        </div>

        {/* Stats bar */}
        <div className="flex items-center gap-6 text-xs text-text-muted">
          <div className="flex items-center gap-1.5">
            <Timer className="w-3.5 h-3.5" />
            <span className="font-mono font-semibold text-text-primary">
              {formatRecordingDuration(recordingSeconds)}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <Users className="w-3.5 h-3.5" />
            <span>
              {uniqueSpeakers} speaker{uniqueSpeakers !== 1 ? 's' : ''}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5" />
            <span className="font-mono">{transcriptions.length} entries</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-text-muted">Model</span>
            <span className="font-mono text-text-primary">
              {getSttModelLabel(selectedSttModel)}
            </span>
          </div>
          {transcriptions.length > 0 && (
            <span className="text-[10px] text-text-muted ml-auto">Click text to edit</span>
          )}
        </div>

        {/* Audio visualizer */}
        <div className="mt-3">
          <AudioVisualizer level={audioLevel} isActive={isActivelyListening} />
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        {/* ─── Transcription Feed ─── */}
        <div
          ref={scrollRef}
          onScroll={handleScroll}
          className="min-h-0 flex-1 overflow-y-auto py-2"
        >
          {transcriptions.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center text-text-muted">
              <AudioLines className="mb-4 h-16 w-16 opacity-20" />
              <p className="mb-1 text-base font-medium">No transcriptions yet</p>
              <p className="text-sm text-text-muted">
                {isRecording
                  ? isPaused
                    ? 'Recording is paused'
                    : 'Listening...'
                  : 'Ready to record'}
              </p>
            </div>
          ) : (
            <div className="space-y-1">
              {transcriptions.map((entry) => {
                const speaker = getSpeakerById(speakers, entry.speakerId);
                const offsetSec = sessionStartTime
                  ? Math.max(0, Math.floor((entry.timestamp.getTime() - sessionStartTime.getTime()) / 1000))
                  : 0;
                const elapsedStr = formatRecordingDuration(offsetSec);
                return (
                  <TranscriptionEntryRow
                    key={entry.id}
                    entry={entry}
                    speaker={speaker}
                    speakers={speakers}
                    elapsedStr={elapsedStr}
                    isEditing={editingId === entry.id}
                    editText={editText}
                    onStartEdit={() => handleStartEdit(entry.id, entry.rawText)}
                    onEditChange={setEditText}
                    onSave={handleSave}
                    onCancel={handleCancel}
                    onSpeakerChange={(speakerId) =>
                      setTranscriptionSpeaker(entry.id, speakerId)
                    }
                  />
                );
              })}
            </div>
          )}

          {/* Scroll-to-bottom button */}
          {transcriptions.length > 5 && (
            <button
              onClick={() => {
                if (scrollRef.current) {
                  scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
                  isAtBottomRef.current = true;
                }
              }}
              className="sticky bottom-2 mx-auto flex items-center gap-1 rounded-full border border-space-border bg-space-card px-3 py-1 text-xs text-text-muted shadow-lg transition-all hover:border-accent-cyan/30 hover:text-text-primary"
            >
              <ChevronDown className="h-3 w-3" />
              Latest
            </button>
          )}
        </div>

        <SpeakerRail
          speakers={speakers}
          activeSpeakerId={activeSpeakerId}
          transcriptions={transcriptions}
          onAddSpeaker={addSpeaker}
          onActiveSpeakerChange={setActiveSpeaker}
          onSpeakerNameChange={(speakerId, name) =>
            updateSpeaker(speakerId, { name })
          }
          onSpeakerColorChange={(speakerId, color) =>
            updateSpeaker(speakerId, { color })
          }
          onRemoveSpeaker={removeSpeaker}
        />
      </div>

      {/* ─── Bottom indicator ─── */}
      {isRecording && (
        <div className="px-5 py-3 border-t border-space-border shrink-0">
          <div className="flex items-center gap-3 text-xs text-text-muted">
            {isPaused ? (
              <>
                <Pause className="w-3.5 h-3.5 text-accent-amber" />
                <span className="text-accent-amber">
                  Paused — audio capture suspended. Click Resume to continue.
                </span>
              </>
            ) : (
              <>
                <div className="flex gap-0.5">
                  {[3, 4, 2, 5, 3, 4, 2, 3].map((h, i) => (
                    <div
                      key={i}
                      className="w-[3px] bg-accent-cyan/50 rounded-full animate-pulse"
                      style={{
                        height: `${h * (3 + audioLevel * 3)}px`,
                        animationDelay: `${i * 80}ms`,
                        animationDuration: `${400 + i * 100}ms`,
                      }}
                    />
                  ))}
                </div>
                <span>Listening — transcribing in real time</span>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
