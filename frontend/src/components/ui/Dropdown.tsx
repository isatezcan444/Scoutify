import React, { useState, useRef, useEffect } from 'react';
import { cn } from '../../lib/utils';

export interface DropdownItem {
  id: string;
  label: React.ReactNode;
  icon?: React.ReactNode;
  onClick: () => void;
  variant?: 'default' | 'danger' | 'warning' | 'primary';
  disabled?: boolean;
}

export interface DropdownProps {
  trigger: React.ReactNode;
  items: (DropdownItem | 'divider')[];
  align?: 'left' | 'right';
  className?: string;
  menuClassName?: string;
}

export const Dropdown: React.FC<DropdownProps> = ({
  trigger,
  items,
  align = 'right',
  className,
  menuClassName,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  return (
    <div className={cn('relative inline-block text-left', className)} ref={dropdownRef}>
      <div onClick={() => setIsOpen(!isOpen)} className="cursor-pointer">
        {trigger}
      </div>

      {isOpen && (
        <div
          className={cn(
            'absolute mt-1.5 w-48 rounded-xl bg-white dark:bg-[#2F3349] border border-slate-200/80 dark:border-white/[0.08] shadow-2xl p-1.5 z-50 animate-scale-in',
            align === 'right' ? 'right-0' : 'left-0',
            menuClassName
          )}
        >
          {items.map((item, idx) => {
            if (item === 'divider') {
              return (
                <div
                  key={`div-${idx}`}
                  className="my-1 border-t border-slate-100 dark:border-white/[0.06]"
                />
              );
            }

            const variantClasses = {
              default: 'text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-white/[0.04] hover:text-[#7367F0]',
              primary: 'text-[#7367F0] hover:bg-[#7367F0]/10',
              warning: 'text-[#FF9F43] hover:bg-[#FF9F43]/10',
              danger: 'text-[#EA5455] hover:bg-[#EA5455]/10',
            };

            return (
              <button
                key={item.id}
                type="button"
                disabled={item.disabled}
                onClick={() => {
                  if (!item.disabled) {
                    item.onClick();
                    setIsOpen(false);
                  }
                }}
                className={cn(
                  'w-full text-left px-3 py-2 rounded-lg text-xs font-semibold flex items-center space-x-2 transition-colors cursor-pointer disabled:opacity-40 disabled:pointer-events-none',
                  variantClasses[item.variant || 'default']
                )}
              >
                {item.icon && <span className="w-4 h-4 shrink-0 flex items-center justify-center">{item.icon}</span>}
                <span className="truncate">{item.label}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};
