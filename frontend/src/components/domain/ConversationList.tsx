import React from 'react';
import { MessageSquare, Clock } from 'lucide-react';
import { Conversation } from '../../types';
import { Avatar } from '../ui/Avatar';
import { Badge } from '../ui/badge';
import { SearchInput } from '../forms/SearchInput';
import { Skeleton } from '../ui/Skeleton';
import { useI18n } from '../../context/I18nContext';

export interface ConversationListProps {
  conversations: Conversation[];
  selectedId?: number;
  onSelect: (conv: Conversation) => void;
  loading?: boolean;
  searchQuery?: string;
  onSearchChange?: (query: string) => void;
}

export const ConversationList: React.FC<ConversationListProps> = ({
  conversations,
  selectedId,
  onSelect,
  loading = false,
  searchQuery = '',
  onSearchChange,
}) => {
  const { t } = useI18n();

  const formatTime = (dateStr?: string) => {
    if (!dateStr) return '';
    try {
      const d = new Date(dateStr);
      const now = new Date();
      if (d.toDateString() === now.toDateString()) {
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      }
      return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    } catch {
      return '';
    }
  };

  const filtered = conversations.filter((c) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      c.lead_name?.toLowerCase().includes(q) ||
      c.lead_phone?.toLowerCase().includes(q) ||
      c.last_message_preview?.toLowerCase().includes(q)
    );
  });

  return (
    <div className="flex flex-col h-full border-r border-slate-200/80 dark:border-white/[0.08] bg-slate-50/50 dark:bg-black/10">
      {/* Search Header */}
      {onSearchChange && (
        <div className="p-3 border-b border-slate-200/80 dark:border-white/[0.08]">
          <SearchInput
            value={searchQuery}
            onChange={onSearchChange}
            placeholder={t('whatsapp.searchConversations')}
            sizeVariant="sm"
          />
        </div>
      )}

      {/* List content */}
      <div className="flex-1 overflow-y-auto divide-y divide-slate-100 dark:divide-white/[0.04]">
        {loading ? (
          <div className="p-3 space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="flex items-center space-x-3 p-2">
                <Skeleton className="w-10 h-10 rounded-xl shrink-0" />
                <div className="flex-1 space-y-1.5">
                  <Skeleton className="w-24 h-3.5" />
                  <Skeleton className="w-36 h-3" />
                </div>
              </div>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-6 text-center text-slate-400 dark:text-slate-500 text-xs">
            <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-40" />
            <p>{t('whatsapp.noConversations')}</p>
          </div>
        ) : (
          filtered.map((conv) => {
            const isSelected = selectedId === conv.id;
            return (
              <button
                key={conv.id}
                type="button"
                onClick={() => onSelect(conv)}
                className={`w-full text-left p-3.5 flex items-start space-x-3 transition-colors cursor-pointer ${
                  isSelected
                    ? 'bg-[#7367F0]/10 dark:bg-[#7367F0]/15 border-l-4 border-[#7367F0]'
                    : 'hover:bg-slate-100/60 dark:hover:bg-white/[0.04]'
                }`}
              >
                <Avatar name={conv.lead_name || conv.lead_phone || 'Lead'} size="md" shape="rounded" />

                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold text-xs text-slate-800 dark:text-slate-100 truncate">
                      {conv.lead_name || conv.lead_phone || `Lead #${conv.lead_id}`}
                    </h4>
                    <span className="text-[10px] text-slate-400 font-medium shrink-0 ml-1">
                      {formatTime(conv.last_message_at || conv.created_at)}
                    </span>
                  </div>

                  <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate mt-0.5">
                    {conv.last_message_preview || t('leads.noMessagesTitle')}
                  </p>

                  <div className="flex items-center justify-between mt-1.5">
                    <span className="text-[10px] font-mono text-slate-400">
                      {conv.lead_phone}
                    </span>
                    {conv.unread_count > 0 && (
                      <Badge variant="primary">
                        {conv.unread_count}
                      </Badge>
                    )}
                  </div>
                </div>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
};
