import * as React from 'react';
import { Avatar } from '../ui/Avatar';
import { cn } from '../../lib/utils';

export interface BusinessCellProps {
  name: string;
  category?: string;
  entityType?: string;
  onClick?: () => void;
  className?: string;
}

export const BusinessCell: React.FC<BusinessCellProps> = ({
  name,
  category,
  entityType,
  onClick,
  className,
}) => {
  return (
    <div className={cn('flex items-center space-x-2.5 max-w-[260px]', className)}>
      <Avatar name={name} size="sm" shape="rounded" />
      <div className="min-w-0 flex-1">
        {onClick ? (
          <button
            type="button"
            onClick={onClick}
            className="font-bold text-slate-800 dark:text-white text-xs truncate hover:text-[#7367F0] dark:hover:text-[#A59DF8] transition-colors cursor-pointer text-left block w-full"
          >
            {name}
          </button>
        ) : (
          <div className="font-bold text-slate-800 dark:text-white text-xs truncate">
            {name}
          </div>
        )}

        <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
          {category && (
            <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-[#7367F0]/10 text-[#7367F0] dark:bg-[#7367F0]/20 dark:text-[#A59DF8] truncate max-w-[150px]">
              {category}
            </span>
          )}
          {entityType && (
            <span className="text-[9px] font-mono uppercase px-1 py-0.2 rounded bg-slate-100 dark:bg-white/[0.06] text-slate-500">
              {entityType}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
