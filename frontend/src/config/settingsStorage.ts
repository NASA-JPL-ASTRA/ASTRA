import type { DualMicConfig } from './audioInputs';
import { loadDualMicConfig, notifyAudioSettingsChanged, saveDualMicConfig } from './audioInputs';

const GENERAL_SETTINGS_KEY = 'astra.settings.general';

export interface GeneralSettings {
  language: string;
  region: string;
  dateFormat: string;
  theme: string;
  use24Hour: boolean;
  autoTranscribe: boolean;
  noiseSuppression: boolean;
  voiceCommands: boolean;
}

const defaultGeneral: GeneralSettings = {
  language: 'en',
  region: 'America/Los_Angeles',
  dateFormat: 'MM/DD/YYYY',
  theme: 'dark',
  use24Hour: false,
  autoTranscribe: true,
  noiseSuppression: true,
  voiceCommands: true,
};

export function loadGeneralSettings(): GeneralSettings {
  if (typeof window === 'undefined') return { ...defaultGeneral };
  try {
    const raw = window.localStorage.getItem(GENERAL_SETTINGS_KEY);
    if (!raw) return { ...defaultGeneral };
    return { ...defaultGeneral, ...JSON.parse(raw) };
  } catch {
    return { ...defaultGeneral };
  }
}

export function saveGeneralSettings(settings: GeneralSettings): void {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(GENERAL_SETTINGS_KEY, JSON.stringify(settings));
}

export interface PersistedSettingsSnapshot {
  dualMic: DualMicConfig;
  general: GeneralSettings;
}

export function persistSettingsSnapshot(snapshot: PersistedSettingsSnapshot): void {
  saveDualMicConfig(snapshot.dualMic);
  saveGeneralSettings(snapshot.general);
  notifyAudioSettingsChanged();
}

export function loadSettingsSnapshot(): PersistedSettingsSnapshot {
  return {
    dualMic: loadDualMicConfig(),
    general: loadGeneralSettings(),
  };
}

export const defaultDualMicConfig = (): DualMicConfig => loadDualMicConfig();

export function resetToDefaultSettings(): PersistedSettingsSnapshot {
  const dualMic: DualMicConfig = {
    enabled: true,
    mic1DeviceId: '',
    mic2DeviceId: '',
  };
  const general = { ...defaultGeneral };
  persistSettingsSnapshot({ dualMic, general });
  return { dualMic, general };
}
