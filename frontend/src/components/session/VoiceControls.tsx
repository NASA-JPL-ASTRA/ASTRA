import { useState } from 'react';
import { Mic, Radio, Send, Volume2, VolumeX, Bot, CheckCircle2, Loader2, XCircle } from 'lucide-react';
import { useStore } from '../../store/useStore';
import { voiceCommands } from '../../mock/data';

export default function VoiceControls() {
  const { isRecording, isMuted, toggleRecording, toggleMute } = useStore();
  const [commandInput, setCommandInput] = useState('');

  const statusConfig = {
    recognized: { icon: CheckCircle2, color: 'text-accent-cyan', label: 'Recognized' },
    processing: { icon: Loader2, color: 'text-accent-amber', label: 'Processing', spin: true },
    executed: { icon: CheckCircle2, color: 'text-accent-green', label: 'Executed' },
    failed: { icon: XCircle, color: 'text-accent-red', label: 'Failed' },
  };

  return (
    <div className="border-t border-space-border bg-space-dark/80 backdrop-blur-md px-6 py-3">
      <div className="flex items-center gap-4">
        {/* Audio Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={toggleRecording}
            className={`p-3 rounded-xl transition-all ${
              isRecording
                ? 'bg-accent-red/15 text-accent-red border border-accent-red/30 shadow-[0_0_20px_rgba(255,82,82,0.15)]'
                : 'bg-space-card text-text-secondary border border-space-border hover:border-accent-cyan/30'
            }`}
          >
            {isRecording ? <Radio className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
          </button>
          <button
            onClick={toggleMute}
            className={`p-2 rounded-lg transition-all ${
              isMuted
                ? 'bg-accent-amber/15 text-accent-amber border border-accent-amber/30'
                : 'text-text-secondary hover:text-text-primary hover:bg-space-hover'
            }`}
          >
            {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
          </button>
        </div>

        {/* Audio Visualizer */}
        {isRecording && (
          <div className="flex items-center gap-[2px] h-8 px-3">
            {Array.from({ length: 20 }).map((_, i) => (
              <div
                key={i}
                className="w-[3px] bg-accent-cyan/60 rounded-full animate-pulse"
                style={{
                  height: `${((i * 11) % 24) + 4}px`,
                  animationDelay: `${i * 50}ms`,
                  animationDuration: `${300 + ((i * 73) % 500)}ms`,
                }}
              />
            ))}
          </div>
        )}

        {/* Divider */}
        <div className="w-px h-8 bg-space-border" />

        {/* Command Input */}
        <div className="flex-1 flex items-center gap-3">
          <Bot className="w-4 h-4 text-accent-purple shrink-0" />
          <input
            type="text"
            value={commandInput}
            onChange={(e) => setCommandInput(e.target.value)}
            placeholder='Type or say "ASTRA, ..." to issue a command'
            className="flex-1 bg-transparent text-sm text-text-primary placeholder-text-muted focus:outline-none"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && commandInput.trim()) {
                setCommandInput('');
              }
            }}
          />
          <button
            className="p-2 rounded-lg text-accent-cyan hover:bg-accent-cyan/10 transition-all disabled:opacity-30"
            disabled={!commandInput.trim()}
          >
            <Send className="w-4 h-4" />
          </button>
        </div>

        {/* Divider */}
        <div className="w-px h-8 bg-space-border" />

        {/* Recent Commands */}
        <div className="flex items-center gap-3">
          {voiceCommands.slice(0, 2).map((vc) => {
            const config = statusConfig[vc.status];
            const Icon = config.icon;
            return (
              <div
                key={vc.id}
                className="flex items-center gap-1.5 text-[10px] text-text-muted bg-space-card px-2 py-1 rounded-lg border border-space-border max-w-48 truncate"
              >
                <Icon
                  className={`w-3 h-3 ${config.color} shrink-0 ${
                    'spin' in config ? 'animate-spin' : ''
                  }`}
                />
                <span className="truncate">{vc.command}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
