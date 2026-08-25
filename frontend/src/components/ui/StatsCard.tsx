import React from 'react';
import { LucideIcon } from 'lucide-react';
import { Card, CardContent } from './card';
import { Badge } from './badge';
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

const variantStyles: Record<StatIconVariant, { bg: string; text: string }> = {
  primary: { bg: 'bg-[#7367F0]/15 dark:bg-[#7367F0]/25', text: 'text-[#7367F0] dark:text-[#A59DF8]' },
  success: { bg: 'bg-[#28C76F]/15 dark:bg-[#28C76F]/25', text: 'text-[#28C76F] dark:text-[#5BE49B]' },
  danger: { bg: 'bg-[#EA5455]/15 dark:bg-[#EA5455]/25', text: 'text-[#EA5455] dark:text-[#FF7F80]' },
  warning: { bg: 'bg-[#FF9F43]/15 dark:bg-[#FF9F43]/25', text: 'text-[#FF9F43] dark:text-[#FFBD7A]' },
  info: { bg: 'bg-[#00CFE8]/15 dark:bg-[#00CFE8]/25', text: 'text-[#00CFE8] dark:text-[#4DE2F5]' },
  secondary: { bg: 'bg-slate-100 dark:bg-slate-800', text: 'text-slate-600 dark:text-slate-300' },
};

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
  const currentVariant = variantStyles[iconVariant] || variantStyles.primary;

  return (
    <Card 
      onClick={onClick}
      className={cn(
        'transition-all duration-200 select-none group',
        onClick ? 'cursor-pointer hover:shadow-md hover:border-[#7367F0]/30' : 'hover:shadow-sm',
        className
      )}
    >
      <CardContent className="p-5">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <span className="text-[11px] font-bold text-slate-500 dark:text-[#7E7F96] uppercase tracking-wider block">
              {title}
            </span>
            <div className="text-2xl font-extrabold text-slate-800 dark:text-white tracking-tight">
              {value}
            </div>
          </div>
          <div className={cn('w-11 h-11 rounded-xl flex items-center justify-center font-bold transition-transform group-hover:scale-105', currentVariant.bg, currentVariant.text)}>
            <Icon className="w-5 h-5" />
          </div>
        </div>

        {(badge || subText) && (
          <div className="mt-3.5 flex items-center space-x-1.5 text-xs">
            {badge && (
              <Badge variant={badge.variant || 'success'} className="text-[10px] px-1.5 py-0.5">
                {badge.text}
              </Badge>
            )}
            {subText && (
              <span className="text-slate-400 dark:text-[#7E7F96] text-[11px] font-medium">
                {subText}
              </span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
