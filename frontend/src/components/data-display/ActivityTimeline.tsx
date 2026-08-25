import * as React from 'react';
import { cn } from '../../lib/utils';

export interface TimelineEvent {
  id: string | number;
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  timestamp?: string;
  badge?: React.ReactNode;
  variant?: 'primary' | 'success' | 'warning' | 'danger' | 'info';
  icon?: React.ReactNode;
}

export interface ActivityTimelineProps {
  events: TimelineEvent[];
  emptyMessage?: string;
  className?: string;
}

export const ActivityTimeline: React.FC<ActivityTimelineProps> = ({
  events,
  emptyMessage = 'No activity recorded yet.',
  className,
}) => {
  if (events.length === 0) {
    return (
      <div className="py-8 text-center text-xs text-slate-400 font-medium">
        {emptyMessage}
      </div>
    );
  }

  const dotColors = {
    primary: 'bg-[#7367F0] ring-[#7367F0]/20',
    success: 'bg-[#28C76F] ring-[#28C76F]/20',
    warning: 'bg-[#FF9F43] ring-[#FF9F43]/20',
    danger: 'bg-[#EA5455] ring-[#EA5455]/20',
    info: 'bg-[#00CFE8] ring-[#00CFE8]/20',
  };

  return (
    <div className={cn('relative pl-6 space-y-6', className)}>
      {/* Vertical Timeline Track */}
      <div className="absolute top-2 bottom-2 left-2.5 w-[2px] bg-slate-200 dark:bg-white/[0.08]" />

      {events.map((event) => {
        const variant = event.variant || 'primary';
        return (
          <div key={event.id} className="relative group">
            {/* Timeline Dot */}
            <div
              className={cn(
                'absolute -left-6 top-1 w-3 h-3 rounded-full ring-4 transition-transform group-hover:scale-125',
                dotColors[variant]
              )}
            />

            {/* Event Item Container */}
            <div className="space-y-1">
              <div className="flex items-center justify-between gap-2">
                <div className="font-bold text-xs text-slate-800 dark:text-white flex items-center gap-2">
                  {event.title}
                </div>
                {event.badge}
              </div>

              {event.subtitle && (
                <div className="text-xs text-slate-500 dark:text-[#7E7F96] leading-relaxed">
                  {event.subtitle}
                </div>
              )}

              {event.timestamp && (
                <div className="text-[10px] font-mono text-slate-400 dark:text-slate-500">
                  {event.timestamp}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};
