import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, LucideIcon } from 'lucide-react';
import { cn } from '../../lib/utils';
import { IconTile } from './IconTile';

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
  // Close on Escape key + lock background scroll
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

  // ModalVariant values map 1:1 onto IconTile semantic tones.
  const iconTone = variant as 'primary' | 'danger' | 'warning' | 'success' | 'info';

  return createPortal(
    <div
      className="fixed inset-0 z-[99999] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in select-none"
      onClick={() => closeOnOutsideClick && onClose()}
    >
      <div
        className={cn(
          'w-full bg-white dark:bg-vuexy-dark-card rounded-2xl shadow-2xl border border-slate-200/80 dark:border-white/[0.08] p-6 animate-scale-up',
          maxWidthClasses[maxWidth] || maxWidthClasses.md,
          className
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-3 mb-4">
          <div className="flex items-center space-x-3">
            {Icon && (
              <IconTile icon={Icon} size="md" tone={iconTone} />
            )}
            <div>
              <h3 className="text-base font-extrabold text-slate-800 dark:text-white tracking-tight">
                {title}
              </h3>
              {subtitle && (
                <p className="text-[11px] text-slate-400 dark:text-vuexy-dark-muted font-medium mt-0.5">
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

        {/* Content Body — typography is owned by the caller */}
        <div>{children}</div>

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
