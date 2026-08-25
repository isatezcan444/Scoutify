import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface AccordionItem {
  id: string;
  title: React.ReactNode;
  content: React.ReactNode;
  icon?: React.ReactNode;
  badge?: React.ReactNode;
  defaultOpen?: boolean;
}

export interface AccordionProps {
  items: AccordionItem[];
  allowMultiple?: boolean;
  className?: string;
}

export const Accordion: React.FC<AccordionProps> = ({
  items,
  allowMultiple = false,
  className,
}) => {
  const [openIds, setOpenIds] = useState<string[]>(() =>
    items.filter((item) => item.defaultOpen).map((item) => item.id)
  );

  const toggleItem = (id: string) => {
    if (allowMultiple) {
      setOpenIds((prev) =>
        prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
      );
    } else {
      setOpenIds((prev) => (prev.includes(id) ? [] : [id]));
    }
  };

  return (
    <div className={cn('divide-y divide-slate-200/60 dark:divide-white/[0.06] rounded-xl border border-slate-200/80 dark:border-white/[0.08] overflow-hidden bg-white dark:bg-white/[0.02]', className)}>
      {items.map((item) => {
        const isOpen = openIds.includes(item.id);
        return (
          <div key={item.id} className="transition-colors">
            <button
              type="button"
              onClick={() => toggleItem(item.id)}
              className="w-full flex items-center justify-between p-4 text-left font-bold text-xs text-slate-800 dark:text-white hover:bg-slate-50 dark:hover:bg-white/[0.03] transition-colors cursor-pointer select-none"
            >
              <div className="flex items-center space-x-2.5 min-w-0">
                {item.icon && <span className="text-[#7367F0] shrink-0">{item.icon}</span>}
                <span className="truncate">{item.title}</span>
                {item.badge}
              </div>

              <ChevronDown
                className={cn(
                  'w-4 h-4 text-slate-400 transition-transform duration-200 shrink-0 ml-2',
                  isOpen && 'transform rotate-180 text-[#7367F0]'
                )}
              />
            </button>

            {isOpen && (
              <div className="p-4 pt-1 text-xs text-slate-600 dark:text-slate-300 leading-relaxed border-t border-slate-100 dark:border-white/[0.04] bg-slate-50/50 dark:bg-black/10 animate-fade-in">
                {item.content}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
