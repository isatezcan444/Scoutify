import * as React from 'react';
import { X } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useI18n } from '../../context/I18nContext';

export interface ChipProps {
  label: React.ReactNode;
  onRemove?: () => void;
  removeLabel?: string;
  variant?: 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'default';
  size?: 'sm' | 'md';
  icon?: React.ReactNode;
  className?: string;
}

export const Chip: React.FC<ChipProps> = ({
  label,
  onRemove,
  removeLabel,
  variant = 'default',
  size = 'md',
  icon,
  className,
}) => {
  const { t } = useI18n();
  const variantStyles = {
    default: 'bg-slate-100 dark:bg-white/[0.06] text-slate-700 dark:text-slate-200 border-slate-200 dark:border-white/[0.08]',
    primary: 'bg-[#7367F0]/15 text-[#7367F0] dark:bg-[#7367F0]/25 dark:text-[#A59DF8] border-[#7367F0]/30',
    success: 'bg-[#28C76F]/15 text-[#28C76F] dark:bg-[#28C76F]/25 dark:text-[#5BE49B] border-[#28C76F]/30',
    warning: 'bg-[#FF9F43]/15 text-[#FF9F43] dark:bg-[#FF9F43]/25 dark:text-[#FFBD7A] border-[#FF9F43]/30',
    danger: 'bg-[#EA5455]/15 text-[#EA5455] dark:bg-[#EA5455]/25 dark:text-[#FF7F80] border-[#EA5455]/30',
    info: 'bg-[#00CFE8]/15 text-[#00CFE8] dark:bg-[#00CFE8]/25 dark:text-[#4DE2F5] border-[#00CFE8]/30',
  };

  const sizeStyles = {
    sm: 'text-[10px] px-2 py-0.5 space-x-1',
    md: 'text-[11px] px-2.5 py-1 space-x-1.5',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center font-bold rounded-lg border transition-all duration-150 select-none shadow-2xs',
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
    >
      {icon && <span className="shrink-0">{icon}</span>}
      <span className="truncate max-w-[220px]">{label}</span>
      {onRemove && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          className="hover:opacity-75 p-0.5 rounded-full hover:bg-black/10 dark:hover:bg-white/10 transition-colors cursor-pointer shrink-0 ml-0.5"
          aria-label={removeLabel ?? t('common.removeLabel')}
        >
          <X className="w-3 h-3" />
        </button>
      )}
    </span>
  );
};
