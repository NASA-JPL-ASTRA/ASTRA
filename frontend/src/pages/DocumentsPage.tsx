import { useState } from 'react';
import {
  FileText,
  Upload,
  BookOpen,
  ClipboardList,
  FileCode2,
  FileSpreadsheet,
  Search,
  CheckCircle2,
  Loader2,
  AlertCircle,
  Trash2,
  Eye,
  MoreVertical,
  Plus,
  Brain,
  Activity,
  Gauge,
  Thermometer,
  Zap,
  Radio,
} from 'lucide-react';
import { documents, telemetryStreams } from '../mock/data';
import type { Document } from '../types';

const typeConfig: Record<Document['type'], { icon: typeof FileText; color: string; label: string }> = {
  manual: { icon: BookOpen, color: '#00d4ff', label: 'Manual' },
  procedure: { icon: ClipboardList, color: '#00e676', label: 'Procedure' },
  specification: { icon: FileSpreadsheet, color: '#b388ff', label: 'Specification' },
  'design-doc': { icon: FileCode2, color: '#ffab00', label: 'Design Doc' },
};

const statusConfig: Record<Document['status'], { icon: typeof CheckCircle2; color: string; label: string }> = {
  indexed: { icon: CheckCircle2, color: 'text-accent-green', label: 'Indexed' },
  processing: { icon: Loader2, color: 'text-accent-amber', label: 'Processing' },
  error: { icon: AlertCircle, color: 'text-accent-red', label: 'Error' },
};

function formatDate(date: Date): string {
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

const telemetryIcons: Record<string, typeof Activity> = {
  tel_volt_ch7: Zap,
  tel_temp_j3: Thermometer,
  tel_torque_j3: Gauge,
  tel_imu_accel: Radio,
  tel_current_arm: Zap,
  tel_encoder_j4: Activity,
};

export default function DocumentsPage() {
  const [isDragOver, setIsDragOver] = useState(false);
  const [activeTab, setActiveTab] = useState<'documents' | 'telemetry'>('documents');

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Page Title */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Documents & Data</h1>
          <p className="text-sm text-text-secondary mt-1">
            Manage system documents for RAG and telemetry data streams
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-accent-purple/10 border border-accent-purple/20 rounded-lg">
            <Brain className="w-4 h-4 text-accent-purple" />
            <span className="text-xs text-accent-purple font-medium">RAG System Active</span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-space-card p-1 rounded-lg w-fit">
        <button
          onClick={() => setActiveTab('documents')}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${
            activeTab === 'documents'
              ? 'bg-accent-cyan/15 text-accent-cyan'
              : 'text-text-secondary hover:text-text-primary'
          }`}
        >
          <FileText className="w-4 h-4" />
          Documents
        </button>
        <button
          onClick={() => setActiveTab('telemetry')}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${
            activeTab === 'telemetry'
              ? 'bg-accent-cyan/15 text-accent-cyan'
              : 'text-text-secondary hover:text-text-primary'
          }`}
        >
          <Activity className="w-4 h-4" />
          Telemetry Data
        </button>
      </div>

      {/* ─── Documents Tab ─── */}
      {activeTab === 'documents' && (
        <>
          {/* Upload Zone */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragOver(true);
            }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={() => setIsDragOver(false)}
            className={`rounded-xl border-2 border-dashed p-8 text-center transition-all ${
              isDragOver
                ? 'border-accent-cyan bg-accent-cyan/5'
                : 'border-space-border bg-space-panel hover:border-space-hover'
            }`}
          >
            <Upload
              className={`w-10 h-10 mx-auto mb-3 ${isDragOver ? 'text-accent-cyan' : 'text-text-muted'}`}
            />
            <p className="text-sm text-text-primary font-medium mb-1">
              Drag & drop documents here, or click to browse
            </p>
            <p className="text-xs text-text-muted">
              Supports PDF, DOCX, TXT, MD files. Max 100MB per file.
            </p>
            <button className="mt-4 flex items-center gap-2 mx-auto px-4 py-2 bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/30 rounded-lg text-sm font-medium hover:bg-accent-cyan/20 transition-all">
              <Plus className="w-4 h-4" />
              Upload Document
            </button>
          </div>

          {/* Search */}
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
            <input
              type="text"
              placeholder="Search documents..."
              className="w-full bg-space-card border border-space-border rounded-lg pl-10 pr-4 py-2.5 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-cyan/50 transition-all"
            />
          </div>

          {/* Documents Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {documents.map((doc) => {
              const typeInfo = typeConfig[doc.type];
              const statusInfo = statusConfig[doc.status];
              const TypeIcon = typeInfo.icon;
              const StatusIcon = statusInfo.icon;
              return (
                <div
                  key={doc.id}
                  className="rounded-xl border border-space-border bg-space-panel p-5 hover:border-accent-cyan/20 transition-all group"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div
                      className="p-2.5 rounded-lg"
                      style={{ backgroundColor: typeInfo.color + '15' }}
                    >
                      <TypeIcon className="w-5 h-5" style={{ color: typeInfo.color }} />
                    </div>
                    <button className="p-1 rounded text-text-muted hover:text-text-primary opacity-0 group-hover:opacity-100 transition-all">
                      <MoreVertical className="w-4 h-4" />
                    </button>
                  </div>
                  <h3 className="text-sm font-semibold text-text-primary mb-1 line-clamp-2 leading-snug">
                    {doc.name}
                  </h3>
                  <span
                    className="inline-block text-[10px] font-medium px-1.5 py-0.5 rounded mb-3"
                    style={{ backgroundColor: typeInfo.color + '15', color: typeInfo.color }}
                  >
                    {typeInfo.label}
                  </span>
                  <div className="flex items-center justify-between text-xs text-text-muted mb-3">
                    <span>{formatDate(doc.uploadDate)}</span>
                    <span>{doc.size}</span>
                    {doc.pages && <span>{doc.pages} pages</span>}
                  </div>
                  <div className="flex items-center justify-between pt-3 border-t border-space-border">
                    <div className="flex items-center gap-1.5">
                      <StatusIcon
                        className={`w-3.5 h-3.5 ${statusInfo.color} ${
                          doc.status === 'processing' ? 'animate-spin' : ''
                        }`}
                      />
                      <span className={`text-xs ${statusInfo.color}`}>{statusInfo.label}</span>
                    </div>
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-all">
                      <button className="p-1.5 rounded-lg text-text-muted hover:text-accent-cyan hover:bg-accent-cyan/10 transition-all">
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                      <button className="p-1.5 rounded-lg text-text-muted hover:text-accent-red hover:bg-accent-red/10 transition-all">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* ─── Telemetry Data Tab ─── */}
      {activeTab === 'telemetry' && (
        <>
          <div className="flex items-center justify-between">
            <p className="text-sm text-text-secondary">
              Live telemetry data streams from the active testbed
            </p>
            <span className="text-xs text-text-muted font-mono">
              {telemetryStreams.length} active streams
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {telemetryStreams.map((stream) => {
              const Icon = telemetryIcons[stream.id] || Activity;
              const statusColor = {
                nominal: { text: 'text-accent-green', bg: 'bg-accent-green/10', border: 'border-accent-green/20' },
                warning: { text: 'text-accent-amber', bg: 'bg-accent-amber/10', border: 'border-accent-amber/20' },
                critical: { text: 'text-accent-red', bg: 'bg-accent-red/10', border: 'border-accent-red/20' },
              }[stream.status];

              return (
                <div
                  key={stream.id}
                  className={`rounded-xl border ${statusColor.border} ${statusColor.bg} p-5 transition-all hover:scale-[1.01]`}
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Icon className={`w-5 h-5 ${statusColor.text}`} />
                      <h3 className="text-sm font-semibold text-text-primary">{stream.name}</h3>
                    </div>
                    <span
                      className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded ${statusColor.bg} ${statusColor.text}`}
                    >
                      {stream.status}
                    </span>
                  </div>

                  <div className="flex items-baseline gap-1.5 mb-4">
                    <span className={`text-2xl font-bold font-mono ${statusColor.text}`}>
                      {stream.currentValue.toFixed(1)}
                    </span>
                    <span className="text-xs text-text-muted">{stream.unit}</span>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-xs text-text-muted">
                      <span>Range</span>
                      <span className="font-mono">
                        {stream.min} – {stream.max} {stream.unit}
                      </span>
                    </div>
                    {stream.threshold && (
                      <>
                        <div className="flex items-center justify-between text-xs text-text-muted">
                          <span>Warning threshold</span>
                          <span className="font-mono text-accent-amber">
                            {stream.threshold.warning} {stream.unit}
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-xs text-text-muted">
                          <span>Critical threshold</span>
                          <span className="font-mono text-accent-red">
                            {stream.threshold.critical} {stream.unit}
                          </span>
                        </div>
                      </>
                    )}
                  </div>

                  <div className="mt-4 pt-3 border-t border-space-border/50">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-text-muted font-mono">{stream.id}</span>
                      <span className="text-[10px] text-text-muted">
                        {stream.data.length} data points
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
