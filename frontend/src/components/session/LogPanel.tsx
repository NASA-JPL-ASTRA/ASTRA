import { useState } from 'react';
import {
  FileText,
  Edit3,
  Check,
  X,
  Tag,
  AlertTriangle,
  AlertCircle,
  CheckCircle2,
  Info,
  Bot,
  Pencil,
  Activity,
  Filter,
} from 'lucide-react';
import { useStore } from '../../store/useStore';
import { operators } from '../../mock/data';
import type { LogCategory, LogEntry } from '../../types';

const categoryConfig: Record<LogCategory, { label: string; color: string; icon: typeof Info }> = {
  observation: { label: 'Observation', color: '#00d4ff', icon: Info },
  command: { label: 'Command', color: '#b388ff', icon: Activity },
  anomaly: { label: 'Anomaly', color: '#ff5252', icon: AlertTriangle },
  measurement: { label: 'Measurement', color: '#00e676', icon: CheckCircle2 },
  procedure: { label: 'Procedure', color: '#ffab00', icon: FileText },
  system: { label: 'System', color: '#8899aa', icon: AlertCircle },
  'voice-command': { label: 'Voice Cmd', color: '#00d4ff', icon: Bot },
};

const severityConfig = {
  info: { icon: Info, color: 'text-accent-cyan', bg: 'bg-accent-cyan/10' },
  warning: { icon: AlertTriangle, color: 'text-accent-amber', bg: 'bg-accent-amber/10' },
  critical: { icon: AlertCircle, color: 'text-accent-red', bg: 'bg-accent-red/10' },
  success: { icon: CheckCircle2, color: 'text-accent-green', bg: 'bg-accent-green/10' },
};

function formatTime(date: Date): string {
  return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function LogEntryCard({ entry }: { entry: LogEntry }) {
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(entry.content);
  const { updateLog } = useStore();
  const operator = operators.find((o) => o.id === entry.operatorId);
  const category = categoryConfig[entry.category];
  const severity = severityConfig[entry.severity];
  const SeverityIcon = severity.icon;

  const handleSave = () => {
    updateLog(entry.id, editContent);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditContent(entry.content);
    setIsEditing(false);
  };

  return (
    <div className="p-4 rounded-lg bg-space-card border border-space-border hover:border-space-hover transition-all animate-slide-up group">
      {/* Top row */}
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <div className={`p-1 rounded ${severity.bg}`}>
            <SeverityIcon className={`w-3.5 h-3.5 ${severity.color}`} />
          </div>
          <h3 className="text-sm font-semibold text-text-primary truncate">{entry.title}</h3>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          {entry.isAIGenerated && (
            <span className="flex items-center gap-1 text-[10px] text-accent-purple bg-accent-purple/10 px-1.5 py-0.5 rounded">
              <Bot className="w-3 h-3" /> AI
            </span>
          )}
          {entry.isEdited && (
            <span className="flex items-center gap-1 text-[10px] text-accent-amber bg-accent-amber/10 px-1.5 py-0.5 rounded">
              <Pencil className="w-3 h-3" /> Edited
            </span>
          )}
        </div>
      </div>

      {/* Content */}
      {isEditing ? (
        <div className="mb-3">
          <textarea
            value={editContent}
            onChange={(e) => setEditContent(e.target.value)}
            className="w-full bg-space-black border border-accent-cyan/30 rounded-lg p-3 text-sm text-text-primary resize-none focus:outline-none focus:ring-1 focus:ring-accent-cyan/30"
            rows={3}
            autoFocus
          />
          <div className="flex items-center gap-2 mt-2">
            <button
              onClick={handleSave}
              className="flex items-center gap-1 px-3 py-1 bg-accent-green/15 text-accent-green border border-accent-green/30 rounded text-xs font-medium hover:bg-accent-green/25 transition-all"
            >
              <Check className="w-3 h-3" /> Save
            </button>
            <button
              onClick={handleCancel}
              className="flex items-center gap-1 px-3 py-1 bg-space-hover text-text-secondary border border-space-border rounded text-xs font-medium hover:text-text-primary transition-all"
            >
              <X className="w-3 h-3" /> Cancel
            </button>
          </div>
        </div>
      ) : (
        <p className="text-sm text-text-secondary leading-relaxed mb-3">{entry.content}</p>
      )}

      {/* Bottom row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className="text-[10px] font-medium px-1.5 py-0.5 rounded"
            style={{
              backgroundColor: category.color + '15',
              color: category.color,
            }}
          >
            {category.label}
          </span>
          {entry.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="flex items-center gap-0.5 text-[10px] text-text-muted bg-space-hover px-1.5 py-0.5 rounded"
            >
              <Tag className="w-2.5 h-2.5" />
              {tag}
            </span>
          ))}
          {entry.telemetryRef && (
            <span className="text-[10px] text-accent-cyan bg-accent-cyan/10 px-1.5 py-0.5 rounded font-mono">
              📊 Telemetry
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <span className="text-[10px] font-mono text-text-muted">{formatTime(entry.timestamp)}</span>
          <span className="text-[10px]" style={{ color: operator?.color }}>
            {operator?.name}
          </span>
          {!isEditing && (
            <button
              onClick={() => setIsEditing(true)}
              className="p-1 rounded text-text-muted hover:text-accent-cyan opacity-0 group-hover:opacity-100 transition-all"
            >
              <Edit3 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default function LogPanel() {
  const { logs } = useStore();
  const [activeFilter, setActiveFilter] = useState<LogCategory | 'all'>('all');

  const filteredLogs =
    activeFilter === 'all' ? logs : logs.filter((l) => l.category === activeFilter);

  const categories: (LogCategory | 'all')[] = [
    'all',
    'observation',
    'command',
    'anomaly',
    'measurement',
    'procedure',
    'voice-command',
  ];

  return (
    <div className="flex flex-col h-full rounded-xl border border-space-border bg-space-panel overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-space-border shrink-0">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-accent-cyan" />
            <h2 className="text-sm font-semibold text-text-primary">Structured Logs</h2>
          </div>
          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-text-muted" />
            <span className="text-[10px] text-text-muted font-mono">{filteredLogs.length} entries</span>
          </div>
        </div>
        {/* Category Filter */}
        <div className="flex gap-1 overflow-x-auto pb-1 -mb-1">
          {categories.map((cat) => {
            const config = cat === 'all' ? null : categoryConfig[cat];
            return (
              <button
                key={cat}
                onClick={() => setActiveFilter(cat)}
                className={`px-2 py-1 rounded text-[10px] font-medium whitespace-nowrap transition-all ${
                  activeFilter === cat
                    ? 'bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30'
                    : 'text-text-muted hover:text-text-secondary bg-space-card border border-transparent'
                }`}
              >
                {cat === 'all' ? 'All' : config?.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Log Feed */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {filteredLogs.map((entry) => (
          <LogEntryCard key={entry.id} entry={entry} />
        ))}
      </div>
    </div>
  );
}
