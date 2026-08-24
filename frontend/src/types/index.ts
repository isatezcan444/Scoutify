export type LeadStatus = 'NEW' | 'CONTACTED' | 'REPLIED' | 'INTERESTED' | 'UNSUBSCRIBED' | 'INVALID_NUMBER';

export interface Lead {
  id: number;
  name: string;
  category?: string;
  phone: string;
  phone_e164: string;
  is_mobile: boolean;
  is_whatsapp_eligible: boolean;
  address?: string;
  city?: string;
  district?: string;
  website?: string;
  email?: string;
  latitude?: number;
  longitude?: number;
  maps_url?: string;
  rating?: number;
  reviews_count?: number;
  search_keyword?: string;
  search_location?: string;
  status: LeadStatus;
  entity_type?: 'BUSINESS' | 'CLINIC' | 'COMPANY' | 'PROFESSIONAL' | 'PERSON' | 'DIRECTORY_PROFILE' | 'UNKNOWN';
  verification_status?: 'VERIFIED' | 'UNVERIFIED' | 'REJECTED';
  confidence_level?: 'HIGH' | 'MEDIUM' | 'LOW';
  confidence_score?: number;
  is_verified?: boolean;
  canonical_category?: string;
  category_score?: number;
  category_classification?: 'MATCH' | 'PARTIAL_MATCH' | 'RELATED' | 'AMBIGUOUS' | 'MISMATCH';
  discovered_from?: string;
  verified_by?: string;
  verification_trace?: any;
  notes?: string;
  created_at: string;
  updated_at: string;
  last_contacted_at?: string;
}

export type CampaignStatus = 'DRAFT' | 'ACTIVE' | 'PAUSED' | 'COMPLETED' | 'ARCHIVED';

export interface Campaign {
  id: number;
  name: string;
  description?: string;
  message_template: string;
  status: CampaignStatus;
  min_delay_seconds: number;
  max_delay_seconds: number;
  typing_delay_seconds: number;
  working_hours_enabled: boolean;
  working_hours_start: string;
  working_hours_end: string;
  session_id?: number;
  total_leads_target: number;
  sent_count: number;
  delivered_count: number;
  replied_count: number;
  failed_count: number;
  created_at: string;
  updated_at: string;
}

export type SessionStatus = 'DISCONNECTED' | 'SCAN_QR' | 'CONNECTING' | 'CONNECTED' | 'BANNED';

export interface WhatsAppSession {
  id: number;
  session_name: string;
  phone_number?: string;
  status: SessionStatus;
  qr_code?: string;
  is_active: boolean;
  warm_up_day: number;
  daily_sent_count: number;
  max_daily_limit: number;
  is_phone_online: boolean;
  battery_level?: number;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface DashboardStats {
  total_leads: number;
  whatsapp_eligible_leads: number;
  contacted_leads: number;
  replied_leads: number;
  response_rate_percentage: number;
  total_campaigns: number;
  active_campaigns: number;
  connected_sessions: number;
  total_messages_sent: number;
  messages_sent_today: number;
  daily_volume: Array<{
    date: string;
    sent_messages: number;
    leads_scraped: number;
  }>;
  leads_by_status: Record<string, number>;
  top_categories: Array<{
    category: string;
    count: number;
  }>;
  recent_activity: Array<{
    id: number;
    phone: string;
    status: string;
    time: string;
    message_snippet: string;
  }>;
}

export interface ScraperJob {
  id: number;
  keyword: string;
  location: string;
  city?: string;
  districts_json?: string[];
  source: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  total_found: number;
  total_valid_phones: number;
  total_new_leads: number;
  duration_seconds: number;
  created_at: string;
}

export interface MessageLog {
  id: number;
  lead_id: number;
  campaign_id?: number;
  session_id?: number;
  target_phone: string;
  rendered_message: string;
  status: string;
  wa_message_id?: string;
  reply_received: boolean;
  reply_text?: string;
  delay_applied_seconds?: number;
  sent_at?: string;
  created_at: string;
}

export interface BlacklistEntry {
  id: number;
  phone_e164: string;
  reason: string;
  notes?: string;
  created_at: string;
}
