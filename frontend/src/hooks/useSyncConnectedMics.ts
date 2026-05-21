import { useEffect } from 'react';
import {
  AUDIO_SETTINGS_CHANGED,
  detectConnectedMics,
  loadDualMicConfig,
} from '../config/audioInputs';
import { useStore } from '../store/useStore';

/** Keep session speakers in sync with how many mics are actually available. */
export function useSyncConnectedMics() {
  const setMicSpeakers = useStore((s) => s.setMicSpeakers);

  useEffect(() => {
    let cancelled = false;

    const sync = async () => {
      const dualEnabled = loadDualMicConfig().enabled;
      if (!dualEnabled) return;

      const info = await detectConnectedMics();
      if (cancelled || info.sources.length === 0) return;
      setMicSpeakers(info.sources);
    };

    void sync();

    const media = navigator.mediaDevices;
    media?.addEventListener('devicechange', sync);
    window.addEventListener(AUDIO_SETTINGS_CHANGED, sync);
    return () => {
      cancelled = true;
      media?.removeEventListener('devicechange', sync);
      window.removeEventListener(AUDIO_SETTINGS_CHANGED, sync);
    };
  }, [setMicSpeakers]);
}
