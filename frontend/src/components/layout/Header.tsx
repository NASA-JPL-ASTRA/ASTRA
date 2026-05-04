import { Bell, Search, Mic, MicOff, Circle } from 'lucide-react';
import { useStore } from '../../store/useStore';

export default function Header() {
  const { isRecording, isMuted, toggleRecording, toggleMute, sessions, currentSessionId } = useStore();
  const currentSession = sessions.find((s) => s.id === currentSessionId);

  return (
    <header className="h-14 bg-space-dark/80 backdrop-blur-md border-b border-space-border flex items-center justify-between px-6 sticky top-0 z-40">
      {/* Left - Session Info */}
      <div className="flex items-center gap-4">
        {currentSession && (
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              {currentSession.status === 'active' && (
                <Circle className="w-2.5 h-2.5 fill-accent-green text-accent-green animate-pulse-glow" />
              )}
              <span className="text-sm font-semibold text-text-primary font-mono">
                {currentSession.name}
              </span>
            </div>
            <span className="text-xs text-text-muted px-2 py-0.5 rounded bg-space-card">
              {currentSession.testbed}
            </span>
          </div>
        )}
      </div>

      {/* Center - Search */}
      <div className="flex-1 max-w-md mx-8">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
          <input
            type="text"
            placeholder="Search logs, commands, telemetry..."
            className="w-full bg-space-card border border-space-border rounded-lg pl-10 pr-4 py-2 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-cyan/50 focus:ring-1 focus:ring-accent-cyan/20 transition-all"
          />
        </div>
      </div>

      {/* Right - Controls */}
      <div className="flex items-center gap-3">
        {/* Recording Indicator */}
        <button
          onClick={toggleRecording}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            isRecording
              ? 'bg-accent-red/15 text-accent-red border border-accent-red/30'
              : 'bg-space-card text-text-secondary border border-space-border hover:border-accent-cyan/30'
          }`}
        >
          <div
            className={`w-2 h-2 rounded-full ${
              isRecording ? 'bg-accent-red animate-pulse-glow' : 'bg-text-muted'
            }`}
          />
          {isRecording ? 'Recording' : 'Paused'}
        </button>

        {/* Mute Toggle */}
        <button
          onClick={toggleMute}
          className={`p-2 rounded-lg transition-all ${
            isMuted
              ? 'bg-accent-amber/15 text-accent-amber border border-accent-amber/30'
              : 'text-text-secondary hover:text-text-primary hover:bg-space-hover'
          }`}
          title={isMuted ? 'Unmute' : 'Mute'}
        >
          {isMuted ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
        </button>

        {/* Notifications */}
        <button className="p-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-space-hover transition-all relative">
          <Bell className="w-4 h-4" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-accent-red rounded-full" />
        </button>

        {/* Operator Avatars */}
        <div className="flex -space-x-2 ml-2">
          {currentSession?.operators.map((op) => (
            <div
              key={op.id}
              className="w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold border-2 border-space-dark"
              style={{ backgroundColor: op.color + '20', color: op.color }}
              title={`${op.name} - ${op.role}`}
            >
              {op.avatarInitials}
            </div>
          ))}
        </div>
      </div>
    </header>
  );
}
