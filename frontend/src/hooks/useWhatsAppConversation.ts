import { useState, useEffect, useCallback, useRef } from 'react';
import { ApiClient } from '../api/client';
import { ConversationDetail, Message } from '../types';

interface UseWhatsAppConversationOptions {
  leadId?: number;
  conversationId?: number;
  enabled?: boolean;
  autoMarkAsRead?: boolean;
  initialLimit?: number;
}

export function useWhatsAppConversation({
  leadId,
  conversationId,
  enabled = true,
  autoMarkAsRead = true,
  initialLimit = 50,
}: UseWhatsAppConversationOptions) {
  const [conversation, setConversation] = useState<ConversationDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [loadingOlder, setLoadingOlder] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const isFetchingOlderRef = useRef(false);

  const fetchConversation = useCallback(async () => {
    if (!enabled || (!leadId && !conversationId)) {
      setConversation(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      let data: ConversationDetail;
      if (leadId) {
        data = await ApiClient.getLeadConversation(leadId, { limit: initialLimit });
      } else if (conversationId) {
        data = await ApiClient.getConversation(conversationId, { limit: initialLimit });
      } else {
        return;
      }
      setConversation(data);

      // Auto mark as read when opened if there are unread messages
      if (autoMarkAsRead && data.unread_count > 0) {
        try {
          await ApiClient.markConversationAsRead(data.id);
          setConversation((prev) => (prev ? { ...prev, unread_count: 0 } : null));
        } catch (e) {
          console.warn('[useWhatsAppConversation] Mark as read failed:', e);
        }
      }
    } catch (err: any) {
      console.error('[useWhatsAppConversation] Fetch error:', err);
      setError(err.message || 'Failed to load conversation');
    } finally {
      setLoading(false);
    }
  }, [leadId, conversationId, enabled, autoMarkAsRead, initialLimit]);

  useEffect(() => {
    fetchConversation();
  }, [fetchConversation]);

  // Load older messages for pagination
  const loadOlderMessages = useCallback(async () => {
    if (!conversation || !conversation.has_more || isFetchingOlderRef.current) {
      return;
    }

    const oldestId = conversation.oldest_message_id || conversation.messages[0]?.id;
    if (!oldestId) return;

    isFetchingOlderRef.current = true;
    setLoadingOlder(true);

    try {
      const res = await ApiClient.getConversationMessages(conversation.id, {
        limit: 30,
        before: oldestId,
      });

      if (res.messages.length > 0) {
        setConversation((prev) => {
          if (!prev) return prev;
          // Filter out any messages already present in state
          const existingIds = new Set(prev.messages.map((m) => m.id));
          const existingWaIds = new Set(prev.messages.map((m) => m.wa_message_id).filter(Boolean));
          const uniqueNew = res.messages.filter(
            (m) => !existingIds.has(m.id) && (!m.wa_message_id || !existingWaIds.has(m.wa_message_id))
          );

          return {
            ...prev,
            has_more: res.has_more,
            oldest_message_id: res.oldest_message_id || (uniqueNew[0]?.id ?? prev.oldest_message_id),
            messages: [...uniqueNew, ...prev.messages],
          };
        });
      } else {
        setConversation((prev) => (prev ? { ...prev, has_more: false } : null));
      }
    } catch (err: any) {
      console.error('[useWhatsAppConversation] Load older messages error:', err);
    } finally {
      setLoadingOlder(false);
      isFetchingOlderRef.current = false;
    }
  }, [conversation]);

  // Explicit mark as read helper
  const markAsRead = useCallback(async () => {
    if (!conversation) return;
    try {
      await ApiClient.markConversationAsRead(conversation.id);
      setConversation((prev) => (prev ? { ...prev, unread_count: 0 } : null));
    } catch (e) {
      console.warn('[useWhatsAppConversation] Mark as read failed:', e);
    }
  }, [conversation]);

  // Real-time Event Listener via CustomEvent bus
  useEffect(() => {
    const handleWsEvent = (e: Event) => {
      const customEvent = e as CustomEvent<any>;
      const eventData = customEvent.detail;
      if (!eventData) return;

      // Handle incoming message
      if (eventData.event === 'inbound_reply') {
        const matchesLead = leadId && eventData.lead_id === leadId;
        const matchesConvId = conversationId && eventData.conversation_id === conversationId;
        const matchesCurrentConv =
          conversation && (eventData.conversation_id === conversation.id || eventData.lead_id === conversation.lead_id);

        if (matchesLead || matchesConvId || matchesCurrentConv) {
          setConversation((prev) => {
            if (!prev) return prev;

            // Idempotency: check if message with this wa_message_id or id already exists
            const msgId = eventData.message_id;
            const waId = eventData.wa_message_id;
            const isDuplicate = prev.messages.some(
              (m) => (waId && m.wa_message_id === waId) || (msgId && m.id === msgId)
            );

            if (isDuplicate) return prev;

            const newMsg: Message = {
              id: eventData.message_id || Date.now(),
              conversation_id: prev.id,
              direction: eventData.direction || 'INBOUND',
              message_type: eventData.message_type || 'TEXT',
              status: eventData.status || 'RECEIVED',
              body: eventData.message,
              wa_message_id: eventData.wa_message_id,
              sender_phone: eventData.phone,
              created_at: eventData.created_at || new Date().toISOString(),
            };

            return {
              ...prev,
              last_message_at: newMsg.created_at,
              last_message_preview: newMsg.body,
              unread_count: autoMarkAsRead ? 0 : (prev.unread_count || 0) + 1,
              messages: [...prev.messages, newMsg],
            };
          });

          if (autoMarkAsRead && conversation) {
            ApiClient.markConversationAsRead(conversation.id).catch(() => {});
          }
        }
      }

      // Handle message status updates (SENT -> DELIVERED -> READ)
      if (eventData.event === 'message_status_updated') {
        const waId = eventData.message_id;
        const newStatus = eventData.status;

        setConversation((prev) => {
          if (!prev) return prev;
          let changed = false;
          const updatedMessages = prev.messages.map((m) => {
            if (m.wa_message_id === waId) {
              changed = true;
              return { ...m, status: newStatus, error_message: eventData.error_message };
            }
            return m;
          });

          if (!changed) return prev;
          return { ...prev, messages: updatedMessages };
        });
      }

      // Handle conversation read event
      if (eventData.event === 'conversation_read') {
        const matchesConv =
          (conversationId && eventData.conversation_id === conversationId) ||
          (conversation && eventData.conversation_id === conversation.id);

        if (matchesConv) {
          setConversation((prev) => (prev ? { ...prev, unread_count: 0 } : null));
        }
      }
    };

    window.addEventListener('scoutify:ws_event', handleWsEvent);
    return () => {
      window.removeEventListener('scoutify:ws_event', handleWsEvent);
    };
  }, [leadId, conversationId, conversation, autoMarkAsRead]);

  return {
    conversation,
    messages: conversation?.messages || [],
    hasMore: conversation?.has_more ?? false,
    loading,
    loadingOlder,
    error,
    refresh: fetchConversation,
    loadOlderMessages,
    markAsRead,
  };
}
