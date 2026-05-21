/** VoiceMeeter Banana: bind each virtual output (A1 / B1) to a browser recording device. */

export const MIC_1_SPEAKER_ID = 'speaker_mic_1';
export const MIC_2_SPEAKER_ID = 'speaker_mic_2';

export const MIC_1_SOURCE = 'mic_1' as const;
export const MIC_2_SOURCE = 'mic_2' as const;

export type MicSourceId = typeof MIC_1_SOURCE | typeof MIC_2_SOURCE;

export const MIC_SOURCE_LABELS: Record<MicSourceId, string> = {
  [MIC_1_SOURCE]: 'Microphone 1',
  [MIC_2_SOURCE]: 'Microphone 2',
};

const DUAL_MIC_STORAGE_KEY = 'astra.dualMic';

export const AUDIO_SETTINGS_CHANGED = 'astra-audio-settings-changed';

export function notifyAudioSettingsChanged(): void {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new Event(AUDIO_SETTINGS_CHANGED));
}

export interface DualMicConfig {
  enabled: boolean;
  mic1DeviceId: string;
  mic2DeviceId: string;
}

const defaultDualMicConfig: DualMicConfig = {
  enabled: true,
  mic1DeviceId: '',
  mic2DeviceId: '',
};

export function loadDualMicConfig(): DualMicConfig {
  if (typeof window === 'undefined') return { ...defaultDualMicConfig };
  try {
    const raw = window.localStorage.getItem(DUAL_MIC_STORAGE_KEY);
    if (!raw) return { ...defaultDualMicConfig };
    const parsed = JSON.parse(raw) as Partial<DualMicConfig>;
    return {
      enabled: parsed.enabled ?? defaultDualMicConfig.enabled,
      mic1DeviceId: parsed.mic1DeviceId ?? '',
      mic2DeviceId: parsed.mic2DeviceId ?? '',
    };
  } catch {
    return { ...defaultDualMicConfig };
  }
}

export function saveDualMicConfig(config: DualMicConfig): void {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(DUAL_MIC_STORAGE_KEY, JSON.stringify(config));
}

export function speakerIdForMicSource(source: MicSourceId): string {
  return source === MIC_1_SOURCE ? MIC_1_SPEAKER_ID : MIC_2_SPEAKER_ID;
}

export function micSourceFromSpeakerId(speakerId: string): MicSourceId | null {
  if (speakerId === MIC_1_SPEAKER_ID) return MIC_1_SOURCE;
  if (speakerId === MIC_2_SPEAKER_ID) return MIC_2_SOURCE;
  return null;
}

export async function listAudioInputDevices(): Promise<MediaDeviceInfo[]> {
  if (!navigator.mediaDevices?.enumerateDevices) return [];
  const devices = await navigator.mediaDevices.enumerateDevices();
  return devices.filter((d) => d.kind === 'audioinput');
}

/** Prompt for mic permission so device labels are populated (Chrome). */
export async function ensureAudioInputLabels(): Promise<MediaDeviceInfo[]> {
  if (!navigator.mediaDevices?.getUserMedia) {
    return listAudioInputDevices();
  }
  let stream: MediaStream | null = null;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch {
    // Still return enumerate results (labels may be empty).
  } finally {
    stream?.getTracks().forEach((t) => t.stop());
  }
  return listAudioInputDevices();
}

const MIC_SPEAKER_COLORS: Record<MicSourceId, string> = {
  [MIC_1_SOURCE]: '#00d4ff',
  [MIC_2_SOURCE]: '#00e676',
};

export interface ConnectedMicInfo {
  count: number;
  sources: MicSourceId[];
  deviceIds: Partial<Record<MicSourceId, string>>;
}

export function micSpeakersForSources(sources: MicSourceId[]) {
  return sources.map((source) => ({
    id: speakerIdForMicSource(source),
    name: MIC_SOURCE_LABELS[source],
    color: MIC_SPEAKER_COLORS[source],
  }));
}

export function defaultMicSpeakers() {
  return micSpeakersForSources([MIC_1_SOURCE, MIC_2_SOURCE]);
}

async function canOpenAudioInput(deviceId: string): Promise<boolean> {
  if (!navigator.mediaDevices?.getUserMedia) return false;
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: deviceId
        ? {
            deviceId: { exact: deviceId },
            echoCancellation: false,
            noiseSuppression: false,
            autoGainControl: false,
            channelCount: 1,
          }
        : {
            echoCancellation: false,
            noiseSuppression: false,
            autoGainControl: false,
            channelCount: 1,
          },
    });
    stream.getTracks().forEach((t) => t.stop());
    return true;
  } catch {
    return false;
  }
}

/** Probe configured devices and return how many mics are actually available. */
export async function detectConnectedMics(
  config?: DualMicConfig,
): Promise<ConnectedMicInfo> {
  const cfg = config ?? loadDualMicConfig();

  if (!cfg.enabled) {
    return {
      count: 1,
      sources: [MIC_1_SOURCE],
      deviceIds: { [MIC_1_SOURCE]: '' },
    };
  }

  const devices = await listAudioInputDevices();
  const knownIds = new Set(devices.map((d) => d.deviceId).filter(Boolean));

  const sources: MicSourceId[] = [];
  const deviceIds: Partial<Record<MicSourceId, string>> = {};

  const tryAdd = async (source: MicSourceId, deviceId: string) => {
    if (!deviceId || sources.includes(source)) return;
    if (knownIds.size > 0 && !knownIds.has(deviceId)) return;
    if (!(await canOpenAudioInput(deviceId))) return;
    sources.push(source);
    deviceIds[source] = deviceId;
  };

  await tryAdd(MIC_1_SOURCE, cfg.mic1DeviceId);
  await tryAdd(MIC_2_SOURCE, cfg.mic2DeviceId);

  // Labels may be empty before permission — probe configured IDs without enumerate filter.
  if (sources.length === 0) {
    for (const { source, deviceId } of [
      { source: MIC_1_SOURCE, deviceId: cfg.mic1DeviceId },
      { source: MIC_2_SOURCE, deviceId: cfg.mic2DeviceId },
    ] as const) {
      if (!deviceId || sources.includes(source)) continue;
      if (!(await canOpenAudioInput(deviceId))) continue;
      sources.push(source);
      deviceIds[source] = deviceId;
    }
  }

  if (sources.length === 0 && (await canOpenAudioInput(''))) {
    return {
      count: 1,
      sources: [MIC_1_SOURCE],
      deviceIds: { [MIC_1_SOURCE]: '' },
    };
  }

  return { count: sources.length, sources, deviceIds };
}
