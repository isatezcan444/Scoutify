import React, { useEffect, useRef } from 'react';
import { Message } from '../../types';
import { ChatBubble } from './ChatBubble';
import { EmptyState } from '../ui/EmptyState';
import { Skeleton } from '../ui/Skeleton';
import { WhatsAppIcon } from '../ui/whatsapp-icon';
import { useI18n } from '../../context/I18nContext';

export interface ChatThreadProps {
  messages: Message[];
  loading?: boolean;
  leadName?: string;
  leadPhone?: string;
}

export const ChatThread: React.FC<ChatThreadProps> = ({
  messages,
  loading = false,
}) => {
  const { t } = useI18n();
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages update
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const getDateLabel = (dateStr?: string) => {
    if (!dateStr) return '';
    try {
      const d = new Date(dateStr);
      const today = new Date();
      const yesterday = new Date();
      yesterday.setDate(today.getDate() - 1);

      if (d.toDateString() === today.toDateString()) {
        return t('leads.today');
      }
      if (d.toDateString() === yesterday.toDateString()) {
        return t('leads.yesterday');
      }
      return d.toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' });
    } catch {
      return '';
    }
  };

  if (loading) {
    return (
      <div className="flex-1 p-4 space-y-4 overflow-y-auto">
        <div className="flex justify-start">
          <Skeleton className="w-48 h-12 rounded-2xl rounded-tl-sm" />
        </div>
        <div className="flex justify-end">
          <Skeleton className="w-56 h-14 rounded-2xl rounded-tr-sm" />
        </div>
        <div className="flex justify-start">
          <Skeleton className="w-64 h-16 rounded-2xl rounded-tl-sm" />
        </div>
      </div>
    );
  }

  if (!messages || messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <EmptyState
          icon={WhatsAppIcon}
          title={t('leads.noMessagesTitle')}
          description={t('leads.noMessagesDesc')}
        />
      </div>
    );
  }

  // Group messages by date
  let lastDate = '';

  return (
    <div className="flex-1 p-4 overflow-y-auto space-y-1">
      {messages.map((msg) => {
        const currentDate = getDateLabel(msg.created_at || msg.external_timestamp);
        const showDateSeparator = currentDate && currentDate !== lastDate;
        if (showDateSeparator) {
          lastDate = currentDate;
        }

        return (
          <React.Fragment key={msg.wa_message_id || msg.id}>
            {showDateSeparator && (
              <div className="flex items-center justify-center my-4">
                <span className="px-3 py-1 rounded-full text-[10px] font-bold bg-slate-200/80 dark:bg-white/[0.08] text-slate-500 dark:text-slate-400 select-none shadow-xs">
                  {currentDate}
                </span>
              </div>
            )}
            <ChatBubble message={msg} />
          </React.Fragment>
        );
      })}
      <div ref={bottomRef} />
    </div>
  );
};
