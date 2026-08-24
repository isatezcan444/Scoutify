import { Lead, Campaign, WhatsAppSession, DashboardStats, ScraperJob, MessageLog, BlacklistEntry } from '../types';

const API_BASE = 'http://localhost:8000/api/v1';
const WS_URL = 'ws://localhost:8000/ws';

export class ApiClient {
  // --- Analytics ---
  static async getDashboardStats(): Promise<DashboardStats> {
    const res = await fetch(`${API_BASE}/analytics/dashboard`);
    if (!res.ok) throw new Error('Failed to fetch dashboard stats');
    return res.json();
  }

  // --- Leads ---
  static async getLeads(params: {
    page?: number;
    size?: number;
    search?: string;
    city?: string;
    district?: string;
    districts?: string[];
    category?: string;
    categories?: string[];
    status?: string;
    whatsapp_eligible_only?: boolean;
  }): Promise<{ items: Lead[]; total: number; page: number; size: number; pages: number }> {
    const query = new URLSearchParams();
    if (params.page) query.set('page', params.page.toString());
    if (params.size) query.set('size', params.size.toString());
    if (params.search) query.set('search', params.search);
    if (params.city) query.set('city', params.city);
    if (params.district) query.set('district', params.district);
    if (params.districts && params.districts.length > 0) {
      params.districts.forEach(d => query.append('districts', d));
    }
    if (params.category) query.set('category', params.category);
    if (params.categories && params.categories.length > 0) {
      params.categories.forEach(c => query.append('categories', c));
    }
    if (params.status) query.set('status', params.status);
    if (params.whatsapp_eligible_only) query.set('whatsapp_eligible_only', 'true');

    const res = await fetch(`${API_BASE}/leads?${query.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch leads');
    return res.json();
  }

  static async createLead(lead: Partial<Lead>): Promise<Lead> {
    const res = await fetch(`${API_BASE}/leads`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(lead)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Lead oluşturulamadı');
    }
    return res.json();
  }

  static async updateLead(id: number, lead: Partial<Lead>): Promise<Lead> {
    const res = await fetch(`${API_BASE}/leads/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(lead)
    });
    if (!res.ok) throw new Error('Lead güncellenemedi');
    return res.json();
  }

  static async deleteLead(id: number): Promise<void> {
    const res = await fetch(`${API_BASE}/leads/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Lead silinemedi');
  }

  static async bulkDeleteLeads(payload: {
    lead_ids?: number[];
    delete_all_matching?: boolean;
    search?: string;
    city?: string;
    districts?: string[];
    categories?: string[];
    status?: string;
    whatsapp_eligible_only?: boolean;
  }): Promise<{ deleted_count: number }> {
    const res = await fetch(`${API_BASE}/leads/bulk-delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('Toplu silme işlemi başarısız oldu');
    return res.json();
  }

  static async bulkBlacklistLeads(payload: {
    lead_ids: number[];
    reason?: string;
  }): Promise<{ blacklisted_count: number; leads_updated: number }> {
    const res = await fetch(`${API_BASE}/leads/bulk-blacklist`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('Toplu kara listeye ekleme işlemi başarısız oldu');
    return res.json();
  }

  static async exportCsv(filters: any = {}): Promise<void> {
    const res = await fetch(`${API_BASE}/leads/export/csv`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(filters)
    });
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `scoutify_leads_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
  }

  static async exportExcel(filters: any = {}): Promise<void> {
    const res = await fetch(`${API_BASE}/leads/export/excel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(filters)
    });
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `scoutify_leads_${new Date().toISOString().slice(0,10)}.xlsx`;
    a.click();
  }

  // --- Scraper ---
  static async startScraper(params: { keyword: string; city: string; districts: string[]; max_results: number }): Promise<ScraperJob> {
    const res = await fetch(`${API_BASE}/scraper/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Tarama başlatılamadı');
    }
    return res.json();
  }

  static async cancelScraper(jobId: number): Promise<ScraperJob> {
    const res = await fetch(`${API_BASE}/scraper/cancel/${jobId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    if (!res.ok) throw new Error('Tarama iptal edilemedi');
    return res.json();
  }

  static async getScraperJobs(): Promise<ScraperJob[]> {
    const res = await fetch(`${API_BASE}/scraper/jobs`);
    if (!res.ok) throw new Error('Failed to fetch scraper jobs');
    return res.json();
  }

  // --- Campaigns ---
  static async getCampaigns(): Promise<Campaign[]> {
    const res = await fetch(`${API_BASE}/campaigns`);
    if (!res.ok) throw new Error('Failed to fetch campaigns');
    return res.json();
  }

  static async createCampaign(campaign: Partial<Campaign>): Promise<Campaign> {
    const res = await fetch(`${API_BASE}/campaigns`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(campaign)
    });
    if (!res.ok) throw new Error('Kampanya oluşturulamadı');
    return res.json();
  }

  static async previewSpintax(template: string, count: number = 5): Promise<{ permutations_count: number; samples: string[] }> {
    const res = await fetch(`${API_BASE}/campaigns/spintax/preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ template, count })
    });
    if (!res.ok) throw new Error('Spintax önizleme hatası');
    return res.json();
  }

  static async launchCampaign(campaignId: number, params: { lead_ids?: number[]; limit?: number } = {}): Promise<any> {
    const res = await fetch(`${API_BASE}/campaigns/${campaignId}/launch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    });
    if (!res.ok) throw new Error('Kampanya başlatılamadı');
    return res.json();
  }

  // --- WhatsApp ---
  static async getWhatsAppSessions(): Promise<WhatsAppSession[]> {
    const res = await fetch(`${API_BASE}/whatsapp/sessions`);
    if (!res.ok) throw new Error('Failed to fetch WhatsApp sessions');
    return res.json();
  }

  static async createWhatsAppSession(name: string, maxDailyLimit: number = 50): Promise<WhatsAppSession> {
    const res = await fetch(`${API_BASE}/whatsapp/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_name: name, max_daily_limit: maxDailyLimit })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Oturum oluşturulamadı');
    }
    return res.json();
  }

  static async simulateConnectSession(sessionId: number): Promise<any> {
    const res = await fetch(`${API_BASE}/whatsapp/sessions/${sessionId}/connect-demo`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error('Oturum bağlanamadı');
    return res.json();
  }

  static async disconnectSession(sessionId: number): Promise<any> {
    const res = await fetch(`${API_BASE}/whatsapp/sessions/${sessionId}/disconnect`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error('Oturum kesilemedi');
    return res.json();
  }

  static async deleteSession(sessionId: number): Promise<void> {
    const res = await fetch(`${API_BASE}/whatsapp/sessions/${sessionId}`, {
      method: 'DELETE'
    });
    if (!res.ok) throw new Error('Oturum silinemedi');
  }

  static async sendTestMessage(phone: string, message: string, sessionId?: number): Promise<any> {
    const res = await fetch(`${API_BASE}/whatsapp/send-test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone_e164: phone, message, session_id: sessionId })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Test mesajı gönderilemedi');
    }
    return res.json();
  }

  static async getMessageLogs(): Promise<MessageLog[]> {
    const res = await fetch(`${API_BASE}/whatsapp/logs`);
    if (!res.ok) throw new Error('Failed to fetch message logs');
    return res.json();
  }

  // --- Blacklist ---
  static async getBlacklist(): Promise<BlacklistEntry[]> {
    const res = await fetch(`${API_BASE}/blacklist`);
    if (!res.ok) throw new Error('Failed to fetch blacklist');
    return res.json();
  }

  static async addToBlacklist(phone: string, reason: string = 'USER_REQUEST'): Promise<BlacklistEntry> {
    const res = await fetch(`${API_BASE}/blacklist`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone_e164: phone, reason })
    });
    if (!res.ok) throw new Error('Numara kara listeye eklenemedi');
    return res.json();
  }

  static async removeFromBlacklist(id: number): Promise<void> {
    const res = await fetch(`${API_BASE}/blacklist/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Numara kara listeden silinemedi');
  }
}

export function createWebSocket(onMessage: (data: any) => void) {
  const ws = new WebSocket(WS_URL);
  
  ws.onopen = () => {
    console.log('[Scoutify WS] Connected to realtime event stream');
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (e) {
      // ignore plain text ping/pong
    }
  };

  ws.onerror = (err) => {
    console.warn('[Scoutify WS] Error:', err);
  };

  return ws;
}
