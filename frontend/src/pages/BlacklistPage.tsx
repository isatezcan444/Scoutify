import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { 
  ShieldAlert, 
  Plus, 
  Trash2, 
  Loader2, 
  X, 
  Phone, 
  Search, 
  Building2, 
  MapPin, 
  CheckCircle2, 
  Save
} from 'lucide-react';
import { ApiClient } from '../api/client';
import { BlacklistEntry, Lead } from '../types';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Card } from '../components/ui/card';
import { useToast } from '../context/ToastContext';

export const BlacklistPage: React.FC = () => {
  const toast = useToast();
  const [blacklist, setBlacklist] = useState<BlacklistEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Form & Lead Search State
  const [newReason, setNewReason] = useState('USER_REQUEST');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Lead[]>([]);
  const [isSearchingLeads, setIsSearchingLeads] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const searchContainerRef = useRef<HTMLDivElement>(null);

  const fetchBlacklist = async () => {
    setLoading(true);
    try {
      const data = await ApiClient.getBlacklist();
      setBlacklist(data);
    } catch (err: any) {
      toast.error(err.message || 'Kara liste yüklenirken hata oluştu', 'Kara Liste Yüklenemedi');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBlacklist();
  }, []);

  // Debounced Lead Search
  useEffect(() => {
    if (!searchQuery.trim() || selectedLead) {
      setSearchResults([]);
      return;
    }

    const timer = setTimeout(async () => {
      setIsSearchingLeads(true);
      try {
        const res = await ApiClient.getLeads({
          search: searchQuery.trim(),
          size: 8
        });
        setSearchResults(res.items || []);
        setShowSuggestions(true);
      } catch (err) {
        console.error('Lead search error in blacklist:', err);
      } finally {
        setIsSearchingLeads(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [searchQuery, selectedLead]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelectLead = (lead: Lead) => {
    setSelectedLead(lead);
    setSearchQuery(lead.name);
    setShowSuggestions(false);
  };

  const handleClearSelectedLead = () => {
    setSelectedLead(null);
    setSearchQuery('');
    setSearchResults([]);
    setShowSuggestions(false);
  };

  const handleOpenAddModal = () => {
    setSelectedLead(null);
    setSearchQuery('');
    setNewReason('USER_REQUEST');
    setSearchResults([]);
    setShowSuggestions(false);
    setIsAddOpen(true);
  };

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedLead) {
      toast.error('Lütfen kara listeye eklemek için bir müşteri adayı arayıp seçin.', 'Müşteri Adayı Seçilmedi');
      return;
    }

    const phoneToSubmit = (selectedLead.phone_e164 || selectedLead.phone || '').trim();
    if (!phoneToSubmit) {
      toast.error('Seçilen işletmenin kayıtlı bir telefon numarası bulunmuyor.', 'Telefon Numarası Eksik');
      return;
    }

    setSubmitting(true);
    try {
      await ApiClient.addToBlacklist(phoneToSubmit, newReason);
      toast.success(
        `${selectedLead.name} (${phoneToSubmit}) başarıyla kara listeye eklendi.`,
        'Numara Engellendi'
      );
      setIsAddOpen(false);
      handleClearSelectedLead();
      fetchBlacklist();
    } catch (err: any) {
      toast.error(err.message || 'Numara kara listeye eklenemedi', 'Kara Listeye Eklenemedi');
    } finally {
      setSubmitting(false);
    }
  };

  const handleRemove = async (id: number, phone: string) => {
    const ok = await toast.confirm({
      title: 'Numarayı Kara Listeden Kaldır',
      message: `${phone} numarasının engeli kaldırılacak ve gelecekteki kampanyalara dahil edilebilecektir. Devam etmek istiyor musunuz?`,
      confirmText: 'Evet, Engeli Kaldır',
      cancelText: 'Vazgeç',
      variant: 'warning',
    });
    if (!ok) return;

    try {
      await ApiClient.removeFromBlacklist(id);
      toast.success('Numara kara listeden çıkarıldı.', 'Engel Kaldırıldı');
      fetchBlacklist();
    } catch (err: any) {
      toast.error(err.message || 'Engel kaldırılamadı', 'Hata');
    }
  };

  const getReasonLabel = (reason: string) => {
    switch (reason) {
      case 'USER_REQUEST':
        return 'Müşteri Talebi';
      case 'BOUNCED':
        return 'Ulaşılamayan Numara';
      case 'SPAM_COMPLAINT':
        return 'Şikayet Riski Önleme';
      case 'MANUAL_BLACKLIST':
        return 'Manuel Yönetici Engeli';
      default:
        return reason;
    }
  };

  return (
    <div className="space-y-6 pb-16 select-none animate-fade-in">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-extrabold text-slate-800 dark:text-white flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-[#EA5455]" />
            Kara Liste ({blacklist.length} Numara)
          </h2>
          <p className="text-xs text-slate-500 dark:text-[#7E7F96] mt-0.5 font-medium">
            İletişim kurulması engellenen işletmeler ve mesajlaşma dışı tutulan numaralar
          </p>
        </div>

        <Button
          variant="destructive"
          size="sm"
          onClick={handleOpenAddModal}
          className="space-x-1.5 font-bold cursor-pointer shadow-md shadow-[#EA5455]/20"
        >
          <Plus className="w-4 h-4" />
          <span>Numara Ekle</span>
        </Button>
      </div>

      {/* Blacklist Table */}
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/80 dark:bg-white/[0.02] text-slate-600 dark:text-slate-300 font-bold border-b border-slate-200/80 dark:border-white/[0.08]">
              <tr>
                <th className="py-3.5 px-4">Telefon Numarası</th>
                <th className="py-3.5 px-4">Engelleme Nedeni</th>
                <th className="py-3.5 px-4">Eklenme Tarihi</th>
                <th className="py-3.5 px-4 text-right">İşlemler</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-white/[0.05] text-slate-700 dark:text-slate-300 font-medium">
              {loading ? (
                <tr>
                  <td colSpan={4} className="py-12 text-center text-slate-400">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto text-[#EA5455]" />
                    <span className="text-xs font-bold block mt-2">Kara liste yükleniyor...</span>
                  </td>
                </tr>
              ) : blacklist.length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-12 text-center text-slate-400 font-semibold">
                    <ShieldAlert className="w-8 h-8 mx-auto text-slate-300 dark:text-slate-600 mb-2" />
                    Kara listede kayıtlı numara bulunmuyor.
                  </td>
                </tr>
              ) : (
                blacklist.map((entry) => (
                  <tr key={entry.id} className="hover:bg-slate-50/60 dark:hover:bg-white/[0.02] transition-colors">
                    <td className="py-3.5 px-4 font-mono font-bold text-[#EA5455]">
                      <div className="flex items-center gap-2">
                        <Phone className="w-3.5 h-3.5" />
                        <span>{entry.phone_e164}</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <Badge variant="danger" className="text-[11px] font-bold">
                        {getReasonLabel(entry.reason)}
                      </Badge>
                    </td>
                    <td className="py-3.5 px-4 text-slate-500 dark:text-[#7E7F96] font-sans">
                      {new Date(entry.created_at).toLocaleString('tr-TR')}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => handleRemove(entry.id, entry.phone_e164)}
                        className="text-slate-400 hover:text-[#EA5455] p-1.5 rounded-lg hover:bg-[#EA5455]/10 transition-colors cursor-pointer"
                        title="Kara Listeden Çıkar"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Numara Ekle Modal with Mandatory Lead Search */}
      {isAddOpen && typeof document !== 'undefined' && createPortal(
        <div 
          className="fixed inset-0 z-[99999] bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 animate-fade-in select-none"
          onClick={() => setIsAddOpen(false)}
        >
          <form 
            onSubmit={handleAdd} 
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-md rounded-2xl bg-white dark:bg-[#2F3349] p-6 space-y-5 shadow-2xl border border-slate-200/80 dark:border-white/[0.1] animate-scale-in"
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-1 border-b border-slate-100 dark:border-white/[0.08]">
              <div className="flex items-center space-x-2.5">
                <div className="w-8 h-8 rounded-xl bg-[#EA5455]/15 text-[#EA5455] flex items-center justify-center font-bold">
                  <ShieldAlert className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-base font-extrabold text-slate-800 dark:text-white">
                    Kara Listeye Numara Ekle
                  </h3>
                  <p className="text-[11px] text-slate-400 dark:text-[#7E7F96]">
                    Kara listeye almak istediğiniz müşteri adayını seçin
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIsAddOpen(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/[0.06] transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="space-y-4 text-xs">
              {/* Mandatory Lead Search Field */}
              <div ref={searchContainerRef} className="relative">
                <label className="text-slate-700 dark:text-slate-300 font-bold block mb-1 flex items-center justify-between">
                  <span>Müşteri Adayı Ara *</span>
                  {selectedLead && (
                    <button
                      type="button"
                      onClick={handleClearSelectedLead}
                      className="text-[10px] text-[#7367F0] hover:underline font-bold cursor-pointer"
                    >
                      Değiştir
                    </button>
                  )}
                </label>

                {!selectedLead ? (
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                      {isSearchingLeads ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin text-[#7367F0]" />
                      ) : (
                        <Search className="w-3.5 h-3.5" />
                      )}
                    </div>
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      onFocus={() => {
                        if (searchResults.length > 0) setShowSuggestions(true);
                      }}
                      placeholder="İşletme adı veya anahtar kelime..."
                      className="w-full pl-9 pr-3 py-2 rounded-lg vuexy-input text-xs font-medium"
                      autoFocus
                    />
                  </div>
                ) : (
                  /* Selected Lead Summary Card */
                  <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-[#25293C] border border-[#7367F0]/30 flex items-center justify-between animate-fade-in shadow-sm">
                    <div className="space-y-1">
                      <div className="font-extrabold text-slate-800 dark:text-white flex items-center gap-1.5 text-xs">
                        <Building2 className="w-3.5 h-3.5 text-[#7367F0]" />
                        <span>{selectedLead.name}</span>
                      </div>
                      <div className="flex items-center gap-2 text-[11px] text-[#EA5455] font-mono font-bold">
                        <Phone className="w-3 h-3" />
                        <span>{selectedLead.phone_e164 || selectedLead.phone || 'Numara Yok'}</span>
                      </div>
                      <div className="flex items-center gap-2 text-[10px] text-slate-400">
                        {selectedLead.category && <span>{selectedLead.category}</span>}
                        {(selectedLead.district || selectedLead.city) && (
                          <span>• {[selectedLead.district, selectedLead.city].filter(Boolean).join(', ')}</span>
                        )}
                      </div>
                    </div>

                    <div className="flex flex-col items-end gap-1.5">
                      <Badge variant="success" className="text-[9px] font-bold">
                        Seçildi
                      </Badge>
                      <button
                        type="button"
                        onClick={handleClearSelectedLead}
                        className="text-[10px] text-[#7367F0] hover:underline font-bold cursor-pointer"
                      >
                        Değiştir
                      </button>
                    </div>
                  </div>
                )}

                {/* Suggestions Dropdown */}
                {showSuggestions && searchResults.length > 0 && !selectedLead && (
                  <div className="absolute left-0 right-0 top-full mt-1.5 bg-white dark:bg-[#25293C] rounded-xl shadow-xl border border-slate-200 dark:border-white/[0.1] max-h-56 overflow-y-auto z-50 divide-y divide-slate-100 dark:divide-white/[0.05] animate-scale-in">
                    {searchResults.map((lead) => (
                      <button
                        key={lead.id}
                        type="button"
                        onClick={() => handleSelectLead(lead)}
                        className="w-full p-2.5 text-left hover:bg-slate-50 dark:hover:bg-white/[0.04] transition-colors flex items-center justify-between group cursor-pointer"
                      >
                        <div className="space-y-0.5">
                          <div className="font-bold text-slate-800 dark:text-white flex items-center gap-1.5">
                            <Building2 className="w-3.5 h-3.5 text-[#7367F0]" />
                            <span>{lead.name}</span>
                          </div>
                          <div className="flex items-center gap-2 text-[10px] text-slate-400">
                            {lead.category && <span>{lead.category}</span>}
                            {(lead.district || lead.city) && (
                              <span className="flex items-center gap-0.5">
                                <MapPin className="w-2.5 h-2.5" />
                                {[lead.district, lead.city].filter(Boolean).join(', ')}
                              </span>
                            )}
                          </div>
                        </div>

                        <div className="text-right">
                          <span className="text-xs font-mono font-bold text-slate-700 dark:text-slate-300 block">
                            {lead.phone_e164 || lead.phone || 'Tel yok'}
                          </span>
                          <span className="text-[9px] text-[#7367F0] group-hover:underline font-bold">
                            Seç ↵
                          </span>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Reason Selection */}
              <div>
                <label className="text-slate-700 dark:text-slate-300 font-bold block mb-1">
                  Engelleme Nedeni
                </label>
                <select
                  value={newReason}
                  onChange={(e) => setNewReason(e.target.value)}
                  className="w-full p-2.5 rounded-lg vuexy-input text-xs font-bold"
                >
                  <option value="USER_REQUEST">Müşteri Talebi</option>
                  <option value="BOUNCED">Ulaşılamayan / Geçersiz Numara</option>
                  <option value="SPAM_COMPLAINT">Şikayet Riski Önleme</option>
                  <option value="MANUAL_BLACKLIST">Manuel Yönetici Engeli</option>
                </select>
              </div>
            </div>

            {/* Modal Actions */}
            <div className="pt-2 flex items-center space-x-2 border-t border-slate-100 dark:border-white/[0.08]">
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsAddOpen(false)}
                className="w-1/2 font-bold cursor-pointer"
                disabled={submitting}
              >
                İptal
              </Button>
              <Button
                type="submit"
                variant="destructive"
                disabled={submitting || !selectedLead}
                className="w-1/2 font-bold shadow-md shadow-[#EA5455]/30 cursor-pointer space-x-1.5"
              >
                {submitting ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Kaydediliyor...</span>
                  </>
                ) : (
                  <>
                    <Save className="w-3.5 h-3.5" />
                    <span>Kaydet</span>
                  </>
                )}
              </Button>
            </div>
          </form>
        </div>,
        document.body
      )}
    </div>
  );
};
