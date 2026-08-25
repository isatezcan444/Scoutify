import * as React from 'react';
import { LucideIcon } from 'lucide-react';
import { cn, renderIcon } from '../../lib/utils';

export interface FormSectionProps {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  icon?: LucideIcon | React.ReactNode;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export const FormSection: React.FC<FormSectionProps> = ({
  title,
  subtitle,
  icon: Icon,
  action,
  children,
  className,
}) => {
  return (
    <div className={cn('space-y-4 pt-2', className)}>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-100 dark:border-white/[0.06]">
        <div className="flex items-center space-x-2.5">
          {Icon && (
            <div className="w-8 h-8 rounded-lg bg-[#7367F0]/15 text-[#7367F0] flex items-center justify-center shrink-0">
              {renderIcon(Icon, 'w-4 h-4')}
            </div>
          )}
          <div>
            <h4 className="text-sm font-extrabold text-slate-800 dark:text-white leading-tight">
              {title}
            </h4>
            {subtitle && (
              <p className="text-[11px] text-slate-400 dark:text-[#7E7F96] mt-0.5">
                {subtitle}
              </p>
            )}
          </div>
        </div>

        {action && <div className="shrink-0">{action}</div>}
      </div>

      <div className="space-y-3.5">{children}</div>
    </div>
  );
};
