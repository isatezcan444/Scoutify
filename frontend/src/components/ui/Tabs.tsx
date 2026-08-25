import * as React from 'react';
import { LucideIcon } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface TabItem {
  id: string;
  label: string;
  icon?: LucideIcon;
  count?: number | string;
  disabled?: boolean;
}

export interface TabsProps {
  items: TabItem[];
  activeId: string;
  onChange: (id: string) => void;
  variant?: 'pills' | 'line' | 'segmented';
  className?: string;
}

export const Tabs: React.FC<TabsProps> = ({
  items,
  activeId,
  onChange,
  variant = 'pills',
  className,
}) => {
  if (variant === 'segmented') {
    return (
      <div
        className={cn(
          'inline-flex p-1 rounded-xl bg-slate-100 dark:bg-white/[0.06] border border-slate-200/80 dark:border-white/[0.08]',
          className
        )}
      >
        {items.map((tab) => {
          const isActive = activeId === tab.id;
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              type="button"
              disabled={tab.disabled}
              onClick={() => onChange(tab.id)}
              className={cn(
                'flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all duration-150 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed',
                isActive
                  ? 'bg-white dark:bg-[#2F3349] text-[#7367F0] shadow-sm shadow-black/5 dark:text-white'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              )}
            >
              {Icon && <Icon className="w-3.5 h-3.5" />}
              <span>{tab.label}</span>
              {tab.count !== undefined && (
                <span
                  className={cn(
                    'px-1.5 py-0.2 rounded-full text-[10px] font-mono',
                    isActive
                      ? 'bg-[#7367F0]/15 text-[#7367F0] dark:bg-[#7367F0]/25 dark:text-[#A59DF8]'
                      : 'bg-slate-200 dark:bg-white/[0.1] text-slate-600 dark:text-slate-400'
                  )}
                >
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}
      </div>
    );
  }

  if (variant === 'line') {
    return (
      <div className={cn('flex items-center space-x-6 border-b border-slate-200 dark:border-white/[0.08]', className)}>
        {items.map((tab) => {
          const isActive = activeId === tab.id;
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              type="button"
              disabled={tab.disabled}
              onClick={() => onChange(tab.id)}
              className={cn(
                'flex items-center space-x-2 py-3 border-b-2 font-bold text-xs transition-colors cursor-pointer disabled:opacity-40 -mb-[2px]',
                isActive
                  ? 'border-[#7367F0] text-[#7367F0] dark:text-[#A59DF8]'
                  : 'border-transparent text-slate-500 hover:text-slate-800 dark:text-[#7E7F96] dark:hover:text-slate-200'
              )}
            >
              {Icon && <Icon className="w-4 h-4" />}
              <span>{tab.label}</span>
              {tab.count !== undefined && (
                <span className="px-1.5 py-0.2 rounded bg-slate-100 dark:bg-white/[0.06] text-[10px] font-mono">
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}
      </div>
    );
  }

  // Default: 'pills'
  return (
    <div className={cn('flex items-center space-x-2 flex-wrap gap-y-1.5', className)}>
      {items.map((tab) => {
        const isActive = activeId === tab.id;
        const Icon = tab.icon;
        return (
          <button
            key={tab.id}
            type="button"
            disabled={tab.disabled}
            onClick={() => onChange(tab.id)}
            className={cn(
              'flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-bold transition-all duration-150 cursor-pointer disabled:opacity-40',
              isActive
                ? 'bg-[#7367F0] text-white shadow-md shadow-[#7367F0]/30'
                : 'bg-white dark:bg-[#2F3349] text-slate-600 dark:text-slate-300 border border-slate-200/80 dark:border-white/[0.08] hover:bg-slate-50 dark:hover:bg-white/[0.04]'
            )}
          >
            {Icon && <Icon className="w-3.5 h-3.5" />}
            <span>{tab.label}</span>
            {tab.count !== undefined && (
              <span
                className={cn(
                  'px-1.5 py-0.2 rounded-md text-[10px] font-mono font-bold ml-1',
                  isActive
                    ? 'bg-white/25 text-white'
                    : 'bg-slate-100 dark:bg-white/[0.08] text-slate-600 dark:text-slate-300'
                )}
              >
                {tab.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
};
