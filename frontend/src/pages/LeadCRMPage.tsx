import React, { useState, useEffect } from 'react';
import { 
  Users, 
  Search, 
  Download, 
  Plus, 
  Trash2, 
  Phone, 
  Star, 
  MapPin, 
  Send, 
  ShieldAlert, 
  Globe, 
  Loader2, 
  X, 
  MessageCircle,
  Navigation,
  ExternalLink
} from 'lucide-react';
import { WhatsAppIcon } from '../components/ui/whatsapp-icon';
import { ApiClient } from '../api/client';
import { Lead, LeadStatus } from '../types';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';

interface LeadCRMPageProps {
  onRefreshStats: () => void;
}

export const LeadCRMPage: React.FC<LeadCRMPageProps> = ({ onRefreshStats }) => {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [search, setSearch] = useState('');
  const [cityFilter, setCityFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [waOnly, setWaOnly] = useState(false);
  const [loading, setLoading] = useState(false);

  // Modals state
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isSendModalOpen, setIsSendModalOpen] = useState(false);
  const [selectedLeadForSend, setSelectedLeadForSend] = useState<Lead | null>(null);
  const [customMessage, setCustomMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [sendSuccessMsg, setSendSuccessMsg] = useState('');

  // New Lead Form State
  const [newLeadName, setNewLeadName] = useState('');
  const [newLeadPhone, setNewLeadPhone] = useState('');
  const [newLeadCategory, setNewLeadCategory] = useState('');
  const [newLeadCity, setNewLeadCity] = useState('');
  const [newLeadDistrict, setNewLeadDistrict] = useState('');
  const [formError, setFormError] = useState('');

  const fetchLeads = async () => {
    setLoading(true);
    try {
      const data = await ApiClient.getLeads({
        page,
        size: pageSize,
        search: search || undefined,
        city: cityFilter || undefined,
        category: categoryFilter || undefined,
        status: statusFilter || undefined,
        whatsapp_eligible_only: waOnly,
      });
      setLeads(data.items);
      setTotal(data.total);
    } catch (err) {
      console.error('Error fetching leads:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeads();
  }, [page, search, cityFilter, categoryFilter, statusFilter, waOnly]);

  const handleStatusChange = async (leadId: number, newStatus: LeadStatus) => {
    try {
      await ApiClient.updateLead(leadId, { status: newStatus });
      setLeads(leads.map((l) => (l.id === leadId ? { ...l, status: newStatus } : l)));
      onRefreshStats();
    } catch (err) {
      alert('Durum güncellenemedi');
    }
  };

  const handleDeleteLead = async (leadId: number) => {
    if (!confirm('Bu lead kaydını silmek istediğinize emin misiniz?')) return;
    try {
      await ApiClient.deleteLead(leadId);
      setLeads(leads.filter((l) => l.id !== leadId));
      setTotal((prev) => Math.max(0, prev - 1));
      onRefreshStats();
    } catch (err) {
      alert('Silme işlemi başarısız');
    }
  };

  const handleAddLead = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError('');
    if (!newLeadName || !newLeadPhone) {
      setFormError('İşletme adı ve telefon zorunludur.');
      return;
    }

    try {
      await ApiClient.createLead({
        name: newLeadName,
        phone: newLeadPhone,
        category: newLeadCategory || 'Genel',
        city: newLeadCity,
        district: newLeadDistrict,
      });
      setIsAddModalOpen(false);
      setNewLeadName('');
      setNewLeadPhone('');
      setNewLeadCategory('');
      setNewLeadCity('');
      setNewLeadDistrict('');
      fetchLeads();
      onRefreshStats();
    } catch (err: any) {
      setFormError(err.message || 'Lead eklenirken hata oluştu.');
    }
  };

  const openSendModal = (lead: Lead) => {
    setSelectedLeadForSend(lead);
    setCustomMessage(
      `Merhaba ${lead.name} yetkilisi, ${lead.city || 'bölgenizdeki'} işletmeniz için hazırladığımız randevu ve WhatsApp otomasyon sistemimizi incelemek ister misiniz?`
    );
    setSendSuccessMsg('');
    setIsSendModalOpen(true);
  };

  const handleSendSingleMessage = async () => {
    if (!selectedLeadForSend || !customMessage) return;
    setIsSending(true);
    try {
      await ApiClient.sendTestMessage(selectedLeadForSend.phone_e164, customMessage);
      setSendSuccessMsg(`✅ Mesaj ${selectedLeadForSend.phone_e164} numarasına başarıyla iletildi!`);
      handleStatusChange(selectedLeadForSend.id, 'CONTACTED' as LeadStatus);
      setTimeout(() => {
        setIsSendModalOpen(false);
      }, 1500);
    } catch (err: any) {
      alert(`Gönderim hatası: ${err.message}`);
    } finally {
      setIsSending(false);
    }
  };

  const handleAddToBlacklist = async (phone: string) => {
    if (!confirm(`${phone} numarasını kara listeye eklemek istediğinize emin misiniz? Artık hiçbir kampanya bu numaraya mesaj göndermeyecektir.`)) return;
    try {
      await ApiClient.addToBlacklist(phone, 'USER_REQUEST');
      alert(`${phone} kara listeye eklendi.`);
      fetchLeads();
    } catch (err: any) {
      alert(err.message);
    }
  };

  return (
    <div className="space-y-4 sm:space-y-6 pb-16 select-none animate-fade-in">
      {/* Top Action Bar & Filter Header */}
      <Card className="p-4 sm:p-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <h2 className="text-lg sm:text-xl font-extrabold text-slate-800 dark:text-white flex items-center gap-2">
              <Users className="w-5 h-5 text-[#7367F0]" />
              Müşteri Adayları & CRM ({total} Lead)
            </h2>
            <p className="text-xs text-slate-500 dark:text-[#7E7F96] mt-0.5 font-medium">
              Tüm taranan işletmeler, WhatsApp durumları ve iletişim geçmişi
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 sm:gap-2.5">
            <Button
              onClick={() => setIsAddModalOpen(true)}
              size="sm"
              className="space-x-1.5 font-bold shadow-md shadow-[#7367F0]/30 w-full sm:w-auto justify-center"
            >
              <Plus className="w-4 h-4" />
              <span>Yeni Lead Ekle</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => ApiClient.exportCsv({ search, city: cityFilter, status: statusFilter })}
              className="space-x-1.5 flex-1 sm:flex-initial justify-center"
            >
              <Download className="w-3.5 h-3.5" />
              <span>CSV İndir</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => ApiClient.exportExcel({ search, city: cityFilter, status: statusFilter })}
              className="space-x-1.5 flex-1 sm:flex-initial justify-center"
            >
              <Download className="w-3.5 h-3.5 text-[#28C76F]" />
              <span>Excel (.xlsx)</span>
            </Button>
          </div>
        </div>

        {/* Filter Controls Row */}
        <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3 pt-4 border-t border-slate-100 dark:border-white/[0.06]">
          {/* Search Box */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-3" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="İsim, telefon veya adres ara..."
              className="w-full pl-9 pr-3 py-2 rounded-lg vuexy-input text-xs font-medium"
            />
          </div>

          {/* City Filter */}
          <div>
            <input
              type="text"
              value={cityFilter}
              onChange={(e) => setCityFilter(e.target.value)}
              placeholder="Şehir filtrele (Örn: İstanbul)"
              className="w-full px-3 py-2 rounded-lg vuexy-input text-xs font-medium"
            />
          </div>

          {/* Category Filter */}
          <div>
            <input
              type="text"
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              placeholder="Kategori filtrele (Örn: Diş)"
              className="w-full px-3 py-2 rounded-lg vuexy-input text-xs font-medium"
            />
          </div>

          {/* Status Filter */}
          <div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full px-3 py-2 rounded-lg vuexy-input text-xs font-semibold"
            >
              <option value="">Tüm Durumlar</option>
              <option value="NEW">NEW (Yeni)</option>
              <option value="CONTACTED">CONTACTED (İletildi)</option>
              <option value="REPLIED">REPLIED (Yanıtlandı)</option>
              <option value="INTERESTED">INTERESTED (İlgileniyor)</option>
              <option value="UNSUBSCRIBED">UNSUBSCRIBED (Kara Liste)</option>
            </select>
          </div>

          {/* WhatsApp Eligible Toggle */}
          <div className="flex items-center">
            <label className="flex items-center space-x-2 text-xs text-slate-700 dark:text-slate-200 font-semibold cursor-pointer select-none">
              <input
                type="checkbox"
                checked={waOnly}
                onChange={(e) => setWaOnly(e.target.checked)}
                className="rounded border-slate-300 dark:border-slate-700 text-[#7367F0] focus:ring-0"
              />
              <span>Sadece WhatsApp Uyumlu</span>
            </label>
          </div>
        </div>
      </Card>

      {/* Leads Table Card */}
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/80 dark:bg-white/[0.02] text-slate-600 dark:text-slate-300 font-bold border-b border-slate-200/80 dark:border-white/[0.08]">
              <tr>
                <th className="py-3.5 px-4">İşletme Adı & Kategori</th>
                <th className="py-3.5 px-4">Telefon (E.164)</th>
                <th className="py-3.5 px-4">Lokasyon</th>
                <th className="py-3.5 px-4">Google Puanı</th>
                <th className="py-3.5 px-4">Durum</th>
                <th className="py-3.5 px-4 text-right">İşlemler</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-white/[0.05] text-slate-700 dark:text-slate-300 font-medium">
              {loading ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-400">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto text-[#7367F0]" />
                    <span className="mt-2 block font-semibold">Veriler yükleniyor...</span>
                  </td>
                </tr>
              ) : leads.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-400 font-semibold">
                    Kriterlere uygun müşteri adayı bulunamadı.
                  </td>
                </tr>
              ) : (
                leads.map((lead) => (
                  <tr key={lead.id} className="hover:bg-slate-50/60 dark:hover:bg-white/[0.02] transition-colors">
                    {/* Business Name */}
                    <td className="py-3.5 px-4">
                      <div className="font-bold text-slate-800 dark:text-white">{lead.name}</div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[10px] text-slate-400 font-medium">{lead.category || 'Genel'}</span>
                        {lead.website && (
                          <a
                            href={lead.website}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[10px] text-[#00CFE8] hover:underline flex items-center gap-0.5 font-bold"
                          >
                            <Globe className="w-2.5 h-2.5" />
                            Web
                          </a>
                        )}
                      </div>
                    </td>

                    {/* Phone */}
                    <td className="py-3.5 px-4 font-mono">
                      <div className="flex items-center space-x-1.5 text-slate-800 dark:text-slate-200 font-bold">
                        <span>{lead.phone_e164}</span>
                        {lead.is_whatsapp_eligible ? (
                          <span 
                            className="inline-flex items-center gap-0.5 px-1.5 py-0.2 rounded-full bg-[#25D366]/15 text-[#25D366] text-[10px] font-sans font-bold"
                            title="Doğrulanmış WhatsApp Numarası"
                          >
                            <WhatsAppIcon className="w-3 h-3 fill-current" />
                            <span>WA</span>
                          </span>
                        ) : (
                          <Badge variant="default" className="text-[8px] px-1 py-0 font-sans">
                            Sabit
                          </Badge>
                        )}
                      </div>
                      <div className="text-[10px] text-slate-400 font-sans">{lead.phone}</div>
                    </td>

                    {/* Location */}
                    <td className="py-3.5 px-4">
                      <div className="text-slate-800 dark:text-slate-200 font-semibold">
                        {lead.district ? `${lead.district}, ${lead.city}` : lead.city || 'Belirtilmedi'}
                      </div>
                      <div className="text-[10px] text-slate-400 line-clamp-1 max-w-xs font-normal">
                        {lead.address}
                      </div>
                    </td>

                    {/* Rating */}
                    <td className="py-3.5 px-4">
                      {lead.rating ? (
                        <div className="flex items-center space-x-1">
                          <Star className="w-3.5 h-3.5 text-[#FF9F43] fill-[#FF9F43]" />
                          <span className="font-bold text-slate-800 dark:text-white">{lead.rating}</span>
                          <span className="text-[10px] text-slate-400 font-normal">({lead.reviews_count || 0})</span>
                        </div>
                      ) : (
                        <span className="text-slate-400">-</span>
                      )}
                    </td>

                    {/* Status Dropdown */}
                    <td className="py-3.5 px-4">
                      <select
                        value={lead.status}
                        onChange={(e) => handleStatusChange(lead.id, e.target.value as LeadStatus)}
                        className={`text-[11px] font-bold px-2.5 py-1 rounded-md border focus:outline-none ${
                          lead.status === 'NEW'
                            ? 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-300 dark:border-slate-700'
                            : lead.status === 'CONTACTED'
                            ? 'bg-[#00CFE8]/15 text-[#00CFE8] border-[#00CFE8]/30'
                            : lead.status === 'REPLIED'
                            ? 'bg-[#28C76F]/15 text-[#28C76F] border-[#28C76F]/30'
                            : lead.status === 'INTERESTED'
                            ? 'bg-[#7367F0]/15 text-[#7367F0] border-[#7367F0]/30'
                            : 'bg-[#EA5455]/15 text-[#EA5455] border-[#EA5455]/30'
                        }`}
                      >
                        <option value="NEW">NEW</option>
                        <option value="CONTACTED">CONTACTED</option>
                        <option value="REPLIED">REPLIED</option>
                        <option value="INTERESTED">INTERESTED</option>
                        <option value="UNSUBSCRIBED">UNSUBSCRIBED</option>
                      </select>
                    </td>

                    {/* Action Buttons */}
                    <td className="py-3.5 px-4 text-right space-x-1.5 whitespace-nowrap">
                      <a
                        href={lead.latitude && lead.longitude && lead.latitude !== 0 ? `https://www.google.com/maps/search/?api=1&query=${lead.latitude},${lead.longitude}` : `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(lead.name + ' ' + (lead.address || '') + ' ' + (lead.city || ''))}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        title="Google Maps'te Aç"
                        className="inline-flex p-1.5 rounded-md bg-[#28C76F]/10 hover:bg-[#28C76F]/20 text-[#28C76F] border border-[#28C76F]/20 transition-all active:scale-95 align-middle"
                      >
                        <Navigation className="w-3.5 h-3.5" />
                      </a>
                      <button
                        onClick={() => openSendModal(lead)}
                        title="Doğrudan WhatsApp Mesajı Gönder"
                        className="p-1.5 rounded-md bg-[#7367F0]/10 hover:bg-[#7367F0]/20 text-[#7367F0] border border-[#7367F0]/20 transition-all active:scale-95 align-middle"
                      >
                        <MessageCircle className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleAddToBlacklist(lead.phone_e164)}
                        title="Kara Listeye Ekle"
                        className="p-1.5 rounded-md bg-slate-100 dark:bg-white/[0.04] hover:bg-[#EA5455]/15 text-slate-500 hover:text-[#EA5455] border border-slate-200 dark:border-white/[0.06] transition-all active:scale-95 align-middle"
                      >
                        <ShieldAlert className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleDeleteLead(lead.id)}
                        title="Sil"
                        className="p-1.5 rounded-md bg-slate-100 dark:bg-white/[0.04] hover:bg-[#EA5455]/15 text-slate-500 hover:text-[#EA5455] border border-slate-200 dark:border-white/[0.06] transition-all active:scale-95 align-middle"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Send Message Direct Modal */}
      {isSendModalOpen && selectedLeadForSend && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="vuexy-card max-w-lg w-full p-6 space-y-4 shadow-xl border border-slate-200 dark:border-white/[0.1]">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <MessageCircle className="w-5 h-5 text-[#28C76F]" />
                <h3 className="text-base font-bold text-slate-800 dark:text-white">
                  Doğrudan WhatsApp Mesajı Gönder
                </h3>
              </div>
              <button
                onClick={() => setIsSendModalOpen(false)}
                className="text-slate-400 hover:text-slate-700 dark:hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-3 rounded-lg bg-slate-50 dark:bg-[#25293C] border border-slate-200/80 dark:border-white/[0.08] text-xs space-y-1">
              <p className="text-slate-700 dark:text-slate-300">
                <strong className="text-slate-900 dark:text-white">Alıcı:</strong> {selectedLeadForSend.name}
              </p>
              <p className="text-[#7367F0] font-mono font-bold">
                <strong>Numara:</strong> {selectedLeadForSend.phone_e164}
              </p>
            </div>

            <div>
              <label className="text-xs font-bold text-slate-700 dark:text-slate-300 block mb-1.5">
                Mesaj Metni
              </label>
              <textarea
                value={customMessage}
                onChange={(e) => setCustomMessage(e.target.value)}
                rows={5}
                className="w-full p-3 rounded-lg vuexy-input text-xs leading-relaxed"
                placeholder="Gönderilecek mesaj..."
              />
            </div>

            {sendSuccessMsg && (
              <div className="p-3 rounded-lg bg-[#28C76F]/15 border border-[#28C76F]/30 text-[#28C76F] text-xs font-bold">
                {sendSuccessMsg}
              </div>
            )}

            <div className="flex items-center justify-end space-x-2 pt-2">
              <Button
                variant="ghost"
                onClick={() => setIsSendModalOpen(false)}
              >
                Kapat
              </Button>
              <Button
                variant="success"
                onClick={handleSendSingleMessage}
                disabled={isSending || !customMessage}
                className="space-x-1.5 font-bold shadow-md shadow-[#28C76F]/30"
              >
                {isSending ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>İletiliyor...</span>
                  </>
                ) : (
                  <>
                    <Send className="w-3.5 h-3.5" />
                    <span>WhatsApp Mesajını Gönder</span>
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Add Lead Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <form 
            onSubmit={handleAddLead} 
            className="vuexy-card max-w-md w-full p-6 space-y-4 shadow-xl border border-slate-200 dark:border-white/[0.1]"
          >
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-800 dark:text-white flex items-center gap-2">
                <Plus className="w-4 h-4 text-[#7367F0]" />
                Manuel Lead Ekle
              </h3>
              <button
                type="button"
                onClick={() => setIsAddModalOpen(false)}
                className="text-slate-400 hover:text-slate-700 dark:hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {formError && (
              <div className="p-2.5 rounded-lg bg-[#EA5455]/15 border border-[#EA5455]/30 text-[#EA5455] text-xs font-semibold">
                {formError}
              </div>
            )}

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-slate-700 dark:text-slate-300 font-bold block mb-1">İşletme Adı *</label>
                <input
                  type="text"
                  value={newLeadName}
                  onChange={(e) => setNewLeadName(e.target.value)}
                  placeholder="Örn: Dentapol Ağız Sağlığı"
                  className="w-full px-3 py-2 rounded-lg vuexy-input text-xs font-medium"
                  required
                />
              </div>

              <div>
                <label className="text-slate-700 dark:text-slate-300 font-bold block mb-1">Telefon Numarası *</label>
                <input
                  type="text"
                  value={newLeadPhone}
                  onChange={(e) => setNewLeadPhone(e.target.value)}
                  placeholder="Örn: 0532 123 45 67 veya +90532..."
                  className="w-full px-3 py-2 rounded-lg vuexy-input text-xs font-mono font-bold"
                  required
                />
                <p className="text-[10px] text-slate-400 mt-1 font-medium">
                  Otomatik E.164 uluslararası standardına dönüştürülür.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-slate-700 dark:text-slate-300 font-bold block mb-1">Kategori</label>
                  <input
                    type="text"
                    value={newLeadCategory}
                    onChange={(e) => setNewLeadCategory(e.target.value)}
                    placeholder="Diş Kliniği"
                    className="w-full px-3 py-2 rounded-lg vuexy-input text-xs font-medium"
                  />
                </div>
                <div>
                  <label className="text-slate-700 dark:text-slate-300 font-bold block mb-1">Şehir</label>
                  <input
                    type="text"
                    value={newLeadCity}
                    onChange={(e) => setNewLeadCity(e.target.value)}
                    placeholder="İstanbul"
                    className="w-full px-3 py-2 rounded-lg vuexy-input text-xs font-medium"
                  />
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end space-x-2 pt-3">
              <Button
                type="button"
                variant="ghost"
                onClick={() => setIsAddModalOpen(false)}
              >
                İptal
              </Button>
              <Button
                type="submit"
                className="font-bold shadow-md shadow-[#7367F0]/30"
              >
                Kaydet
              </Button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
