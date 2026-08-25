import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, LucideIcon } from 'lucide-react';
import { cn } from '../../lib/utils';

export type ModalVariant = 'primary' | 'danger' | 'warning' | 'success' | 'info';

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  icon?: LucideIcon;
  variant?: ModalVariant;
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl';
  children: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
  closeOnOutsideClick?: boolean;
}

const variantStyles: Record<ModalVariant, { bg: string; text: string; border: string }> = {
  primary: {
    bg: 'bg-[#7367F0]/10 dark:bg-[#7367F0]/20',
    text: 'text-[#7367F0] dark:text-[#A59DF8]',
    border: 'border-[#7367F0]/20',
  },
  danger: {
    bg: 'bg-rose-50 dark:bg-rose-500/10',
    text: 'text-[#EA5455] dark:text-[#FF7F80]',
    border: 'border-rose-200 dark:border-rose-500/20',
  },
  warning: {
    bg: 'bg-amber-50 dark:bg-amber-500/10',
    text: 'text-[#FF9F43] dark:text-[#FFBD7A]',
    border: 'border-amber-200 dark:border-amber-500/20',
  },
  success: {
    bg: 'bg-emerald-50 dark:bg-emerald-500/10',
    text: 'text-[#28C76F] dark:text-[#5BE49B]',
    border: 'border-emerald-200 dark:border-emerald-500/20',
  },
  info: {
    bg: 'bg-cyan-50 dark:bg-cyan-500/10',
    text: 'text-[#00CFE8] dark:text-[#4DE2F5]',
    border: 'border-cyan-200 dark:border-cyan-500/20',
  },
};

const maxWidthClasses = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
  '2xl': 'max-w-2xl',
};

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  subtitle,
  icon: Icon,
  variant = 'primary',
  maxWidth = 'md',
  children,
  footer,
  className,
  closeOnOutsideClick = true,
}) => {
  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen || typeof document === 'undefined') return null;

  const currentVariant = variantStyles[variant] || variantStyles.primary;

  return createPortal(
    <div
      className="fixed inset-0 z-[99999] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in select-none"
      onClick={() => closeOnOutsideClick && onClose()}
    >
      <div
        className={cn(
          'w-full bg-white dark:bg-[#2F3349] rounded-2xl shadow-2xl border border-slate-200/80 dark:border-white/[0.08] p-6 animate-scale-up',
          maxWidthClasses[maxWidth] || maxWidthClasses.md,
          className
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-3 mb-4">
          <div className="flex items-center space-x-3">
            {Icon && (
              <div
                className={cn(
                  'w-11 h-11 rounded-2xl flex items-center justify-center shrink-0 border',
                  currentVariant.bg,
                  currentVariant.text,
                  currentVariant.border
                )}
              >
                <Icon className="w-5 h-5 stroke-[2.2]" />
              </div>
            )}
            <div>
              <h3 className="text-base font-extrabold text-slate-800 dark:text-white tracking-tight">
                {title}
              </h3>
              {subtitle && (
                <p className="text-[11px] text-slate-400 dark:text-[#7E7F96] font-medium mt-0.5">
                  {subtitle}
                </p>
              )}
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/[0.06] transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="text-xs text-slate-600 dark:text-slate-300">
          {children}
        </div>

        {/* Optional Footer */}
        {footer && (
          <div className="mt-5 pt-4 border-t border-slate-100 dark:border-white/[0.06] flex items-center justify-end space-x-2.5">
            {footer}
          </div>
        )}
      </div>
    </div>,
    document.body
  );
};
