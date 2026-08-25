import * as React from 'react';
import { Avatar, AvatarProps } from './Avatar';
import { cn } from '../../lib/utils';

export interface AvatarGroupProps {
  items: Array<{ name: string }>;
  max?: number;
  size?: AvatarProps['size'];
  shape?: AvatarProps['shape'];
  className?: string;
}

export const AvatarGroup: React.FC<AvatarGroupProps> = ({
  items,
  max = 4,
  size = 'md',
  shape = 'circle',
  className,
}) => {
  const visibleItems = items.slice(0, max);
  const remainingCount = items.length - max;

  const countSizeClasses = {
    xs: 'w-6 h-6 text-[9px]',
    sm: 'w-8 h-8 text-[10px]',
    md: 'w-10 h-10 text-xs',
    lg: 'w-12 h-12 text-sm',
    xl: 'w-14 h-14 text-base',
  };

  return (
    <div className={cn('flex items-center -space-x-2 overflow-hidden py-1', className)}>
      {visibleItems.map((item, idx) => (
        <div key={idx} className="ring-2 ring-white dark:ring-[#2F3349] rounded-full">
          <Avatar name={item.name} size={size} shape={shape} />
        </div>
      ))}

      {remainingCount > 0 && (
        <div
          className={cn(
            'flex items-center justify-center font-bold font-mono text-slate-600 dark:text-slate-300 bg-slate-200 dark:bg-white/[0.1] ring-2 ring-white dark:ring-[#2F3349] rounded-full select-none',
            countSizeClasses[size]
          )}
        >
          +{remainingCount}
        </div>
      )}
    </div>
  );
};
