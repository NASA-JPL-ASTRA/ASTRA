export interface Operator {
  id: string;
  name: string;
  role: string;
  color: string;
  avatarInitials: string;
}

export interface TranscriptionEntry {
  id: string;
  timestamp: Date;
  operatorId: string;
  rawText: string;
  confidence: number;
  isProcessing?: boolean;
}

export interface LogEntry {
  id: string;
  timestamp: Date;
  category: LogCategory;
  title: string;
  content: string;
  operatorId: string;
  tags: string[];
  telemetryRef?: string;
  isEdited?: boolean;
  isAIGenerated: boolean;
  severity: 'info' | 'warning' | 'critical' | 'success';
}

export type LogCategory =
  | 'observation'
  | 'command'
  | 'anomaly'
  | 'measurement'
  | 'procedure'
  | 'system'
  | 'voice-command';

export interface TelemetryDataPoint {
  timestamp: number;
  value: number;
}

export interface TelemetryStream {
  id: string;
  name: string;
  unit: string;
  currentValue: number;
  status: 'nominal' | 'warning' | 'critical';
  data: TelemetryDataPoint[];
  min: number;
  max: number;
  threshold?: { warning: number; critical: number };
}

export interface SavedTranscription {
  id: string;
  timestamp: string;
  speakerId: string;
  rawText: string;
  confidence: number;
  isFinal: boolean;
}

export interface Session {
  id: string;
  name: string;
  description: string;
  summary?: string;
  startTime: Date;
  endTime?: Date;
  status: 'active' | 'paused' | 'completed';
  operators: Operator[];
  logCount: number;
  telemetryStreams: number;
  testbed: string;
  transcriptions?: SavedTranscription[];
}

export type NoteType = 'observation' | 'command' | 'system';

export interface BackendNote {
  id: string;
  session_id: string;
  timestamp: string;
  speaker: string | null;
  content: string;
  type: NoteType;
  tags: string[];
  telemetry_snapshot: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

/** Backend structure note (timestamps: ISO 8601 with timezone, e.g. …+00:00). */
export type StructureTestSummaryStatus =
  | 'pending'
  | 'generating'
  | 'ready'
  | 'skipped'
  | 'error';

export interface StructureNoteTestSummary {
  status: StructureTestSummaryStatus;
  generated_at: string | null;
  content_markdown: string;
  error?: string | null;
}

export interface StructureNoteAnomaly {
  id: string;
  recorded_at: string;
  user_utterance_raw: string;
  title: string;
  description: string;
  severity: 'info' | 'low' | 'med' | 'high';
  merge_of?: string[];
  related_telemetry_refs?: { scenario?: string | null; log?: string | null; time?: string | null }[];
  known_pattern_id?: string | null;
}

export interface StructureNoteDetailParagraph {
  id: string;
  updated_at: string;
  time_anchor: string;
  bullet_markdown: string;
  source_transcript_excerpt: string;
  source_task_ids?: string[];
}

export interface StructureNoteDocument {
  schema_version: string;
  session_id: string;
  updated_at: string;
  telemetry_time_format: string;
  test_summary: StructureNoteTestSummary;
  anomalies: StructureNoteAnomaly[];
  detail_notes: { paragraphs: StructureNoteDetailParagraph[] };
}

export interface Document {
  id: string;
  name: string;
  type: 'manual' | 'procedure' | 'specification' | 'design-doc';
  uploadDate: Date;
  size: string;
  status: 'indexed' | 'processing' | 'error';
  pages?: number;
}

export interface VoiceCommand {
  id: string;
  timestamp: Date;
  command: string;
  status: 'recognized' | 'processing' | 'executed' | 'failed';
  response?: string;
}

export interface SystemStats {
  activeSessions: number;
  totalLogs: number;
  avgLatency: number;
  wordErrorRate: number;
  uptime: string;
  activeStreams: number;
}
