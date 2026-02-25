import type {
  Operator,
  TranscriptionEntry,
  LogEntry,
  TelemetryStream,
  Session,
  Document,
  VoiceCommand,
  SystemStats,
} from '../types';

export const operators: Operator[] = [
  { id: 'op1', name: 'Dr. Sarah Chen', role: 'Lead Operator', color: '#00d4ff', avatarInitials: 'SC' },
  { id: 'op2', name: 'Marcus Rivera', role: 'Systems Engineer', color: '#00e676', avatarInitials: 'MR' },
  { id: 'op3', name: 'Dr. James Park', role: 'Telemetry Specialist', color: '#b388ff', avatarInitials: 'JP' },
];

const now = new Date();
const t = (minutesAgo: number) => new Date(now.getTime() - minutesAgo * 60000);

export const transcriptionEntries: TranscriptionEntry[] = [
  {
    id: 'tr1',
    timestamp: t(12),
    operatorId: 'op1',
    rawText: 'Initiating arm calibration sequence for joint three. Setting torque limit to forty-five newton meters.',
    confidence: 0.94,
  },
  {
    id: 'tr2',
    timestamp: t(11),
    operatorId: 'op2',
    rawText: 'Confirmed. Telemetry shows joint three is responding. Current temperature is thirty-two degrees Celsius on the actuator.',
    confidence: 0.91,
  },
  {
    id: 'tr3',
    timestamp: t(9),
    operatorId: 'op1',
    rawText: 'ASTRA, log the current voltage on channel seven.',
    confidence: 0.97,
  },
  {
    id: 'tr4',
    timestamp: t(8),
    operatorId: 'op3',
    rawText: 'I am seeing some oscillation in the IMU readings. Might be a grounding issue. Let me check the connector.',
    confidence: 0.88,
  },
  {
    id: 'tr5',
    timestamp: t(6),
    operatorId: 'op2',
    rawText: 'Switching to manual control mode for the gripper subsystem. Autonomous mode disabled.',
    confidence: 0.93,
  },
  {
    id: 'tr6',
    timestamp: t(4),
    operatorId: 'op1',
    rawText: 'The calibration is looking good. Joint three accuracy is within zero point five degrees. Moving on to joint four.',
    confidence: 0.95,
  },
  {
    id: 'tr7',
    timestamp: t(2),
    operatorId: 'op3',
    rawText: 'Grounding issue confirmed on the IMU. Replacing connector cable now. IMU readings should stabilize in about two minutes.',
    confidence: 0.89,
  },
  {
    id: 'tr8',
    timestamp: t(0.5),
    operatorId: 'op1',
    rawText: 'ASTRA, mark this as an anomaly. The arm encoder on joint four is showing intermittent dropouts.',
    confidence: 0.96,
    isProcessing: true,
  },
];

export const logEntries: LogEntry[] = [
  {
    id: 'log1',
    timestamp: t(12),
    category: 'procedure',
    title: 'Arm Calibration Initiated - Joint 3',
    content: 'Operator initiated calibration sequence for robotic arm Joint 3. Torque limit set to 45 N·m as per procedure TP-2024-ARM-003.',
    operatorId: 'op1',
    tags: ['calibration', 'joint-3', 'arm'],
    isAIGenerated: true,
    severity: 'info',
  },
  {
    id: 'log2',
    timestamp: t(11),
    category: 'measurement',
    title: 'Joint 3 Actuator Temperature Nominal',
    content: 'Joint 3 actuator temperature reading: 32°C. Within nominal operating range (15°C - 65°C). Telemetry confirmation received.',
    operatorId: 'op2',
    tags: ['temperature', 'joint-3', 'nominal'],
    telemetryRef: 'tel_temp_j3',
    isAIGenerated: true,
    severity: 'success',
  },
  {
    id: 'log3',
    timestamp: t(9),
    category: 'voice-command',
    title: 'Voltage Logged - Channel 7',
    content: 'Voice command executed: Logged voltage on Channel 7. Current reading: 24.3V (nominal range: 22V - 26V).',
    operatorId: 'op1',
    tags: ['voltage', 'channel-7', 'voice-command'],
    telemetryRef: 'tel_volt_ch7',
    isAIGenerated: true,
    severity: 'info',
  },
  {
    id: 'log4',
    timestamp: t(8),
    category: 'anomaly',
    title: 'IMU Oscillation Detected',
    content: 'Unexpected oscillation observed in IMU sensor readings. Suspected root cause: grounding issue at the IMU connector interface. Investigation initiated.',
    operatorId: 'op3',
    tags: ['IMU', 'oscillation', 'anomaly', 'grounding'],
    isAIGenerated: true,
    severity: 'warning',
  },
  {
    id: 'log5',
    timestamp: t(6),
    category: 'command',
    title: 'Gripper Mode Changed to Manual',
    content: 'Gripper subsystem switched from autonomous to manual control mode. All automated grip sequences are suspended until further notice.',
    operatorId: 'op2',
    tags: ['gripper', 'manual-mode', 'control'],
    isAIGenerated: true,
    severity: 'info',
  },
  {
    id: 'log6',
    timestamp: t(4),
    category: 'observation',
    title: 'Joint 3 Calibration Complete',
    content: 'Joint 3 calibration completed successfully. Positional accuracy measured at ±0.5°, meeting acceptance criteria (±1.0°). Proceeding to Joint 4 calibration.',
    operatorId: 'op1',
    tags: ['calibration', 'joint-3', 'complete', 'accuracy'],
    isAIGenerated: true,
    severity: 'success',
  },
  {
    id: 'log7',
    timestamp: t(2),
    category: 'anomaly',
    title: 'IMU Grounding Issue - Connector Replaced',
    content: 'Grounding issue on IMU confirmed. Faulty connector cable identified and replacement initiated. Expected stabilization time: ~2 minutes. Ref: Anomaly Log #4.',
    operatorId: 'op3',
    tags: ['IMU', 'grounding', 'repair', 'connector'],
    isAIGenerated: true,
    severity: 'warning',
  },
];

function generateTelemetryData(
  baseValue: number,
  variance: number,
  points: number
): { timestamp: number; value: number }[] {
  const data = [];
  const start = now.getTime() - points * 5000;
  for (let i = 0; i < points; i++) {
    data.push({
      timestamp: start + i * 5000,
      value: baseValue + (Math.random() - 0.5) * variance * 2,
    });
  }
  return data;
}

export const telemetryStreams: TelemetryStream[] = [
  {
    id: 'tel_volt_ch7',
    name: 'Voltage Ch.7',
    unit: 'V',
    currentValue: 24.3,
    status: 'nominal',
    data: generateTelemetryData(24.3, 0.5, 120),
    min: 22,
    max: 26,
    threshold: { warning: 25, critical: 26 },
  },
  {
    id: 'tel_temp_j3',
    name: 'Temp Joint 3',
    unit: '°C',
    currentValue: 32.1,
    status: 'nominal',
    data: generateTelemetryData(32, 2, 120),
    min: 15,
    max: 65,
    threshold: { warning: 55, critical: 65 },
  },
  {
    id: 'tel_torque_j3',
    name: 'Torque Joint 3',
    unit: 'N·m',
    currentValue: 44.8,
    status: 'nominal',
    data: generateTelemetryData(44, 3, 120),
    min: 0,
    max: 60,
    threshold: { warning: 50, critical: 55 },
  },
  {
    id: 'tel_imu_accel',
    name: 'IMU Accel X',
    unit: 'm/s²',
    currentValue: 0.12,
    status: 'warning',
    data: generateTelemetryData(0.1, 0.15, 120),
    min: -2,
    max: 2,
    threshold: { warning: 0.5, critical: 1.0 },
  },
  {
    id: 'tel_current_arm',
    name: 'Arm Current',
    unit: 'A',
    currentValue: 3.7,
    status: 'nominal',
    data: generateTelemetryData(3.5, 0.8, 120),
    min: 0,
    max: 10,
    threshold: { warning: 7, critical: 9 },
  },
  {
    id: 'tel_encoder_j4',
    name: 'Encoder J4',
    unit: 'deg',
    currentValue: 127.3,
    status: 'warning',
    data: generateTelemetryData(127, 5, 120),
    min: 0,
    max: 360,
  },
];

export const sessions: Session[] = [
  {
    id: 'sess1',
    name: 'ARM-CAL-2026-042',
    description: 'Robotic arm calibration sequence - Full joint sweep with torque verification',
    startTime: t(45),
    status: 'active',
    operators: [operators[0], operators[1], operators[2]],
    logCount: 7,
    telemetryStreams: 6,
    testbed: 'Mars Rover Testbed Alpha',
  },
  {
    id: 'sess2',
    name: 'MOB-NAV-2026-041',
    description: 'Mobility subsystem navigation test over simulated terrain',
    startTime: t(180),
    endTime: t(60),
    status: 'completed',
    operators: [operators[0], operators[2]],
    logCount: 23,
    telemetryStreams: 8,
    testbed: 'Mars Yard',
  },
  {
    id: 'sess3',
    name: 'GRIP-AUT-2026-040',
    description: 'Gripper autonomous sample collection test',
    startTime: t(300),
    endTime: t(210),
    status: 'completed',
    operators: [operators[1]],
    logCount: 15,
    telemetryStreams: 4,
    testbed: 'Sample Handling Testbed',
  },
  {
    id: 'sess4',
    name: 'COMM-RNG-2026-039',
    description: 'Communication range test with simulated orbital relay',
    startTime: t(1440),
    endTime: t(1380),
    status: 'completed',
    operators: [operators[0], operators[1]],
    logCount: 31,
    telemetryStreams: 3,
    testbed: 'Comms Lab B',
  },
];

export const documents: Document[] = [
  {
    id: 'doc1',
    name: 'Robotic Arm Operations Manual v3.2',
    type: 'manual',
    uploadDate: t(10080),
    size: '12.4 MB',
    status: 'indexed',
    pages: 234,
  },
  {
    id: 'doc2',
    name: 'TP-2024-ARM-003: Joint Calibration Procedure',
    type: 'procedure',
    uploadDate: t(4320),
    size: '2.1 MB',
    status: 'indexed',
    pages: 18,
  },
  {
    id: 'doc3',
    name: 'Mars Rover Testbed Alpha - System Specification',
    type: 'specification',
    uploadDate: t(20160),
    size: '45.8 MB',
    status: 'indexed',
    pages: 512,
  },
  {
    id: 'doc4',
    name: 'IMU Sensor Integration Design Document',
    type: 'design-doc',
    uploadDate: t(2880),
    size: '8.3 MB',
    status: 'indexed',
    pages: 87,
  },
  {
    id: 'doc5',
    name: 'Gripper Subsystem Safety Procedures',
    type: 'procedure',
    uploadDate: t(720),
    size: '1.8 MB',
    status: 'processing',
    pages: 12,
  },
];

export const voiceCommands: VoiceCommand[] = [
  {
    id: 'vc1',
    timestamp: t(9),
    command: 'ASTRA, log the current voltage on channel seven',
    status: 'executed',
    response: 'Logged voltage on Channel 7: 24.3V',
  },
  {
    id: 'vc2',
    timestamp: t(0.5),
    command: 'ASTRA, mark this as an anomaly',
    status: 'processing',
  },
];

export const systemStats: SystemStats = {
  activeSessions: 1,
  totalLogs: 76,
  avgLatency: 3.2,
  wordErrorRate: 12.4,
  uptime: '14d 7h 23m',
  activeStreams: 7,
};
