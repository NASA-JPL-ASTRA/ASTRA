import type { ThemePreference } from './theme';

const GENERAL_SETTINGS_KEY = 'astra.settings.general';

export interface GeneralSettings {
  theme: ThemePreference;
}

const defaultGeneral: GeneralSettings = {
  theme: 'system',
};

export function loadGeneralSettings(): GeneralSettings {
  if (typeof window === 'undefined') return { ...defaultGeneral };
  try {
    const raw = window.localStorage.getItem(GENERAL_SETTINGS_KEY);
    if (!raw) return { ...defaultGeneral };
    const parsed = { ...defaultGeneral, ...JSON.parse(raw) };
    if (parsed.theme !== 'dark' && parsed.theme !== 'light' && parsed.theme !== 'system') {
      parsed.theme = defaultGeneral.theme;
    }
    return { theme: parsed.theme };
  } catch {
    return { ...defaultGeneral };
  }
}

export function saveGeneralSettings(settings: GeneralSettings): void {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(GENERAL_SETTINGS_KEY, JSON.stringify(settings));
}
