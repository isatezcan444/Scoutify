import * as React from 'react';
import { Check } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface StepItem {
  id: string | number;
  title: string;
  subtitle?: string;
  icon?: React.ReactNode;
}

export interface StepperProps {
  steps: StepItem[];
  currentStep: number; // 0-indexed
  onStepClick?: (stepIndex: number) => void;
  className?: string;
}

export const Stepper: React.FC<StepperProps> = ({
  steps,
  currentStep,
  onStepClick,
  className,
}) => {
  return (
    <div className={cn('w-full flex items-center justify-between', className)}>
      {steps.map((step, idx) => {
        const isCompleted = idx < currentStep;
        const isActive = idx === currentStep;
        const isLast = idx === steps.length - 1;

        return (
          <React.Fragment key={String(step.id)}>
            <div
              onClick={() => onStepClick && onStepClick(idx)}
              className={cn(
                'flex items-center space-x-3 select-none',
                onStepClick && 'cursor-pointer'
              )}
            >
              {/* Step Circle */}
              <div
                className={cn(
                  'w-9 h-9 rounded-xl flex items-center justify-center font-bold text-xs transition-all duration-200 shadow-xs shrink-0',
                  isCompleted
                    ? 'bg-[#28C76F] text-white'
                    : isActive
                    ? 'bg-[#7367F0] text-white ring-4 ring-[#7367F0]/20'
                    : 'bg-slate-100 dark:bg-white/[0.06] text-slate-500 dark:text-[#7E7F96]'
                )}
              >
                {isCompleted ? (
                  <Check className="w-4 h-4 stroke-[3]" />
                ) : (
                  <span>{idx + 1}</span>
                )}
              </div>

              {/* Step Label */}
              <div className="hidden sm:block">
                <div
                  className={cn(
                    'text-xs font-bold leading-tight',
                    isActive
                      ? 'text-slate-800 dark:text-white'
                      : 'text-slate-500 dark:text-[#7E7F96]'
                  )}
                >
                  {step.title}
                </div>
                {step.subtitle && (
                  <div className="text-[10px] text-slate-400 dark:text-[#7E7F96]/80 mt-0.5">
                    {step.subtitle}
                  </div>
                )}
              </div>
            </div>

            {/* Connecting Track Line */}
            {!isLast && (
              <div
                className={cn(
                  'flex-1 h-[2px] mx-3 transition-colors duration-200',
                  idx < currentStep
                    ? 'bg-[#28C76F]'
                    : 'bg-slate-200 dark:bg-white/[0.08]'
                )}
              />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};
