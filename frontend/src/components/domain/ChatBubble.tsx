import React from 'react';
import { Check, CheckCheck, AlertCircle } from 'lucide-react';
import { Message } from '../../types';
import { Tooltip } from '../ui/Tooltip';
import { useI18n } from '../../context/I18nContext';

export interface ChatBubbleProps {
  message: Message;
}

export const ChatBubble: React.FC<ChatBubbleProps> = ({ message }) => {
  const { t } = useI18n();
  const isInbound = message.direction === 'INBOUND';

  const formatTime = (dateStr?: string) => {
    if (!dateStr) return '';
    try {
      const d = new Date(dateStr);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  const renderStatusIcon = () => {
    if (isInbound) return null;
    switch (message.status) {
      case 'SENT':
        return (
          <Tooltip content={t('leads.msgSent')}>
            <Check className="w-3.5 h-3.5 text-white/70" />
          </Tooltip>
        );
      case 'DELIVERED':
        return (
          <Tooltip content={t('leads.msgDelivered')}>
            <CheckCheck className="w-3.5 h-3.5 text-white/70" />
          </Tooltip>
        );
      case 'READ':
        return (
          <Tooltip content={t('leads.msgRead')}>
            <CheckCheck className="w-3.5 h-3.5 text-cyan-200" />
          </Tooltip>
        );
      case 'FAILED':
        return (
          <Tooltip content={message.error_message || t('leads.msgFailed')}>
            <AlertCircle className="w-3.5 h-3.5 text-rose-300" />
          </Tooltip>
        );
      default:
        return null;
    }
  };

  return (
    <div className={`flex w-full mb-3 ${isInbound ? 'justify-start' : 'justify-end'}`}>
      <div
        className={`relative group max-w-[85%] sm:max-w-[75%] px-4 py-2.5 shadow-sm text-xs leading-relaxed transition-all duration-200 ${
          isInbound
            ? 'bg-slate-100 dark:bg-white/[0.08] text-slate-800 dark:text-slate-100 rounded-2xl rounded-tl-sm border border-slate-200/60 dark:border-white/[0.04]'
            : 'bg-[#7367F0] text-white rounded-2xl rounded-tr-sm shadow-[#7367F0]/20'
        }`}
      >
        {/* Message Content */}
        <p className="whitespace-pre-wrap break-words font-medium">
          {message.body || '[Medya içeriği]'}
        </p>

        {/* Footer info: time & status check */}
        <div
          className={`flex items-center justify-end space-x-1.5 mt-1.5 text-[10px] select-none ${
            isInbound ? 'text-slate-400 dark:text-slate-500' : 'text-white/80'
          }`}
        >
          <span>{formatTime(message.created_at || message.external_timestamp)}</span>
          {renderStatusIcon()}
        </div>
      </div>
    </div>
  );
};
