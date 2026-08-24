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
  ExternalLink,
  RotateCcw,
  Layers,
  Check
} from 'lucide-react';
import { WhatsAppIcon } from '../components/ui/whatsapp-icon';
import { LocationMultiSelect } from '../components/LeadFinder/LocationMultiSelect';
import { CategoryMultiSelect } from '../components/LeadFinder/CategoryMultiSelect';
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
  
  // Search & Filter State
  const [search, setSearch] = useState('');
  const [selectedCity, setSelectedCity] = useState('');
  const [selectedDistricts, setSelectedDistricts] = useState<string[]>([]);
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
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
        city: selectedCity || undefined,
        districts: selectedDistricts.length > 0 ? selectedDistricts : undefined,
        categories: selectedCategories.length > 0 ? selectedCategories : undefined,
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
  }, [page, search, selectedCity, selectedDistricts, selectedCategories, statusFilter, waOnly]);

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
      setFormError(err.message || 'Eklenirken bir hata oluştu');
    }
  };

  const handleOpenSendModal = (lead: Lead) => {
    setSelectedLeadForSend(lead);
    setCustomMessage(`Merhaba ${lead.name} yetkilisi, işletmeniz için harika bir teklifimiz var!`);
    setSendSuccessMsg('');
    setIsSendModalOpen(true);
  };

  const handleSendSingleMessage = async () => {
    if (!selectedLeadForSend || !customMessage) return;
    setIsSending(true);
    setSendSuccessMsg('');

    try {
      await ApiClient.sendSingleMessage({
        phone: selectedLeadForSend.phone_e164 || selectedLeadForSend.phone,
        message: customMessage,
        lead_id: selectedLeadForSend.id,
      });

      setSendSuccessMsg('✅ Mesaj kuyruğa alındı ve iletildi!');
      setTimeout(() => {
        setIsSendModalOpen(false);
        fetchLeads();
        onRefreshStats();
      }, 1200);
    } catch (err: any) {
      alert(`Mesaj gönderilemedi: ${err.message}`);
    } finally {
      setIsSending(false);
    }
  };

  const handleBlacklistNumber = async (phone: string, reason: string) => {
    if (!confirm(`${phone} numarasını kara listeye eklemek istediğinize emin misiniz?`)) return;
    try {
      await ApiClient.addBlacklist({ phone, reason: reason || 'Kullanıcı talebi' });
      alert('Numara kara listeye eklendi');
      fetchLeads();
      onRefreshStats();
    } catch (err: any) {
      alert(`Hata: ${err.message}`);
    }
  };

  const hasActiveFilters = Boolean(
    search || selectedCity || selectedDistricts.length > 0 || selectedCategories.length > 0 || statusFilter || waOnly
  );

  const resetAllFilters = () => {
    setSearch('');
    setSelectedCity('');
    setSelectedDistricts([]);
    setSelectedCategories([]);
    setStatusFilter('');
    setWaOnly(false);
    setPage(1);
  };

  return (
    <div className="space-y-4 sm:space-y-6 pb-16 select-none animate-fade-in">
      {/* Top Action Bar & Filter Header */}
      <Card className="p-4 sm:p-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <h2 className="text-lg sm:text-xl font-extrabold text-slate-800 dark:text-white flex items-center gap-2">
              <Users className="w-5 h-5 text-[#7367F0]" />
              Müşteri Adayları ({total})
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
              onClick={() => ApiClient.exportCsv({ 
                search, 
                city: selectedCity, 
                districts: selectedDistricts,
                categories: selectedCategories,
                status: statusFilter 
              })}
              className="space-x-1.5 flex-1 sm:flex-initial justify-center"
            >
              <Download className="w-3.5 h-3.5" />
              <span>CSV İndir</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => ApiClient.exportExcel({ 
                search, 
                city: selectedCity, 
                districts: selectedDistricts,
                categories: selectedCategories,
                status: statusFilter 
              })}
              className="space-x-1.5 flex-1 sm:flex-initial justify-center"
            >
              <Download className="w-3.5 h-3.5 text-[#28C76F]" />
              <span>Excel (.xlsx)</span>
            </Button>
          </div>
        </div>

        {/* Filter Controls Row */}
        <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-12 gap-3 pt-4 border-t border-slate-100 dark:border-white/[0.06] items-center">
          {/* Search Box: 4 cols */}
          <div className="lg:col-span-4 relative flex items-center">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 pointer-events-none" />
            <input
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder="İsim, telefon veya adres ara..."
              className="w-full pl-9 pr-3 py-2 rounded-lg vuexy-input text-xs font-medium h-10"
            />
          </div>

          {/* Location Multi-Select (City + Districts): 3 cols */}
          <div className="lg:col-span-3 relative">
            <LocationMultiSelect
              selectedCity={selectedCity}
              selectedDistricts={selectedDistricts}
              onChange={(city, districts) => {
                setSelectedCity(city);
                setSelectedDistricts(districts);
                setPage(1);
              }}
              onCityChange={(city) => {
                setSelectedCity(city);
                setPage(1);
              }}
              onDistrictsChange={(districts) => {
                setSelectedDistricts(districts);
                setPage(1);
              }}
            />
          </div>

          {/* Category Multi-Select: 3 cols */}
          <div className="lg:col-span-3 relative">
            <CategoryMultiSelect
              selectedCategories={selectedCategories}
              onChange={(cats) => {
                setSelectedCategories(cats);
                setPage(1);
              }}
            />
          </div>

          {/* Status Filter: 2 cols */}
          <div className="lg:col-span-2">
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="w-full px-3 rounded-lg vuexy-input text-xs font-semibold h-10"
            >
              <option value="">Tüm Durumlar</option>
              <option value="NEW">NEW (Yeni)</option>
              <option value="CONTACTED">CONTACTED (İletildi)</option>
              <option value="REPLIED">REPLIED (Yanıtlandı)</option>
              <option value="INTERESTED">INTERESTED (İlgileniyor)</option>
              <option value="UNSUBSCRIBED">UNSUBSCRIBED (Kara Liste)</option>
            </select>
          </div>
        </div>

        {/* Second Row: WhatsApp Only Toggle & Active Filter Tags & Reset */}
        <div className="mt-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pt-3 border-t border-slate-100 dark:border-white/[0.04] text-xs">
          <div className="flex items-center space-x-2 flex-wrap gap-y-1.5">
            <label className="flex items-center space-x-2 text-xs text-slate-700 dark:text-slate-200 font-semibold cursor-pointer select-none bg-slate-50 dark:bg-white/[0.03] px-3 py-1.5 rounded-lg border border-slate-200/60 dark:border-white/[0.06]">
              <input
                type="checkbox"
                checked={waOnly}
                onChange={(e) => {
                  setWaOnly(e.target.checked);
                  setPage(1);
                }}
                className="rounded border-slate-300 dark:border-slate-700 text-[#7367F0] focus:ring-0"
              />
              <span>Sadece WhatsApp Uyumlu</span>
            </label>

            {/* Active Filters Summary Chips */}
            {selectedCity && (
              <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-1 rounded-lg bg-[#7367F0]/15 text-[#7367F0] dark:bg-[#7367F0]/25 dark:text-[#A59DF8]">
                <span>{selectedCity}</span>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedCity('');
                    setSelectedDistricts([]);
                    setPage(1);
                  }}
                  className="hover:text-[#EA5455] ml-0.5"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}

            {selectedDistricts.length > 0 && (
              <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-1 rounded-lg bg-slate-100 dark:bg-white/[0.06] text-slate-700 dark:text-slate-200">
                <span>{selectedDistricts.length} İlçe: {selectedDistricts.slice(0, 2).join(', ')}{selectedDistricts.length > 2 ? '...' : ''}</span>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedDistricts([]);
                    setPage(1);
                  }}
                  className="hover:text-[#EA5455] ml-0.5"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}

            {selectedCategories.length > 0 && (
              <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-1 rounded-lg bg-[#00CFE8]/15 text-[#00CFE8] dark:bg-[#00CFE8]/25 dark:text-[#00CFE8]">
                <span>{selectedCategories.length} Kategori: {selectedCategories.slice(0, 2).join(', ')}{selectedCategories.length > 2 ? '...' : ''}</span>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedCategories([]);
                    setPage(1);
                  }}
                  className="hover:text-[#EA5455] ml-0.5"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}
          </div>

          {hasActiveFilters && (
            <button
              type="button"
              onClick={resetAllFilters}
              className="text-xs font-bold text-slate-400 hover:text-[#EA5455] flex items-center gap-1.5 self-start sm:self-auto transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Filtreleri Sıfırla</span>
            </button>
          )}
        </div>
      </Card>

      {/* Leads Table Card */}
      <Card className="overflow-hidden shadow-sm">
        <div className="overflow-x-auto min-w-full">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200/80 dark:border-white/[0.08] bg-slate-50/75 dark:bg-white/[0.02] text-slate-500 dark:text-[#7E7F96] font-bold uppercase tracking-wider text-[11px]">
                <th className="py-3.5 px-4">İşletme Profili</th>
                <th className="py-3.5 px-4">İletişim & WhatsApp</th>
                <th className="py-3.5 px-4">Lokasyon</th>
                <th className="py-3.5 px-4">Puan & Web</th>
                <th className="py-3.5 px-4">Durum</th>
                <th className="py-3.5 px-4 text-right">İşlemler</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-white/[0.04]">
              {loading ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-400">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto text-[#7367F0] mb-2" />
                    <span>Müşteri adayları yükleniyor...</span>
                  </td>
                </tr>
              ) : leads.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-400">
                    <Users className="w-8 h-8 mx-auto text-slate-300 dark:text-slate-600 mb-2" />
                    <p className="font-bold text-slate-700 dark:text-slate-200">Kayıt Bulunamadı</p>
                    <p className="text-[11px] mt-0.5">Arama kriterlerinizi değiştirin veya "İşletme Ara" bölümünden yeni arama başlatın.</p>
                  </td>
                </tr>
              ) : (
                leads.map((lead) => (
                  <tr 
                    key={lead.id} 
                    className="hover:bg-slate-50/70 dark:hover:bg-white/[0.02] transition-colors group"
                  >
                    {/* Name & Category */}
                    <td className="py-3.5 px-4 max-w-[240px]">
                      <div className="font-bold text-slate-800 dark:text-white text-xs truncate">
                        {lead.name}
                      </div>
                      <div className="flex items-center gap-1.5 mt-1 flex-wrap">
                        <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-[#7367F0]/10 text-[#7367F0] dark:bg-[#7367F0]/20 dark:text-[#A59DF8]">
                          {lead.category || 'Genel'}
                        </span>
                        {lead.entity_type && (
                          <span className="text-[9px] font-mono uppercase px-1 py-0.2 rounded bg-slate-100 dark:bg-white/[0.06] text-slate-500">
                            {lead.entity_type}
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Phone & WhatsApp */}
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <div className="flex items-center space-x-2 font-mono font-bold text-xs text-slate-700 dark:text-slate-200">
                        <Phone className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                        <span>{lead.phone_e164 || lead.phone || 'Belirtilmemiş'}</span>
                      </div>
                      <div className="mt-1">
                        {lead.is_whatsapp_eligible ? (
                          <span className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded-full bg-[#25D366]/15 text-[#25D366] font-bold text-[10px]">
                            <WhatsAppIcon className="w-3 h-3" />
                            <span>WhatsApp Aktif</span>
                          </span>
                        ) : (
                          <span className="text-[10px] text-slate-400 font-sans">
                            WhatsApp Doğrulanmadı
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Location */}
                    <td className="py-3.5 px-4 max-w-[240px]">
                      <div className="flex items-start space-x-1.5 text-xs text-slate-600 dark:text-slate-300">
                        <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
                        <span className="line-clamp-2 leading-tight">
                          {lead.address || `${lead.district ? `${lead.district}, ` : ''}${lead.city || ''}`}
                        </span>
                      </div>
                    </td>

                    {/* Rating & Website */}
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      {lead.rating ? (
                        <div className="flex items-center space-x-1 text-xs">
                          <Star className="w-3.5 h-3.5 text-[#FF9F43] fill-[#FF9F43]" />
                          <span className="font-bold text-slate-800 dark:text-white">{lead.rating}</span>
                          {lead.reviews_count ? (
                            <span className="text-slate-400 text-[10px]">({lead.reviews_count})</span>
                          ) : null}
                        </div>
                      ) : (
                        <span className="text-slate-400 text-[10px]">Puan Yok</span>
                      )}

                      {lead.website ? (
                        <a
                          href={lead.website.startsWith('http') ? lead.website : `https://${lead.website}`}
                          target="_blank"
                          rel="noreferrer"
                          className="mt-1 inline-flex items-center space-x-1 text-[11px] text-[#7367F0] hover:underline truncate max-w-[140px]"
                        >
                          <Globe className="w-3 h-3 shrink-0" />
                          <span className="truncate">{lead.website.replace(/^https?:\/\/(www\.)?/, '')}</span>
                        </a>
                      ) : null}
                    </td>

                    {/* Status Dropdown */}
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <select
                        value={lead.status}
                        onChange={(e) => handleStatusChange(lead.id, e.target.value as LeadStatus)}
                        className={`px-2.5 py-1 rounded-lg text-xs font-bold border transition-colors cursor-pointer ${
                          lead.status === 'NEW'
                            ? 'bg-blue-50 text-blue-600 border-blue-200 dark:bg-blue-500/10 dark:text-blue-400 dark:border-blue-500/20'
                            : lead.status === 'CONTACTED'
                            ? 'bg-amber-50 text-amber-600 border-amber-200 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-500/20'
                            : lead.status === 'REPLIED'
                            ? 'bg-emerald-50 text-emerald-600 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/20'
                            : lead.status === 'INTERESTED'
                            ? 'bg-purple-50 text-purple-600 border-purple-200 dark:bg-purple-500/10 dark:text-purple-400 dark:border-purple-500/20'
                            : 'bg-rose-50 text-rose-600 border-rose-200 dark:bg-rose-500/10 dark:text-rose-400 dark:border-rose-500/20'
                        }`}
                      >
                        <option value="NEW">NEW</option>
                        <option value="CONTACTED">CONTACTED</option>
                        <option value="REPLIED">REPLIED</option>
                        <option value="INTERESTED">INTERESTED</option>
                        <option value="UNSUBSCRIBED">UNSUBSCRIBED</option>
                      </select>
                    </td>

                    {/* Actions */}
                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end space-x-1.5">
                        <button
                          type="button"
                          onClick={() => handleOpenSendModal(lead)}
                          title="Hızlı WhatsApp Mesajı Gönder"
                          className="p-1.5 rounded-lg text-[#25D366] hover:bg-[#25D366]/15 transition-colors"
                        >
                          <Send className="w-4 h-4" />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleBlacklistNumber(lead.phone_e164 || lead.phone, 'Kullanıcı manuel engelledi')}
                          title="Numarayı Kara Listeye Ekle"
                          className="p-1.5 rounded-lg text-slate-400 hover:text-[#EA5455] hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-colors"
                        >
                          <ShieldAlert className="w-4 h-4" />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDeleteLead(lead.id)}
                          title="Lead'i Sil"
                          className="p-1.5 rounded-lg text-slate-400 hover:text-[#EA5455] hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {total > pageSize && (
          <div className="p-4 border-t border-slate-100 dark:border-white/[0.06] flex items-center justify-between text-xs text-slate-500 dark:text-[#7E7F96]">
            <span>
              Toplam <strong>{total}</strong> kayıttan <strong>{(page - 1) * pageSize + 1} - {Math.min(page * pageSize, total)}</strong> arası gösteriliyor
            </span>
            <div className="flex items-center space-x-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
              >
                Önceki
              </Button>
              <span className="font-bold text-slate-700 dark:text-slate-200">
                Sayfa {page} / {Math.ceil(total / pageSize)}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page * pageSize >= total}
                onClick={() => setPage(page + 1)}
              >
                Sonraki
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Add New Lead Modal */}
      {isAddModalOpen && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in select-none"
          onClick={() => setIsAddModalOpen(false)}
        >
          <div 
            className="w-full max-w-md bg-white dark:bg-[#2F3349] rounded-2xl shadow-2xl border border-slate-200 dark:border-white/[0.08] p-6 animate-scale-up"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100 dark:border-white/[0.06]">
              <h3 className="text-base font-extrabold text-slate-800 dark:text-white flex items-center gap-2">
                <Plus className="w-5 h-5 text-[#7367F0]" />
                Yeni Müşteri Adayı Ekle
              </h3>
              <button 
                onClick={() => setIsAddModalOpen(false)}
                className="text-slate-400 hover:text-slate-700 dark:hover:text-white p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {formError && (
              <div className="mb-4 p-3 rounded-lg bg-rose-50 text-[#EA5455] text-xs font-bold border border-rose-200">
                {formError}
              </div>
            )}

            <form onSubmit={handleAddLead} className="space-y-3.5 text-xs">
              <div>
                <label className="text-slate-700 dark:text-slate-300 font-bold block mb-1">İşletme Adı *</label>
                <input
                  type="text"
                  value={newLeadName}
                  onChange={(e) => setNewLeadName(e.target.value)}
                  placeholder="Örn: Dentgroup Ataşehir"
                  className="w-full px-3 py-2 rounded-lg vuexy-input"
                  required
                />
              </div>

              <div>
                <label className="text-slate-700 dark:text-slate-300 font-bold block mb-1">Telefon Numarası *</label>
                <input
                  type="text"
                  value={newLeadPhone}
                  onChange={(e) => setNewLeadPhone(e.target.value)}
                  placeholder="Örn: 0532 123 45 67 veya 0216 414 99 88"
                  className="w-full px-3 py-2 rounded-lg vuexy-input font-mono"
                  required
                />
              </div>

              <div>
                <label className="text-slate-700 dark:text-slate-300 font-bold block mb-1">Kategori / Sektör</label>
                <input
                  type="text"
                  value={newLeadCategory}
                  onChange={(e) => setNewLeadCategory(e.target.value)}
                  placeholder="Örn: Diş Kliniği"
                  className="w-full px-3 py-2 rounded-lg vuexy-input"
                />
              </div>

              <div className="grid grid-cols-2 gap-2.5">
                <div>
                  <label className="text-slate-700 dark:text-slate-300 font-bold block mb-1">Şehir</label>
                  <input
                    type="text"
                    value={newLeadCity}
                    onChange={(e) => setNewLeadCity(e.target.value)}
                    placeholder="İstanbul"
                    className="w-full px-3 py-2 rounded-lg vuexy-input"
                  />
                </div>
                <div>
                  <label className="text-slate-700 dark:text-slate-300 font-bold block mb-1">İlçe</label>
                  <input
                    type="text"
                    value={newLeadDistrict}
                    onChange={(e) => setNewLeadDistrict(e.target.value)}
                    placeholder="Ataşehir"
                    className="w-full px-3 py-2 rounded-lg vuexy-input"
                  />
                </div>
              </div>

              <div className="pt-3 flex items-center justify-end space-x-2">
                <Button 
                  type="button" 
                  variant="outline" 
                  size="sm" 
                  onClick={() => setIsAddModalOpen(false)}
                >
                  Vazgeç
                </Button>
                <Button 
                  type="submit" 
                  size="sm" 
                  className="font-bold shadow-md shadow-[#7367F0]/30"
                >
                  Kaydet
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Quick Send Message Modal */}
      {isSendModalOpen && selectedLeadForSend && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in select-none"
          onClick={() => setIsSendModalOpen(false)}
        >
          <div 
            className="w-full max-w-md bg-white dark:bg-[#2F3349] rounded-2xl shadow-2xl border border-slate-200 dark:border-white/[0.08] p-6 animate-scale-up"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100 dark:border-white/[0.06]">
              <h3 className="text-base font-extrabold text-slate-800 dark:text-white flex items-center gap-2">
                <Send className="w-4 h-4 text-[#25D366]" />
                Tekil WhatsApp Mesajı Gönder
              </h3>
              <button 
                onClick={() => setIsSendModalOpen(false)}
                className="text-slate-400 hover:text-slate-700 dark:hover:text-white p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="mb-3.5 p-3 rounded-lg bg-slate-50 dark:bg-[#25293C] border border-slate-200/60 dark:border-white/[0.05] text-xs">
              <p className="font-bold text-slate-800 dark:text-white">{selectedLeadForSend.name}</p>
              <p className="font-mono text-[#7367F0] mt-0.5">{selectedLeadForSend.phone_e164 || selectedLeadForSend.phone}</p>
            </div>

            {sendSuccessMsg && (
              <div className="mb-3 p-2.5 rounded-lg bg-emerald-50 text-[#28C76F] text-xs font-bold border border-emerald-200 animate-fade-in">
                {sendSuccessMsg}
              </div>
            )}

            <div className="space-y-3.5 text-xs">
              <div>
                <label className="text-slate-700 dark:text-slate-300 font-bold block mb-1">Mesaj Metni</label>
                <textarea
                  value={customMessage}
                  onChange={(e) => setCustomMessage(e.target.value)}
                  rows={5}
                  className="w-full p-3 rounded-lg vuexy-input leading-relaxed"
                  placeholder="Mesajınızı buraya yazın..."
                />
              </div>

              <div className="flex items-center justify-end space-x-2 pt-2">
                <Button 
                  type="button" 
                  variant="outline" 
                  size="sm" 
                  onClick={() => setIsSendModalOpen(false)}
                >
                  Kapat
                </Button>
                <Button 
                  type="button" 
                  size="sm" 
                  disabled={isSending || !customMessage}
                  onClick={handleSendSingleMessage}
                  className="bg-[#25D366] hover:bg-[#1EBE5D] text-white font-bold space-x-1.5"
                >
                  {isSending ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>İletiliyor...</span>
                    </>
                  ) : (
                    <>
                      <Send className="w-3.5 h-3.5" />
                      <span>Mesajı Gönder</span>
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
