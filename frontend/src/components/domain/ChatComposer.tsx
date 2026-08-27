import React, { useState } from 'react';
import { Send, Lock, Smile, Paperclip } from 'lucide-react';
import { Button } from '../ui/button';
import { Tooltip } from '../ui/Tooltip';
import { useI18n } from '../../context/I18nContext';

export interface ChatComposerProps {
  onSend?: (text: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export const ChatComposer: React.FC<ChatComposerProps> = ({
  disabled = true, // Default to safe disabled mode in test phase
  placeholder,
}) => {
  const { t } = useI18n();
  const [text, setText] = useState('');

  return (
    <div className="p-3 border-t border-slate-200/80 dark:border-white/[0.08] bg-slate-50/50 dark:bg-black/20">
      {/* Safe Mode Notice */}
      {disabled && (
        <div className="flex items-center space-x-1.5 mb-2 px-2.5 py-1 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-600 dark:text-amber-400 text-[10px] font-semibold">
          <Lock className="w-3 h-3 shrink-0" />
          <span>{t('leads.readOnlyComposerTooltip')}</span>
        </div>
      )}

      <div className="flex items-center space-x-2">
        <div className="relative flex-1">
          <input
            type="text"
            value={text}
            disabled={disabled}
            onChange={(e) => setText(e.target.value)}
            placeholder={placeholder || t('leads.typeMessagePlaceholder')}
            className={`w-full px-3 py-2 pr-16 text-xs rounded-xl vuexy-input transition-all ${
              disabled
                ? 'opacity-60 cursor-not-allowed bg-slate-100 dark:bg-white/[0.04]'
                : ''
            }`}
          />
          <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center space-x-1 text-slate-400">
            <button type="button" disabled className="p-1 hover:text-slate-600 dark:hover:text-slate-200 disabled:opacity-40">
              <Smile className="w-3.5 h-3.5" />
            </button>
            <button type="button" disabled className="p-1 hover:text-slate-600 dark:hover:text-slate-200 disabled:opacity-40">
              <Paperclip className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <Tooltip content={t('leads.readOnlyComposerTooltip')}>
          <div>
            <Button
              size="sm"
              disabled={disabled || !text.trim()}
              className="bg-[#25D366] hover:bg-[#1EBE5D] text-white px-3.5 py-2 font-bold cursor-not-allowed opacity-60 shadow-sm"
            >
              <Send className="w-3.5 h-3.5" />
            </Button>
          </div>
        </Tooltip>
      </div>
    </div>
  );
};
