export interface SttModelOption {
  value: string;
  label: string;
  description: string;
}

export const STT_MODEL_OPTIONS: SttModelOption[] = [
  {
    value: 'gpt-4o-mini-transcribe',
    label: 'OpenAI GPT-4o Mini Transcribe',
    description: 'Lower latency and lower cost for everyday dictation.',
  },
  {
    value: 'gpt-4o-transcribe',
    label: 'OpenAI GPT-4o Transcribe',
    description: 'Higher accuracy for more challenging audio conditions.',
  },
  {
    value: 'gpt-4o-transcribe-diarize',
    label: 'OpenAI GPT-4o Transcribe Diarize',
    description: 'Adds speaker diarization when multiple speakers are present.',
  },
];

export const DEFAULT_STT_MODEL = STT_MODEL_OPTIONS[0].value;

export function isSupportedSttModel(model: string): boolean {
  return STT_MODEL_OPTIONS.some((option) => option.value === model);
}

export function getSttModelLabel(model: string): string {
  return (
    STT_MODEL_OPTIONS.find((option) => option.value === model)?.label ??
    model
  );
}
