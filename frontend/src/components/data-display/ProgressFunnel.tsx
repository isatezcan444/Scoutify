import * as React from 'react';
import { Progress } from '../ui/Progress';
import { cn } from '../../lib/utils';

export interface FunnelStage {
  id: string | number;
  label: string;
  count: number;
  percentage: number;
  variant?: 'primary' | 'success' | 'warning' | 'info' | 'gradient';
}

export interface ProgressFunnelProps {
  stages: FunnelStage[];
  className?: string;
}

export const ProgressFunnel: React.FC<ProgressFunnelProps> = ({ stages, className }) => {
  return (
    <div className={cn('space-y-4', className)}>
      {stages.map((stage, idx) => (
        <div key={stage.id} className="space-y-1.5">
          <div className="flex justify-between text-xs font-bold text-slate-700 dark:text-slate-200">
            <span>
              {idx + 1}. {stage.label}
            </span>
            <span className="font-mono text-[#7367F0]">
              {stage.count} (%{Math.round(stage.percentage)})
            </span>
          </div>
          <Progress
            value={stage.percentage}
            variant={stage.variant || (idx === 0 ? 'primary' : idx === 1 ? 'info' : idx === 2 ? 'warning' : 'success')}
            size="md"
          />
        </div>
      ))}
    </div>
  );
};
