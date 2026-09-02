import React from 'react';
import { LucideIcon } from 'lucide-react';
import { Card, CardContent } from './card';
import { Badge } from './badge';
import { IconTile } from './IconTile';
import { cn } from '../../lib/utils';

export type StatIconVariant = 'primary' | 'success' | 'danger' | 'warning' | 'info' | 'secondary';

export interface StatsCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  iconVariant?: StatIconVariant;
  badge?: {
    text: string;
    variant?: 'primary' | 'success' | 'danger' | 'warning' | 'info' | 'default';
  };
  subText?: string;
  className?: string;
  onClick?: () => void;
}

export const StatsCard: React.FC<StatsCardProps> = ({
  title,
  value,
  icon: Icon,
  iconVariant = 'primary',
  badge,
  subText,
  className,
  onClick,
}) => {
  return (
    <Card
      onClick={onClick}
      className={cn(
        'h-full flex flex-col justify-between transition-all duration-200 select-none group',
        onClick ? 'cursor-pointer hover:shadow-md hover:border-vuexy-primary/30' : 'hover:shadow-sm',
        className
      )}
    >
      <CardContent className="p-5 flex flex-col justify-between h-full flex-1">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <span
              className="text-[11px] font-bold text-slate-500 dark:text-vuexy-dark-muted uppercase tracking-wider block h-7 leading-tight line-clamp-2"
              title={title}
            >
              {title}
            </span>
            <div className="text-2xl font-extrabold text-slate-800 dark:text-white tracking-tight mt-1.5">
              {value}
            </div>
          </div>
          <IconTile
            icon={Icon}
            size="md"
            tone={iconVariant}
            className="font-bold transition-transform group-hover:scale-105 shrink-0 mt-0.5"
          />
        </div>

        {(badge || subText) && (
          <div className="mt-4 pt-2.5 flex flex-col justify-end gap-1.5 text-xs">
            <div className="min-h-[22px] flex items-center">
              {badge && (
                <Badge
                  variant={badge.variant || 'success'}
                  className="text-[10px] font-semibold px-2 py-0.5 whitespace-nowrap inline-flex"
                >
                  {badge.text}
                </Badge>
              )}
            </div>
            <div className="min-h-[16px] flex items-center">
              {subText && (
                <span className="text-slate-400 dark:text-vuexy-dark-muted text-[11px] font-medium leading-tight">
                  {subText}
                </span>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
