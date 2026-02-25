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
