import React from 'react';
import { X } from 'lucide-react';
import { useI18n } from '../../context/I18nContext';
import { cn } from '../../lib/utils';

export interface BulkActionToolbarProps {
  selectedCount: number;
  totalCount: number;
  selectAllMatching: boolean;
  onSelectAllMatching?: () => void;
  onClearSelection: () => void;
  actions: React.ReactNode;
  className?: string;
}

export const BulkActionToolbar: React.FC<BulkActionToolbarProps> = ({
  selectedCount,
  totalCount,
  selectAllMatching,
  onSelectAllMatching,
  onClearSelection,
  actions,
  className,
}) => {
  const { t } = useI18n();

  if (selectedCount <= 0) return null;

  return (
    <div
      className={cn(
        'p-3.5 rounded-xl bg-gradient-to-r from-[#7367F0] to-[#867BFF] text-white shadow-lg shadow-[#7367F0]/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3 animate-fade-in select-none',
        className
      )}
    >
      <div className="flex items-center space-x-2.5 flex-wrap">
        <span className="w-7 h-7 rounded-lg bg-white/20 flex items-center justify-center font-bold text-xs shadow-inner">
          {selectedCount}
        </span>
        <span className="text-xs font-extrabold tracking-wide">
          {selectAllMatching
            ? t('leads.allMatchingSelected', { total: totalCount })
            : t('leads.bulkToolbarCount', { count: selectedCount })}
        </span>

        {/* Quick Link to Select All across all pages if available */}
        {!selectAllMatching && onSelectAllMatching && totalCount > selectedCount && (
          <button
            type="button"
            onClick={onSelectAllMatching}
            className="px-2.5 py-1 rounded-lg bg-white/20 hover:bg-white/30 text-white font-bold text-[11px] underline underline-offset-2 transition-all cursor-pointer"
          >
            {t('leads.selectAllTotal', { total: totalCount })}
          </button>
        )}
      </div>

      <div className="flex items-center space-x-2 flex-wrap sm:flex-nowrap">
        {actions}

        <button
          type="button"
          onClick={onClearSelection}
          className="p-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white/80 hover:text-white transition-colors cursor-pointer"
          title={t('common.clearSelection')}
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
