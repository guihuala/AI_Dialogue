export type AutoFixPresetId = 'strict' | 'balanced' | 'loose';

export type AutoFixConfig = {
  fixInvalidType: boolean;
  fixInvalidNumbers: boolean;
  fixInvalidTriggers: boolean;
  normalizeKeyOptions: boolean;
  fillKeyOptions: boolean;
  resetReviewed: boolean;
};

export const AUTO_FIX_PRESETS: Record<AutoFixPresetId, { label: string; config: AutoFixConfig }> = {
  strict: {
    label: '严格',
    config: {
      fixInvalidType: true,
      fixInvalidNumbers: true,
      fixInvalidTriggers: true,
      normalizeKeyOptions: true,
      fillKeyOptions: true,
      resetReviewed: true,
    },
  },
  balanced: {
    label: '平衡',
    config: {
      fixInvalidType: true,
      fixInvalidNumbers: true,
      fixInvalidTriggers: true,
      normalizeKeyOptions: true,
      fillKeyOptions: true,
      resetReviewed: false,
    },
  },
  loose: {
    label: '宽松',
    config: {
      fixInvalidType: true,
      fixInvalidNumbers: false,
      fixInvalidTriggers: false,
      normalizeKeyOptions: true,
      fillKeyOptions: false,
      resetReviewed: false,
    },
  },
};
