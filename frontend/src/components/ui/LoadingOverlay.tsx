import * as React from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface LoadingOverlayProps {
  isLoading: boolean;
  message?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export const LoadingOverlay: React.FC<LoadingOverlayProps> = ({
  isLoading,
  message,
  children,
  className,
}) => {
  return (
    <div className={cn('relative', className)}>
      {children}

      {isLoading && (
        <div className="absolute inset-0 z-30 flex flex-col items-center justify-center bg-white/70 dark:bg-slate-900/70 backdrop-blur-xs rounded-xl transition-all animate-fade-in">
          <Loader2 className="w-8 h-8 animate-spin text-[#7367F0]" />
          {message && (
            <span className="mt-2 text-xs font-bold text-slate-700 dark:text-slate-200 animate-pulse">
              {message}
            </span>
          )}
        </div>
      )}
    </div>
  );
};
