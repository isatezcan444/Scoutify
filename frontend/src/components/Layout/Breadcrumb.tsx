import * as React from 'react';
import { ChevronRight, Home } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface BreadcrumbItem {
  label: string;
  href?: string;
  onClick?: () => void;
  icon?: React.ReactNode;
}

export interface BreadcrumbProps {
  items: BreadcrumbItem[];
  className?: string;
}

export const Breadcrumb: React.FC<BreadcrumbProps> = ({ items, className }) => {
  return (
    <nav className={cn('flex items-center space-x-1.5 text-xs text-slate-400 font-medium', className)} aria-label="Breadcrumb">
      <div className="flex items-center space-x-1 hover:text-slate-700 dark:hover:text-slate-200 transition-colors">
        <Home className="w-3.5 h-3.5 text-slate-400" />
      </div>

      {items.map((item, idx) => {
        const isLast = idx === items.length - 1;
        return (
          <React.Fragment key={idx}>
            <ChevronRight className="w-3 h-3 text-slate-400/60 shrink-0" />
            {isLast ? (
              <span className="font-bold text-slate-700 dark:text-slate-200 select-none">
                {item.label}
              </span>
            ) : item.onClick ? (
              <button
                type="button"
                onClick={item.onClick}
                className="hover:text-[#7367F0] transition-colors cursor-pointer"
              >
                {item.label}
              </button>
            ) : (
              <span className="hover:text-slate-700 dark:hover:text-slate-200 transition-colors">
                {item.label}
              </span>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
};
