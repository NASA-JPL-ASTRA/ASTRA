import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Mic,
  Brain,
  Activity,
  Database,
  Shield,
  Globe,
  Sliders,
  Save,
  RotateCcw,
  User,
  LogOut,
  LogIn,
  Languages,
  MapPin,
  Clock,
  Palette,
  CheckCircle2,
  Loader2,
} from 'lucide-react';
import { useStore } from '../store/useStore';
import {
  STT_MODEL_OPTIONS,
  getSttModelLabel,
} from '../config/sttModels';
import {
  ensureAudioInputLabels,
  loadDualMicConfig,
  type DualMicConfig,
} from '../config/audioInputs';
import {
  loadGeneralSettings,
  persistSettingsSnapshot,
  resetToDefaultSettings,
} from '../config/settingsStorage';

interface SettingGroup {
  id: string;
  icon: typeof Mic;
  label: string;
  description: string;
}

const settingGroups: SettingGroup[] = [
  { id: 'user', icon: User, label: 'User', description: 'Account, login, and logout' },
  { id: 'general', icon: Globe, label: 'General', description: 'Language, region, and display preferences' },
  { id: 'audio', icon: Mic, label: 'Audio & Speech', description: 'Microphone, STT model, and voice commands' },
  { id: 'ai', icon: Brain, label: 'AI & LLM', description: 'Language model, RAG, and prompt configuration' },
  { id: 'telemetry', icon: Activity, label: 'Telemetry', description: 'Data streams, refresh rates, and thresholds' },
  { id: 'storage', icon: Database, label: 'Storage & Database', description: 'Log retention, export, and backup' },
  { id: 'security', icon: Shield, label: 'Security', description: 'Permissions and audit settings' },
];

function Toggle({ enabled, onChange }: { enabled: boolean; onChange: () => void }) {
  return (
    <button
      onClick={onChange}
      className={`relative w-10 h-5 rounded-full transition-colors ${
        enabled ? 'bg-accent-cyan' : 'bg-space-border'
      }`}
    >
      <div
        className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
          enabled ? 'translate-x-5.5' : 'translate-x-0.5'
        }`}
      />
    </button>
  );
}

type SaveStatus = 'idle' | 'saving' | 'saved';

export default function SettingsPage() {
  const [activeGroup, setActiveGroup] = useState('user');
  const { selectedSttModel, setSelectedSttModel } = useStore();

  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle');
  const saveTimerRef = useRef<ReturnType<typeof window.setTimeout> | null>(null);

  // User state
  const [isLoggedIn, setIsLoggedIn] = useState(true);
  const [userName] = useState('Dr. Sarah Chen');
  const [userEmail] = useState('sarah.chen@jpl.nasa.gov');
  const [userRole] = useState('Lead Operator');

  // General state (loaded from localStorage on mount)
  const [language, setLanguage] = useState(() => loadGeneralSettings().language);
  const [region, setRegion] = useState(() => loadGeneralSettings().region);
  const [dateFormat, setDateFormat] = useState(() => loadGeneralSettings().dateFormat);
  const [theme, setTheme] = useState(() => loadGeneralSettings().theme);
  const [use24Hour, setUse24Hour] = useState(() => loadGeneralSettings().use24Hour);

  // Audio state
  const [autoTranscribe, setAutoTranscribe] = useState(
    () => loadGeneralSettings().autoTranscribe,
  );
  const [noiseSuppression, setNoiseSuppression] = useState(
    () => loadGeneralSettings().noiseSuppression,
  );
  const [dualMic, setDualMic] = useState<DualMicConfig>(() => loadDualMicConfig());
  const [audioInputs, setAudioInputs] = useState<MediaDeviceInfo[]>([]);
  const [devicesLoading, setDevicesLoading] = useState(false);
  const [voiceCommands, setVoiceCommands] = useState(
    () => loadGeneralSettings().voiceCommands,
  );

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
    if (activeGroup === 'audio') {
      void refreshAudioDevices();
    }
  }, [activeGroup, refreshAudioDevices]);

  const updateDualMic = (patch: Partial<DualMicConfig>) => {
    setDualMic((prev) => ({ ...prev, ...patch }));
    if (saveStatus === 'saved') setSaveStatus('idle');
  };

  useEffect(() => {
    return () => {
      if (saveTimerRef.current !== null) {
        window.clearTimeout(saveTimerRef.current);
      }
    };
  }, []);

  const handleSaveChanges = () => {
    if (saveTimerRef.current !== null) {
      window.clearTimeout(saveTimerRef.current);
    }
    setSaveStatus('saving');

    setSelectedSttModel(selectedSttModel);
    persistSettingsSnapshot({
      dualMic,
      general: {
        language,
        region,
        dateFormat,
        theme,
        use24Hour,
        autoTranscribe,
        noiseSuppression,
        voiceCommands,
      },
    });

    window.setTimeout(() => {
      setSaveStatus('saved');
      saveTimerRef.current = window.setTimeout(() => {
        setSaveStatus('idle');
        saveTimerRef.current = null;
      }, 3200);
    }, 280);
  };

  const handleResetDefaults = () => {
    if (saveTimerRef.current !== null) {
      window.clearTimeout(saveTimerRef.current);
      saveTimerRef.current = null;
    }
    const defaults = resetToDefaultSettings();
    setDualMic(defaults.dualMic);
    setLanguage(defaults.general.language);
    setRegion(defaults.general.region);
    setDateFormat(defaults.general.dateFormat);
    setTheme(defaults.general.theme);
    setUse24Hour(defaults.general.use24Hour);
    setAutoTranscribe(defaults.general.autoTranscribe);
    setNoiseSuppression(defaults.general.noiseSuppression);
    setVoiceCommands(defaults.general.voiceCommands);
    setSaveStatus('saved');
    saveTimerRef.current = window.setTimeout(() => setSaveStatus('idle'), 3200);
  };

  // AI state
  const [llmModel, setLlmModel] = useState('gpt-4');
  const [ragEnabled, setRagEnabled] = useState(true);

  const isSaving = saveStatus === 'saving';
  const isSaved = saveStatus === 'saved';

  return (
    <div className="relative p-6 space-y-6 animate-fade-in">
      {isSaved && (
        <div
          className="fixed top-20 right-6 z-50 animate-slide-up"
          role="status"
          aria-live="polite"
        >
          <div className="flex items-center gap-3 px-5 py-3.5 bg-space-panel border border-accent-green/35 rounded-xl shadow-2xl shadow-accent-green/10">
            <CheckCircle2 className="w-5 h-5 text-accent-green shrink-0" />
            <div>
              <p className="text-sm font-semibold text-text-primary">Settings saved</p>
              <p className="text-xs text-text-secondary mt-0.5">
                Audio devices, STT model, and preferences stored in this browser.
              </p>
            </div>
          </div>
        </div>
      )}
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Settings</h1>
        <p className="text-sm text-text-secondary mt-1">Configure ASTRA system parameters</p>
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Left - Nav */}
        <div className="col-span-3 space-y-1">
          {settingGroups.map((group) => (
            <button
              key={group.id}
              onClick={() => setActiveGroup(group.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-all ${
                activeGroup === group.id
                  ? 'bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/20'
                  : 'text-text-secondary hover:bg-space-hover hover:text-text-primary border border-transparent'
              }`}
            >
              <group.icon className="w-5 h-5 shrink-0" />
              <div>
                <p className="text-sm font-medium">{group.label}</p>
                <p className="text-[10px] text-text-muted leading-tight">{group.description}</p>
              </div>
            </button>
          ))}
        </div>

        {/* Right - Content */}
        <div className="col-span-9 rounded-xl border border-space-border bg-space-panel p-6">

          {/* ─── User Management ─── */}
          {activeGroup === 'user' && (
            <div className="space-y-6">
              <div className="flex items-center gap-3 pb-4 border-b border-space-border">
                <User className="w-5 h-5 text-accent-cyan" />
                <div>
                  <h2 className="text-lg font-semibold text-text-primary">User Management</h2>
                  <p className="text-xs text-text-muted">Account information and session control</p>
                </div>
              </div>

              {isLoggedIn ? (
                <>
                  {/* User Profile Card */}
                  <div className="flex items-center gap-4 p-4 rounded-xl bg-space-card border border-space-border">
                    <div className="w-14 h-14 rounded-full bg-accent-cyan/15 border-2 border-accent-cyan/30 flex items-center justify-center text-lg font-bold text-accent-cyan">
                      SC
                    </div>
                    <div className="flex-1">
                      <h3 className="text-base font-semibold text-text-primary">{userName}</h3>
                      <p className="text-sm text-text-secondary">{userEmail}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/20">
                          {userRole}
                        </span>
                        <span className="text-[10px] text-accent-green flex items-center gap-1">
                          <div className="w-1.5 h-1.5 rounded-full bg-accent-green" />
                          Online
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Account Details */}
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-text-primary">Display Name</p>
                        <p className="text-xs text-text-muted mt-0.5">Your name shown to other operators</p>
                      </div>
                      <span className="text-sm text-text-secondary">{userName}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-text-primary">Email</p>
                        <p className="text-xs text-text-muted mt-0.5">Associated account email</p>
                      </div>
                      <span className="text-sm text-text-secondary font-mono">{userEmail}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-text-primary">Role</p>
                        <p className="text-xs text-text-muted mt-0.5">Access level and permissions</p>
                      </div>
                      <span className="text-sm text-text-secondary">{userRole}</span>
                    </div>
                  </div>

                  {/* Logout */}
                  <div className="pt-4 border-t border-space-border">
                    <button
                      onClick={() => setIsLoggedIn(false)}
                      className="flex items-center gap-2 px-4 py-2.5 bg-accent-red/10 text-accent-red border border-accent-red/20 rounded-lg text-sm font-medium hover:bg-accent-red/20 transition-all"
                    >
                      <LogOut className="w-4 h-4" />
                      Log Out
                    </button>
                  </div>
                </>
              ) : (
                <>
                  {/* Login Form */}
                  <div className="max-w-sm space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-text-primary mb-1.5">Email</label>
                      <input
                        type="email"
                        placeholder="your.email@jpl.nasa.gov"
                        className="w-full bg-space-card border border-space-border rounded-lg px-3 py-2.5 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-cyan/50 transition-all"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-text-primary mb-1.5">Password</label>
                      <input
                        type="password"
                        placeholder="Enter password"
                        className="w-full bg-space-card border border-space-border rounded-lg px-3 py-2.5 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-cyan/50 transition-all"
                      />
                    </div>
                    <button
                      onClick={() => setIsLoggedIn(true)}
                      className="flex items-center gap-2 px-5 py-2.5 bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30 rounded-lg text-sm font-semibold hover:bg-accent-cyan/25 transition-all w-full justify-center"
                    >
                      <LogIn className="w-4 h-4" />
                      Log In
                    </button>
                    <p className="text-xs text-text-muted text-center">
                      Use your NASA JPL credentials to sign in
                    </p>
                  </div>
                </>
              )}
            </div>
          )}

          {/* ─── General Settings ─── */}
          {activeGroup === 'general' && (
            <div className="space-y-6">
              <div className="flex items-center gap-3 pb-4 border-b border-space-border">
                <Globe className="w-5 h-5 text-accent-cyan" />
                <div>
                  <h2 className="text-lg font-semibold text-text-primary">General Settings</h2>
                  <p className="text-xs text-text-muted">Language, region, and display preferences</p>
                </div>
              </div>

              {/* Language */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Languages className="w-4 h-4 text-text-muted" />
                  <div>
                    <p className="text-sm font-medium text-text-primary">Language</p>
                    <p className="text-xs text-text-muted mt-0.5">Interface and transcription language</p>
                  </div>
                </div>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="bg-space-card border border-space-border rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-cyan/50"
                >
                  <option value="en">English</option>
                  <option value="zh-CN">简体中文</option>
                  <option value="zh-TW">繁體中文</option>
                  <option value="es">Español</option>
                  <option value="ja">日本語</option>
                  <option value="ko">한국어</option>
                  <option value="fr">Français</option>
                  <option value="de">Deutsch</option>
                </select>
              </div>

              {/* Region / Timezone */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <MapPin className="w-4 h-4 text-text-muted" />
                  <div>
                    <p className="text-sm font-medium text-text-primary">Region / Timezone</p>
                    <p className="text-xs text-text-muted mt-0.5">Used for timestamps and local time display</p>
                  </div>
                </div>
                <select
                  value={region}
                  onChange={(e) => setRegion(e.target.value)}
                  className="bg-space-card border border-space-border rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-cyan/50"
                >
                  <option value="America/Los_Angeles">US Pacific (Los Angeles)</option>
                  <option value="America/New_York">US Eastern (New York)</option>
                  <option value="America/Chicago">US Central (Chicago)</option>
                  <option value="America/Denver">US Mountain (Denver)</option>
                  <option value="Europe/London">UK (London)</option>
                  <option value="Europe/Berlin">Central Europe (Berlin)</option>
                  <option value="Asia/Shanghai">China (Shanghai)</option>
                  <option value="Asia/Tokyo">Japan (Tokyo)</option>
                  <option value="UTC">UTC</option>
                </select>
              </div>

              {/* Date Format */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Clock className="w-4 h-4 text-text-muted" />
                  <div>
                    <p className="text-sm font-medium text-text-primary">Date Format</p>
                    <p className="text-xs text-text-muted mt-0.5">How dates are displayed throughout the app</p>
                  </div>
                </div>
                <select
                  value={dateFormat}
                  onChange={(e) => setDateFormat(e.target.value)}
                  className="bg-space-card border border-space-border rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-cyan/50"
                >
                  <option value="MM/DD/YYYY">MM/DD/YYYY</option>
                  <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                  <option value="YYYY-MM-DD">YYYY-MM-DD (ISO)</option>
                </select>
              </div>

              {/* 24-hour clock */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Clock className="w-4 h-4 text-text-muted" />
                  <div>
                    <p className="text-sm font-medium text-text-primary">24-Hour Clock</p>
                    <p className="text-xs text-text-muted mt-0.5">Display time in 24-hour format instead of AM/PM</p>
                  </div>
                </div>
                <Toggle enabled={use24Hour} onChange={() => setUse24Hour(!use24Hour)} />
              </div>

              {/* Theme */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Palette className="w-4 h-4 text-text-muted" />
                  <div>
                    <p className="text-sm font-medium text-text-primary">Theme</p>
                    <p className="text-xs text-text-muted mt-0.5">Interface appearance</p>
                  </div>
                </div>
                <select
                  value={theme}
                  onChange={(e) => setTheme(e.target.value)}
                  className="bg-space-card border border-space-border rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-cyan/50"
                >
                  <option value="dark">Dark (Space Control)</option>
                  <option value="light">Light</option>
                  <option value="system">System Default</option>
                </select>
              </div>
            </div>
          )}

          {/* ─── Audio Settings ─── */}
          {activeGroup === 'audio' && (
            <div className="space-y-6">
              <div className="flex items-center gap-3 pb-4 border-b border-space-border">
                <Mic className="w-5 h-5 text-accent-cyan" />
                <div>
                  <h2 className="text-lg font-semibold text-text-primary">Audio & Speech Settings</h2>
                  <p className="text-xs text-text-muted">Configure audio capture and speech-to-text processing</p>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-text-primary">Speech-to-Text Model</p>
                  <p className="text-xs text-text-muted mt-0.5">Select the STT engine for transcription</p>
                </div>
                <select
                  value={selectedSttModel}
                  onChange={(e) => setSelectedSttModel(e.target.value)}
                  className="bg-space-card border border-space-border rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-cyan/50"
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
                <p className="text-xs text-text-muted mt-1">
                  The selected model is applied immediately to new dictation uploads and is
                  stored locally in this browser.
                </p>
              </div>

              <div className="rounded-lg border border-space-border bg-space-card/60 px-4 py-3">
                <p className="text-xs font-medium text-text-primary">Transcription language</p>
                <p className="text-xs text-text-muted mt-1 leading-relaxed">
                  Live STT language is set in <span className="font-mono">backend/.env</span> via{' '}
                  <span className="font-mono">OPENAI_STT_LANGUAGE=en</span> (restart backend after
                  changes). Leave <span className="font-mono">OPENAI_STT_PROMPT</span> empty unless
                  you need domain words (e.g. channel names)—do not put instruction sentences there;
                  they can appear in the transcript stream. The General → Language dropdown is
                  UI-only.
                </p>
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-text-primary">Auto-Transcribe</p>
                  <p className="text-xs text-text-muted mt-0.5">Automatically transcribe audio when recording starts</p>
                </div>
                <Toggle enabled={autoTranscribe} onChange={() => setAutoTranscribe(!autoTranscribe)} />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-text-primary">Noise Suppression</p>
                  <p className="text-xs text-text-muted mt-0.5">Filter background noise from testbed environment</p>
                </div>
                <Toggle enabled={noiseSuppression} onChange={() => setNoiseSuppression(!noiseSuppression)} />
              </div>

              <div className="rounded-lg border border-accent-cyan/20 bg-accent-cyan/5 px-4 py-3 space-y-3">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm font-medium text-text-primary">
                      VoiceMeeter Banana — dual microphone
                    </p>
                    <p className="text-xs text-text-muted mt-0.5 leading-relaxed">
                      Route Input 1 → A1 and Input 2 → B1. Both streams record in parallel
                      and are labeled Microphone 1 / 2. When both speak at once, entries are
                      ordered by who started first; interjections appear after.
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
                        {devicesLoading ? 'Scanning…' : 'Rescan input devices'}
                      </button>
                    </div>
                    <div>
                      <label className="text-xs font-medium text-text-secondary">
                        Microphone 1 (VoiceMeeter A1 output)
                      </label>
                      <select
                        value={dualMic.mic1DeviceId}
                        onChange={(e) => updateDualMic({ mic1DeviceId: e.target.value })}
                        className="mt-1 w-full bg-space-card border border-space-border rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-cyan/50"
                      >
                        <option value="">— Select device —</option>
                        {audioInputs.map((d) => (
                          <option key={d.deviceId} value={d.deviceId}>
                            {d.label || d.deviceId}
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
                        className="mt-1 w-full bg-space-card border border-space-border rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-cyan/50"
                      >
                        <option value="">— Select device —</option>
                        {audioInputs.map((d) => (
                          <option key={d.deviceId} value={d.deviceId}>
                            {d.label || d.deviceId}
                          </option>
                        ))}
                      </select>
                    </div>
                  </>
                )}
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-text-primary">Voice Commands</p>
                  <p className="text-xs text-text-muted mt-0.5">Enable "ASTRA, ..." wake word for voice commands</p>
                </div>
                <Toggle enabled={voiceCommands} onChange={() => setVoiceCommands(!voiceCommands)} />
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <p className="text-sm font-medium text-text-primary">Confidence Threshold</p>
                    <p className="text-xs text-text-muted mt-0.5">Minimum confidence to accept a transcription</p>
                  </div>
                  <span className="text-sm font-mono text-accent-cyan">75%</span>
                </div>
                <input type="range" min="50" max="99" defaultValue="75" className="w-full accent-accent-cyan" />
              </div>
            </div>
          )}

          {/* ─── AI Settings ─── */}
          {activeGroup === 'ai' && (
            <div className="space-y-6">
              <div className="flex items-center gap-3 pb-4 border-b border-space-border">
                <Brain className="w-5 h-5 text-accent-purple" />
                <div>
                  <h2 className="text-lg font-semibold text-text-primary">AI & LLM Settings</h2>
                  <p className="text-xs text-text-muted">Configure language model and RAG system parameters</p>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-text-primary">Language Model</p>
                  <p className="text-xs text-text-muted mt-0.5">LLM used for log structuring</p>
                </div>
                <select
                  value={llmModel}
                  onChange={(e) => setLlmModel(e.target.value)}
                  className="bg-space-card border border-space-border rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-cyan/50"
                >
                  <option value="gpt-4">GPT-4</option>
                  <option value="gpt-4-turbo">GPT-4 Turbo</option>
                  <option value="llama-3-70b">Llama 3 70B</option>
                  <option value="llama-3-8b">Llama 3 8B</option>
                </select>
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-text-primary">RAG (Retrieval-Augmented Generation)</p>
                  <p className="text-xs text-text-muted mt-0.5">Enable contextual awareness from uploaded documents</p>
                </div>
                <Toggle enabled={ragEnabled} onChange={() => setRagEnabled(!ragEnabled)} />
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <p className="text-sm font-medium text-text-primary">Max Output Tokens</p>
                    <p className="text-xs text-text-muted mt-0.5">Maximum tokens per log generation</p>
                  </div>
                  <span className="text-sm font-mono text-accent-purple">512</span>
                </div>
                <input type="range" min="128" max="2048" step="128" defaultValue="512" className="w-full accent-accent-purple" />
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <p className="text-sm font-medium text-text-primary">Temperature</p>
                    <p className="text-xs text-text-muted mt-0.5">Controls randomness in generation (lower = more precise)</p>
                  </div>
                  <span className="text-sm font-mono text-accent-purple">0.3</span>
                </div>
                <input type="range" min="0" max="100" defaultValue="30" className="w-full accent-accent-purple" />
              </div>
            </div>
          )}

          {/* ─── Placeholder for other sections ─── */}
          {!['user', 'general', 'audio', 'ai'].includes(activeGroup) && (
            <div className="flex flex-col items-center justify-center py-16 text-text-muted">
              <Sliders className="w-12 h-12 mb-4 opacity-30" />
              <p className="text-sm font-medium">
                {settingGroups.find((g) => g.id === activeGroup)?.label} Settings
              </p>
              <p className="text-xs mt-1">Configuration options coming soon</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-col items-end gap-3 pt-6 mt-6 border-t border-space-border">
            {isSaved && (
              <p className="flex items-center gap-2 text-xs font-medium text-accent-green animate-fade-in">
                <CheckCircle2 className="w-3.5 h-3.5" />
                All changes saved locally
              </p>
            )}
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleResetDefaults}
                disabled={isSaving}
                className="flex items-center gap-2 px-4 py-2 text-text-secondary hover:text-text-primary text-sm transition-colors disabled:opacity-50"
              >
                <RotateCcw className="w-4 h-4" />
                Reset to Defaults
              </button>
              <button
                type="button"
                onClick={handleSaveChanges}
                disabled={isSaving}
                className={`flex items-center gap-2 min-w-[9.5rem] justify-center px-4 py-2 rounded-lg text-sm font-medium border transition-all duration-300 disabled:opacity-70 ${
                  isSaved
                    ? 'bg-accent-green/15 text-accent-green border-accent-green/35 scale-[1.02]'
                    : isSaving
                      ? 'bg-accent-cyan/10 text-accent-cyan border-accent-cyan/25'
                      : 'bg-accent-cyan/15 text-accent-cyan border-accent-cyan/30 hover:bg-accent-cyan/25'
                }`}
              >
                {isSaving ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Saving…
                  </>
                ) : isSaved ? (
                  <>
                    <CheckCircle2 className="w-4 h-4" />
                    Saved
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    Save Changes
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
