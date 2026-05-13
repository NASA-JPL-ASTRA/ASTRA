export interface SummaryModelOption {
  value: string;
  label: string;
  description: string;
}

export const SUMMARY_MODEL_OPTIONS: SummaryModelOption[] = [
  {
    value: 'gpt-5-mini',
    label: 'GPT-5 Mini',
    description: 'Fast summary edits and action extraction.',
  },
  {
    value: 'gpt-5',
    label: 'GPT-5',
    description: 'Balanced quality for structured notes.',
  },
  {
    value: 'gpt-5.5',
    label: 'GPT-5.5',
    description: 'Highest-quality polished note summaries.',
  },
];

export const DEFAULT_SUMMARY_MODEL = SUMMARY_MODEL_OPTIONS[0].value;

export function getSummaryModelLabel(model: string): string {
  return SUMMARY_MODEL_OPTIONS.find((option) => option.value === model)?.label ?? model;
}
