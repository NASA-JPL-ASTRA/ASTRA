import { useCallback, useEffect, useRef, useState } from 'react';
import {
  CheckCircle2,
  Loader2,
  Mic,
  Palette,
  RotateCcw,
  Save,
} from 'lucide-react';
import { useStore } from '../store/useStore';
import {
  STT_MODEL_OPTIONS,
  getSttModelLabel,
} from '../config/sttModels';
import {
  ensureAudioInputLabels,
  loadDualMicConfig,
  saveDualMicConfig,
  notifyAudioSettingsChanged,
  type DualMicConfig,
} from '../config/audioInputs';
import {
  loadGeneralSettings,
  saveGeneralSettings,
} from '../config/settingsStorage';
import {
  applyThemePreference,
  notifyThemeChanged,
  type ThemePreference,
} from '../config/theme';

function Toggle({ enabled, onChange }: { enabled: boolean; onChange: () => void }) {
  return (
    <button
      type="button"
      onClick={onChange}
      className={`relative h-5 w-10 rounded-full transition-colors ${
        enabled ? 'bg-accent-cyan' : 'bg-space-border'
      }`}
    >
      <div
        className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform ${
          enabled ? 'translate-x-5.5' : 'translate-x-0.5'
        }`}
      />
    </button>
  );
}

type SaveStatus = 'idle' | 'saving' | 'saved';

const defaultDualMicConfig: DualMicConfig = {
  enabled: true,
  mic1DeviceId: '',
  mic2DeviceId: '',
};

export default function SettingsPage() {
  const { selectedSttModel, setSelectedSttModel } = useStore();

  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle');
  const saveTimerRef = useRef<ReturnType<typeof window.setTimeout> | null>(null);

  const [theme, setTheme] = useState<ThemePreference>(() => loadGeneralSettings().theme);
  const [dualMic, setDualMic] = useState<DualMicConfig>(() => loadDualMicConfig());
  const [audioInputs, setAudioInputs] = useState<MediaDeviceInfo[]>([]);
  const [devicesLoading, setDevicesLoading] = useState(false);

  const refreshAudioDevices = useCallback(async () => {
    setDevicesLoading(true);
    try {
      const devices = await ensureAudioInputLabels();
      setAudioInputs(devices);
    } finally {
      setDevicesLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshAudioDevices();
  }, [refreshAudioDevices]);

  useEffect(() => {
    return () => {
      if (saveTimerRef.current !== null) {
        window.clearTimeout(saveTimerRef.current);
      }
    };
  }, []);

  const markDirty = () => {
    if (saveStatus === 'saved') setSaveStatus('idle');
  };

  const updateDualMic = (patch: Partial<DualMicConfig>) => {
    setDualMic((prev) => ({ ...prev, ...patch }));
    markDirty();
  };

  const showSavedState = () => {
    window.setTimeout(() => {
      setSaveStatus('saved');
      saveTimerRef.current = window.setTimeout(() => {
        setSaveStatus('idle');
        saveTimerRef.current = null;
      }, 3200);
    }, 280);
  };

  const handleSaveChanges = () => {
    if (saveTimerRef.current !== null) {
      window.clearTimeout(saveTimerRef.current);
    }
    setSaveStatus('saving');

    setSelectedSttModel(selectedSttModel);
    saveGeneralSettings({ theme });
    saveDualMicConfig(dualMic);
    notifyAudioSettingsChanged();
    applyThemePreference(theme);
    notifyThemeChanged();

    showSavedState();
  };

  const handleResetDefaults = () => {
    if (saveTimerRef.current !== null) {
      window.clearTimeout(saveTimerRef.current);
      saveTimerRef.current = null;
    }

    setTheme('dark');
    setDualMic(defaultDualMicConfig);
    saveGeneralSettings({ theme: 'dark' });
    saveDualMicConfig(defaultDualMicConfig);
    notifyAudioSettingsChanged();
    applyThemePreference('dark');
    notifyThemeChanged();
    setSaveStatus('saved');
    saveTimerRef.current = window.setTimeout(() => setSaveStatus('idle'), 3200);
  };

  const isSaving = saveStatus === 'saving';
  const isSaved = saveStatus === 'saved';

  return (
    <div className="relative space-y-6 p-6 animate-fade-in">
      {isSaved && (
        <div
          className="fixed right-6 top-20 z-50 animate-slide-up"
          role="status"
          aria-live="polite"
        >
          <div className="flex items-center gap-3 rounded-xl border border-accent-green/35 bg-space-panel px-5 py-3.5 shadow-2xl shadow-accent-green/10">
            <CheckCircle2 className="h-5 w-5 shrink-0 text-accent-green" />
            <div>
              <p className="text-sm font-semibold text-text-primary">Settings saved</p>
              <p className="mt-0.5 text-xs text-text-secondary">
                Theme, STT model, and microphone preferences stored in this browser.
              </p>
            </div>
          </div>
        </div>
      )}

      <div>
        <h1 className="text-2xl font-bold text-text-primary">Settings</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Configure the settings currently wired into ASTRA.
        </p>
      </div>

      <div className="rounded-xl border border-space-border bg-space-panel p-6">
        <div className="space-y-8">
          <section className="space-y-5">
            <div className="flex items-center gap-3 border-b border-space-border pb-4">
              <Palette className="h-5 w-5 text-accent-cyan" />
              <div>
                <h2 className="text-lg font-semibold text-text-primary">Appearance</h2>
                <p className="text-xs text-text-muted">Interface theme</p>
              </div>
            </div>

            <div className="flex items-center justify-between gap-6">
              <div>
                <p className="text-sm font-medium text-text-primary">Theme</p>
                <p className="mt-0.5 text-xs text-text-muted">Choose the app color mode</p>
              </div>
              <select
                value={theme}
                onChange={(e) => {
                  const nextTheme = e.target.value as ThemePreference;
                  setTheme(nextTheme);
                  applyThemePreference(nextTheme);
                  markDirty();
                }}
                className="rounded-lg border border-space-border bg-space-card px-3 py-2 text-sm text-text-primary focus:border-accent-cyan/50 focus:outline-none"
              >
                <option value="dark">Dark (Space Control)</option>
                <option value="light">Light</option>
                <option value="system">System Default</option>
              </select>
            </div>
          </section>

          <section className="space-y-5">
            <div className="flex items-center gap-3 border-b border-space-border pb-4">
              <Mic className="h-5 w-5 text-accent-cyan" />
              <div>
                <h2 className="text-lg font-semibold text-text-primary">Audio & Speech</h2>
                <p className="text-xs text-text-muted">Speech-to-text model and microphone routing</p>
              </div>
            </div>

            <div className="flex items-center justify-between gap-6">
              <div>
                <p className="text-sm font-medium text-text-primary">Speech-to-Text Model</p>
                <p className="mt-0.5 text-xs text-text-muted">
                  Applied to new dictation uploads and voice telemetry queries
                </p>
              </div>
              <select
                value={selectedSttModel}
                onChange={(e) => {
                  setSelectedSttModel(e.target.value);
                  markDirty();
                }}
                className="rounded-lg border border-space-border bg-space-card px-3 py-2 text-sm text-text-primary focus:border-accent-cyan/50 focus:outline-none"
              >
                {STT_MODEL_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="rounded-lg border border-space-border bg-space-card/60 px-4 py-3">
              <p className="text-xs font-medium text-text-primary">
                Active model: {getSttModelLabel(selectedSttModel)}
              </p>
              <p className="mt-1 text-xs text-text-muted">
                The selected model is stored locally in this browser.
              </p>
            </div>

            <div className="rounded-lg border border-space-border bg-space-card/60 px-4 py-3">
              <p className="text-xs font-medium text-text-primary">Transcription language</p>
              <p className="mt-1 text-xs leading-relaxed text-text-muted">
                Live STT language is set in <span className="font-mono">backend/.env</span> via{' '}
                <span className="font-mono">OPENAI_STT_LANGUAGE=en</span>. Restart the backend
                after changing it. Leave <span className="font-mono">OPENAI_STT_PROMPT</span>{' '}
                empty unless you need domain words such as channel names.
              </p>
            </div>

            <div className="space-y-3 rounded-lg border border-accent-cyan/20 bg-accent-cyan/5 px-4 py-3">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-text-primary">
                    VoiceMeeter Banana - dual microphone
                  </p>
                  <p className="mt-0.5 text-xs leading-relaxed text-text-muted">
                    Route Input 1 to A1 and Input 2 to B1. Both streams record in
                    parallel and are labeled Microphone 1 / 2.
                  </p>
                </div>
                <Toggle
                  enabled={dualMic.enabled}
                  onChange={() => updateDualMic({ enabled: !dualMic.enabled })}
                />
              </div>

              {dualMic.enabled && (
                <>
                  <div className="flex justify-end">
                    <button
                      type="button"
                      onClick={() => void refreshAudioDevices()}
                      disabled={devicesLoading}
                      className="text-xs text-accent-cyan hover:underline disabled:opacity-50"
                    >
                      {devicesLoading ? 'Scanning...' : 'Rescan input devices'}
                    </button>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-text-secondary">
                      Microphone 1 (VoiceMeeter A1 output)
                    </label>
                    <select
                      value={dualMic.mic1DeviceId}
                      onChange={(e) => updateDualMic({ mic1DeviceId: e.target.value })}
                      className="mt-1 w-full rounded-lg border border-space-border bg-space-card px-3 py-2 text-sm text-text-primary focus:border-accent-cyan/50 focus:outline-none"
                    >
                      <option value="">Select device</option>
                      {audioInputs.map((device) => (
                        <option key={device.deviceId} value={device.deviceId}>
                          {device.label || device.deviceId}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-text-secondary">
                      Microphone 2 (VoiceMeeter B1 output)
                    </label>
                    <select
                      value={dualMic.mic2DeviceId}
                      onChange={(e) => updateDualMic({ mic2DeviceId: e.target.value })}
                      className="mt-1 w-full rounded-lg border border-space-border bg-space-card px-3 py-2 text-sm text-text-primary focus:border-accent-cyan/50 focus:outline-none"
                    >
                      <option value="">Select device</option>
                      {audioInputs.map((device) => (
                        <option key={device.deviceId} value={device.deviceId}>
                          {device.label || device.deviceId}
                        </option>
                      ))}
                    </select>
                  </div>
                </>
              )}
            </div>
          </section>
        </div>

        <div className="mt-6 flex flex-col items-end gap-3 border-t border-space-border pt-6">
          {isSaved && (
            <p className="flex items-center gap-2 text-xs font-medium text-accent-green animate-fade-in">
              <CheckCircle2 className="h-3.5 w-3.5" />
              All changes saved locally
            </p>
          )}
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleResetDefaults}
              disabled={isSaving}
              className="flex items-center gap-2 px-4 py-2 text-sm text-text-secondary transition-colors hover:text-text-primary disabled:opacity-50"
            >
              <RotateCcw className="h-4 w-4" />
              Reset to Defaults
            </button>
            <button
              type="button"
              onClick={handleSaveChanges}
              disabled={isSaving}
              className={`flex min-w-[9.5rem] items-center justify-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-all duration-300 disabled:opacity-70 ${
                isSaved
                  ? 'scale-[1.02] border-accent-green/35 bg-accent-green/15 text-accent-green'
                  : isSaving
                    ? 'border-accent-cyan/25 bg-accent-cyan/10 text-accent-cyan'
                    : 'border-accent-cyan/30 bg-accent-cyan/15 text-accent-cyan hover:bg-accent-cyan/25'
              }`}
            >
              {isSaving ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : isSaved ? (
                <>
                  <CheckCircle2 className="h-4 w-4" />
                  Saved
                </>
              ) : (
                <>
                  <Save className="h-4 w-4" />
                  Save Changes
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
