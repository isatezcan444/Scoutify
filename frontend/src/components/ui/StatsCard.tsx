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
        'transition-all duration-200 select-none group',
        onClick ? 'cursor-pointer hover:shadow-md hover:border-vuexy-primary/30' : 'hover:shadow-sm',
        className
      )}
    >
      <CardContent className="p-5">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <span className="text-[11px] font-bold text-slate-500 dark:text-vuexy-dark-muted uppercase tracking-wider block">
              {title}
            </span>
            <div className="text-2xl font-extrabold text-slate-800 dark:text-white tracking-tight">
              {value}
            </div>
          </div>
          <IconTile
            icon={Icon}
            size="md"
            tone={iconVariant}
            className="font-bold transition-transform group-hover:scale-105"
          />
        </div>

        {(badge || subText) && (
          <div className="mt-3.5 flex items-center space-x-1.5 text-xs">
            {badge && (
              <Badge variant={badge.variant || 'success'} className="text-[10px] px-1.5 py-0.5">
                {badge.text}
              </Badge>
            )}
            {subText && (
              <span className="text-slate-400 dark:text-vuexy-dark-muted text-[11px] font-medium">
                {subText}
              </span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
