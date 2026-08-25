/**
 * Vuexy design tokens — single source of truth for semantic tones.
 *
 * Components MUST consume these helpers instead of hardcoding palette hexes,
 * so light/dark surfaces stay consistent across the design system (DIP).
 * Tone definitions derive from the `vuexy-*` palette declared in tailwind.config.js.
 */
import { cva, type VariantProps } from 'class-variance-authority';

export type SemanticTone = 'primary' | 'success' | 'danger' | 'warning' | 'info' | 'secondary';

/** Soft treatment: tinted background + tone text (icon tiles, badges, info boxes). */
const TONE_SOFT: Record<SemanticTone, string> = {
  primary: 'bg-vuexy-primary/15 dark:bg-vuexy-primary/25 text-vuexy-primary dark:text-[#A59DF8]',
  success: 'bg-vuexy-success/15 dark:bg-vuexy-success/25 text-vuexy-success dark:text-[#5BE49B]',
  danger: 'bg-vuexy-danger/15 dark:bg-vuexy-danger/25 text-vuexy-danger dark:text-[#FF7F80]',
  warning: 'bg-vuexy-warning/15 dark:bg-vuexy-warning/25 text-vuexy-warning dark:text-[#FFBD7A]',
  info: 'bg-vuexy-info/15 dark:bg-vuexy-info/25 text-vuexy-info dark:text-[#4DE2F5]',
  secondary: 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300',
};

/** Matching hairline border per tone (modal headers, alert boxes). */
const TONE_BORDER: Record<SemanticTone, string> = {
  primary: 'border-vuexy-primary/20',
  success: 'border-vuexy-success/20',
  danger: 'border-vuexy-danger/20',
  warning: 'border-vuexy-warning/20',
  info: 'border-vuexy-info/20',
  secondary: 'border-slate-200 dark:border-white/[0.08]',
};

const composeOutline = (): Record<SemanticTone, string> =>
  Object.fromEntries(
    Object.entries(TONE_SOFT).map(([tone, soft]) => [tone, `${soft} ${TONE_BORDER[tone as SemanticTone]}`])
  ) as Record<SemanticTone, string>;

export const toneSoftVariants = cva('', {
  variants: { tone: TONE_SOFT },
  defaultVariants: { tone: 'primary' },
});

export const toneOutlineVariants = cva('', {
  variants: { tone: composeOutline() },
  defaultVariants: { tone: 'primary' },
});

export type ToneVariantProps = VariantProps<typeof toneSoftVariants>;
