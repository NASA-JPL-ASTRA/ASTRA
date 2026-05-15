import { createContext, useContext, type ReactNode } from 'react';
import { useWhisper } from '../hooks/useWhisper';

type RecordingControls = ReturnType<typeof useWhisper>;

const RecordingContext = createContext<RecordingControls | null>(null);

export function RecordingProvider({ children }: { children: ReactNode }) {
  const recording = useWhisper();

  return (
    <RecordingContext.Provider value={recording}>
      {children}
    </RecordingContext.Provider>
  );
}

export function useRecording() {
  const context = useContext(RecordingContext);
  if (!context) {
    throw new Error('useRecording must be used within RecordingProvider');
  }
  return context;
}
