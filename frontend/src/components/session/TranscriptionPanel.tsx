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
} from 'lucide-react';
import { useStore } from '../../store/useStore';
import type { LiveTranscription } from '../../store/useStore';

/* ─── Confidence color (0–50% red, 50–85% yellow, 85–100% green) ─── */
function getConfidenceColorClass(confidence: number): string {
  if (confidence >= 0.85) return 'bg-accent-green';
  if (confidence >= 0.5) return 'bg-accent-amber';
  return 'bg-accent-red';
}

/* ─── Speaker color mapping ─── */
const SPEAKER_COLORS = [
  { color: '#00d4ff', name: 'Speaker A', initials: 'SA' },
  { color: '#00e676', name: 'Speaker B', initials: 'SB' },
  { color: '#b388ff', name: 'Speaker C', initials: 'SC' },
  { color: '#ffab00', name: 'Speaker D', initials: 'SD' },
  { color: '#ff5252', name: 'Speaker E', initials: 'SE' },
];

function getSpeaker(speakerId: string, speakerMap: Map<string, number>) {
  if (!speakerMap.has(speakerId)) {
    speakerMap.set(speakerId, speakerMap.size);
  }
  const idx = speakerMap.get(speakerId)!;
  return SPEAKER_COLORS[idx % SPEAKER_COLORS.length];
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
        const barLevel = isActive
          ? Math.max(
              0.05,
              level * (0.4 + 0.6 * Math.sin((i / bars) * Math.PI)) +
                Math.random() * 0.08
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

/* ─── Single transcription entry (with inline editing) ─── */
function TranscriptionEntryRow({
  entry,
  speaker,
  elapsedStr,
  isEditing,
  editText,
  onStartEdit,
  onEditChange,
  onSave,
  onCancel,
}: {
  entry: LiveTranscription;
  speaker: { color: string; name: string; initials: string };
  elapsedStr: string;
  isEditing: boolean;
  editText: string;
  onStartEdit: () => void;
  onEditChange: (text: string) => void;
  onSave: () => void;
  onCancel: () => void;
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

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
          {speaker.initials}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-1.5">
            <span className="text-xs font-semibold" style={{ color: speaker.color }}>
              {speaker.name}
            </span>
            <span className="text-[11px] text-accent-cyan/70 font-mono bg-accent-cyan/5 px-1.5 py-0.5 rounded">
              {elapsedStr}
            </span>
            {!entry.isFinal && (
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
              onClick={onStartEdit}
              className={`text-[15px] leading-relaxed cursor-pointer rounded px-1 -mx-1 py-0.5 hover:bg-accent-cyan/5 transition-colors group/text ${
                entry.isFinal ? 'text-text-primary' : 'text-text-secondary italic'
              }`}
            >
              {entry.rawText}
              <Pencil className="w-3 h-3 text-text-muted opacity-0 group-hover/text:opacity-60 inline ml-1.5 transition-opacity" />
            </p>
          )}

          <div className="flex items-center gap-2 mt-2">
            <div className="flex items-center gap-1.5">
              <div
                className={`w-2 h-2 rounded-full ${getConfidenceColorClass(entry.confidence)}`}
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

/* ─── Main panel ─── */
export default function TranscriptionPanel() {
  const {
    transcriptions,
    isRecording,
    isPaused,
    wsConnected,
    audioLevel,
    sessionStartTime,
    updateLiveTranscription,
  } = useStore();
  const scrollRef = useRef<HTMLDivElement>(null);
  const isAtBottomRef = useRef(true);

  const speakerMap = useMemo(() => new Map<string, number>(), []);
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
      ? Math.floor((now.getTime() - sessionStartTime.getTime()) / 1000)
      : 0;

  const displayedTranscriptions = useMemo(
    () => transcriptions.filter((t) => t.confidence >= 0.5),
    [transcriptions],
  );
  const uniqueSpeakers = new Set(displayedTranscriptions.map((t) => t.speakerId)).size;
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
            <span className="font-mono">{displayedTranscriptions.length} entries</span>
          </div>
          {displayedTranscriptions.length > 0 && (
            <span className="text-[10px] text-text-muted ml-auto">Click text to edit</span>
          )}
        </div>

        {/* Audio visualizer */}
        <div className="mt-3">
          <AudioVisualizer level={audioLevel} isActive={isActivelyListening} />
        </div>
      </div>

      {/* ─── Transcription Feed ─── */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto py-2"
      >
        {displayedTranscriptions.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-text-muted">
            <AudioLines className="w-16 h-16 mb-4 opacity-20" />
            <p className="text-base font-medium mb-1">No transcriptions yet</p>
            <p className="text-sm text-text-muted">
              {isRecording
                ? isPaused
                  ? 'Recording is paused — click Resume to continue'
                  : 'Listening... speak into your microphone'
                : 'Click "Start Recording" to begin a new session'}
            </p>
          </div>
        ) : (
          <div className="space-y-1">
            {displayedTranscriptions.map((entry) => {
              const speaker = getSpeaker(entry.speakerId, speakerMap);
              const offsetSec = sessionStartTime
                ? Math.max(0, Math.floor((entry.timestamp.getTime() - sessionStartTime.getTime()) / 1000))
                : 0;
              const elapsedStr = formatRecordingDuration(offsetSec);
              return (
                <TranscriptionEntryRow
                  key={entry.id}
                  entry={entry}
                  speaker={speaker}
                  elapsedStr={elapsedStr}
                  isEditing={editingId === entry.id}
                  editText={editText}
                  onStartEdit={() => handleStartEdit(entry.id, entry.rawText)}
                  onEditChange={setEditText}
                  onSave={handleSave}
                  onCancel={handleCancel}
                />
              );
            })}
          </div>
        )}

        {/* Scroll-to-bottom button */}
        {displayedTranscriptions.length > 5 && (
          <button
            onClick={() => {
              if (scrollRef.current) {
                scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
                isAtBottomRef.current = true;
              }
            }}
            className="sticky bottom-2 mx-auto flex items-center gap-1 px-3 py-1 bg-space-card border border-space-border rounded-full text-xs text-text-muted hover:text-text-primary hover:border-accent-cyan/30 transition-all shadow-lg"
          >
            <ChevronDown className="w-3 h-3" />
            Latest
          </button>
        )}
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
