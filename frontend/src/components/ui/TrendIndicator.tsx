import * as React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface TrendIndicatorProps {
  value: number | string;
  direction?: 'up' | 'down' | 'neutral';
  isPositiveGood?: boolean;
  prefix?: string;
  suffix?: string;
  className?: string;
}

export const TrendIndicator: React.FC<TrendIndicatorProps> = ({
  value,
  direction = 'up',
  isPositiveGood = true,
  prefix = '',
  suffix = '%',
  className,
}) => {
  const isUp = direction === 'up';
  const isDown = direction === 'down';
  const isNeutral = direction === 'neutral';

  const isSuccess = (isUp && isPositiveGood) || (isDown && !isPositiveGood);
  const isDanger = (isDown && isPositiveGood) || (isUp && !isPositiveGood);

  const colorStyles = isSuccess
    ? 'text-[#28C76F] bg-[#28C76F]/15 border-[#28C76F]/25'
    : isDanger
    ? 'text-[#EA5455] bg-[#EA5455]/15 border-[#EA5455]/25'
    : 'text-slate-500 bg-slate-100 dark:bg-white/[0.06] border-slate-200 dark:border-white/[0.08]';

  return (
    <span
      className={cn(
        'inline-flex items-center space-x-1 px-2 py-0.5 rounded-md border text-[11px] font-bold font-mono select-none',
        colorStyles,
        className
      )}
    >
      {isUp ? (
        <TrendingUp className="w-3 h-3" />
      ) : isDown ? (
        <TrendingDown className="w-3 h-3" />
      ) : (
        <Minus className="w-3 h-3" />
      )}
      <span>
        {prefix}
        {value}
        {suffix}
      </span>
    </span>
  );
};
