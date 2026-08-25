import * as React from 'react';
import { cn } from '../../lib/utils';

export interface ButtonGroupProps {
  children: React.ReactNode;
  className?: string;
  orientation?: 'horizontal' | 'vertical';
}

export const ButtonGroup: React.FC<ButtonGroupProps> = ({
  children,
  className,
  orientation = 'horizontal',
}) => {
  return (
    <div
      role="group"
      className={cn(
        'inline-flex rounded-lg shadow-2xs',
        orientation === 'horizontal'
          ? 'flex-row [&>*:not(:first-child)]:rounded-l-none [&>*:not(:last-child)]:rounded-r-none [&>*:not(:first-child)]:-ml-[1px]'
          : 'flex-col [&>*:not(:first-child)]:rounded-t-none [&>*:not(:last-child)]:rounded-b-none [&>*:not(:first-child)]:-mt-[1px]',
        className
      )}
    >
      {children}
    </div>
  );
};
