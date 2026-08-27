import { useState, useEffect, useCallback } from 'react';
import { ApiClient } from '../api/client';
import { ConversationDetail, Message } from '../types';

interface UseWhatsAppConversationOptions {
  leadId?: number;
  conversationId?: number;
  enabled?: boolean;
}

export function useWhatsAppConversation({
  leadId,
  conversationId,
  enabled = true,
}: UseWhatsAppConversationOptions) {
  const [conversation, setConversation] = useState<ConversationDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

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
        data = await ApiClient.getLeadConversation(leadId);
      } else if (conversationId) {
        data = await ApiClient.getConversation(conversationId);
      } else {
        return;
      }
      setConversation(data);
    } catch (err: any) {
      console.error('[useWhatsAppConversation] Fetch error:', err);
      setError(err.message || 'Failed to load conversation');
    } finally {
      setLoading(false);
    }
  }, [leadId, conversationId, enabled]);

  useEffect(() => {
    fetchConversation();
  }, [fetchConversation]);

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
        const matchesCurrentConv = conversation && (eventData.conversation_id === conversation.id || eventData.lead_id === conversation.lead_id);

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
              messages: [...prev.messages, newMsg],
            };
          });
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
    };

    window.addEventListener('scoutify:ws_event', handleWsEvent);
    return () => {
      window.removeEventListener('scoutify:ws_event', handleWsEvent);
    };
  }, [leadId, conversation]);

  return {
    conversation,
    messages: conversation?.messages || [],
    loading,
    error,
    refresh: fetchConversation,
  };
}
