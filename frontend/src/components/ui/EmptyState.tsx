import React from 'react';
import { LucideIcon, Inbox } from 'lucide-react';
import { Button } from './button';
import { IconTile } from './IconTile';
import { cn } from '../../lib/utils';

export interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
    icon?: LucideIcon;
  };
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon = Inbox,
  title,
  description,
  action,
  className,
}) => {
  const ActionIcon = action?.icon;

  return (
    <div
      className={cn(
        'py-12 px-4 text-center flex flex-col items-center justify-center select-none animate-fade-in',
        className
      )}
    >
      <IconTile icon={Icon} size="lg" tone="secondary" className="mb-3.5 border border-slate-200/60 dark:border-white/[0.06]" />

      <h3 className="text-sm font-extrabold text-slate-700 dark:text-slate-200">
        {title}
      </h3>

      {description && (
        <p className="mt-1 text-xs text-slate-400 dark:text-vuexy-dark-muted max-w-sm leading-relaxed">
          {description}
        </p>
      )}

      {action && (
        <div className="mt-4">
          <Button
            size="sm"
            onClick={action.onClick}
            className="space-x-1.5 font-bold cursor-pointer"
          >
            {ActionIcon && <ActionIcon className="w-3.5 h-3.5" />}
            <span>{action.label}</span>
          </Button>
        </div>
      )}
    </div>
  );
};
