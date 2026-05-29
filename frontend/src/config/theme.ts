import { loadGeneralSettings } from './settingsStorage';

export type ThemePreference = 'dark' | 'light' | 'system';
export type ResolvedTheme = 'dark' | 'light';

const THEME_STORAGE_EVENT = 'astra:theme-changed';

export function normalizeThemePreference(value: unknown): ThemePreference {
  return value === 'light' || value === 'system' || value === 'dark' ? value : 'dark';
}

export function getSystemTheme(): ResolvedTheme {
  if (typeof window === 'undefined' || !window.matchMedia) return 'dark';
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

export function resolveTheme(preference: ThemePreference): ResolvedTheme {
  return preference === 'system' ? getSystemTheme() : preference;
}

export function applyThemePreference(preference: ThemePreference): ResolvedTheme {
  const resolvedTheme = resolveTheme(preference);
  if (typeof document !== 'undefined') {
    document.documentElement.dataset.theme = resolvedTheme;
    document.documentElement.style.colorScheme = resolvedTheme;
  }
  return resolvedTheme;
}

export function applyStoredTheme(): ResolvedTheme {
  return applyThemePreference(normalizeThemePreference(loadGeneralSettings().theme));
}

export function notifyThemeChanged(): void {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new Event(THEME_STORAGE_EVENT));
}

export function subscribeToThemeChanges(onChange: () => void): () => void {
  if (typeof window === 'undefined') return () => {};

  const media = window.matchMedia?.('(prefers-color-scheme: light)');
  const handleStorage = (event: StorageEvent) => {
    if (event.key === 'astra.settings.general') onChange();
  };
  const handleLocalThemeChange = () => onChange();
  const handleSystemThemeChange = () => {
    if (normalizeThemePreference(loadGeneralSettings().theme) === 'system') {
      onChange();
    }
  };

  window.addEventListener('storage', handleStorage);
  window.addEventListener(THEME_STORAGE_EVENT, handleLocalThemeChange);
  media?.addEventListener('change', handleSystemThemeChange);

  return () => {
    window.removeEventListener('storage', handleStorage);
    window.removeEventListener(THEME_STORAGE_EVENT, handleLocalThemeChange);
    media?.removeEventListener('change', handleSystemThemeChange);
  };
}
