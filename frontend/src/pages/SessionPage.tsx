import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Mic,
  Square,
  Pause,
  Play,
  AlertCircle,
  CheckCircle2,
  X,
  Clock,
} from 'lucide-react';
import TranscriptionPanel from '../components/session/TranscriptionPanel';
import { useWhisper } from '../hooks/useWhisper';
import { useStore } from '../store/useStore';

export default function SessionPage() {
  const {
    startRecording,
    pauseRecording,
    resumeRecording,
    stopRecording,
    isRecording,
    isPaused,
  } = useWhisper();
  const {
    recordingError,
    transcriptions,
    savedSessionToast,
    dismissSavedToast,
    sessionStartTime,
  } = useStore();
  const navigate = useNavigate();

  // Auto-dismiss toast after 5 seconds
  useEffect(() => {
    if (savedSessionToast) {
      const timer = setTimeout(dismissSavedToast, 5000);
      return () => clearTimeout(timer);
    }
  }, [savedSessionToast, dismissSavedToast]);

  // Tick every second to update elapsed timer in real-time
  const [, setTick] = useState(0);
  useEffect(() => {
    if (isRecording) {
      const timer = setInterval(() => setTick((t) => t + 1), 1000);
      return () => clearInterval(timer);
    }
  }, [isRecording]);

  const elapsed = sessionStartTime
    ? Math.floor((Date.now() - sessionStartTime.getTime()) / 1000)
    : 0;
  const elapsedStr = `${String(Math.floor(elapsed / 60)).padStart(2, '0')}:${String(elapsed % 60).padStart(2, '0')}`;

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)] animate-fade-in">
      {/* Full-width transcription canvas */}
      <div className="flex-1 p-4 min-h-0">
        <TranscriptionPanel />
      </div>

      {/* Auto-save toast notification */}
      {savedSessionToast && (
        <div className="fixed top-20 right-6 z-50 animate-slide-up">
          <div className="flex items-center gap-3 px-5 py-3.5 bg-space-panel border border-accent-green/30 rounded-xl shadow-2xl shadow-accent-green/5">
            <CheckCircle2 className="w-5 h-5 text-accent-green shrink-0" />
            <div>
              <p className="text-sm font-semibold text-text-primary">Session saved</p>
              <p className="text-xs text-text-secondary mt-0.5">
                <span className="font-mono text-accent-cyan">{savedSessionToast}</span>{' '}
                has been saved to Session History
              </p>
            </div>
            <div className="flex items-center gap-2 ml-4">
              <button
                onClick={() => {
                  dismissSavedToast();
                  navigate('/history');
                }}
                className="text-xs text-accent-cyan hover:underline font-medium"
              >
                View
              </button>
              <button
                onClick={dismissSavedToast}
                className="p-1 rounded text-text-muted hover:text-text-primary transition-colors"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Bottom control bar */}
      <div className="border-t border-space-border bg-space-dark/80 backdrop-blur-md px-6 py-3 shrink-0">
        <div className="flex items-center justify-between">
          {/* Left: main controls */}
          <div className="flex items-center gap-3">
            {!isRecording ? (
              /* ─── Start button ─── */
              <button
                onClick={startRecording}
                className="flex items-center gap-2.5 px-5 py-2.5 rounded-xl text-sm font-semibold bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30 hover:bg-accent-cyan/25 transition-all"
              >
                <Mic className="w-4 h-4" />
                Start Recording
              </button>
            ) : (
              <>
                {/* ─── Pause / Resume button ─── */}
                {isPaused ? (
                  <button
                    onClick={resumeRecording}
                    className="flex items-center gap-2.5 px-5 py-2.5 rounded-xl text-sm font-semibold bg-accent-green/15 text-accent-green border border-accent-green/30 hover:bg-accent-green/25 transition-all"
                  >
                    <Play className="w-4 h-4" />
                    Resume
                  </button>
                ) : (
                  <button
                    onClick={pauseRecording}
                    className="flex items-center gap-2.5 px-5 py-2.5 rounded-xl text-sm font-semibold bg-accent-amber/15 text-accent-amber border border-accent-amber/30 hover:bg-accent-amber/25 transition-all"
                  >
                    <Pause className="w-4 h-4" />
                    Pause
                  </button>
                )}

                {/* ─── Stop button ─── */}
                <button
                  onClick={stopRecording}
                  className="flex items-center gap-2.5 px-5 py-2.5 rounded-xl text-sm font-semibold bg-accent-red/15 text-accent-red border border-accent-red/30 hover:bg-accent-red/25 transition-all"
                >
                  <Square className="w-4 h-4" />
                  Stop
                </button>
              </>
            )}
          </div>

          {/* Center: status indicators */}
          <div className="flex items-center gap-4">
            {recordingError && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-accent-red/10 border border-accent-red/20 rounded-lg">
                <AlertCircle className="w-4 h-4 text-accent-red shrink-0" />
                <span className="text-xs text-accent-red">{recordingError}</span>
              </div>
            )}

            {isRecording && (
              <div className="flex items-center gap-2 text-xs text-text-muted">
                <Clock className="w-3.5 h-3.5" />
                <span className="font-mono">{elapsedStr}</span>
                <span className="mx-1 text-space-border">|</span>
                <span className="font-mono">
                {transcriptions.filter((t) => t.confidence >= 0.5).length} entries
              </span>
              </div>
            )}
          </div>

          {/* Right: info */}
          <div className="flex items-center gap-4 text-xs text-text-muted">
            {isRecording && (
              <div className="flex items-center gap-2">
                {isPaused ? (
                  <span className="flex items-center gap-1.5 text-accent-amber">
                    <Pause className="w-3 h-3" />
                    Paused
                  </span>
                ) : (
                  <span className="flex items-center gap-1.5 text-accent-red">
                    <div className="w-2 h-2 rounded-full bg-accent-red animate-pulse-glow" />
                    Recording
                  </span>
                )}
                <span className="mx-1 text-space-border">|</span>
              </div>
            )}
            <span className="font-mono">
              Whisper large-v3 &middot; 16kHz mono &middot; VAD（有语音才发送）
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
