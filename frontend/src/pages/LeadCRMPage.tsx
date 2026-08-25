import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
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
  RotateCcw,
  Check,
  AlertTriangle,
  CheckSquare,
  Square,
  MinusSquare,
  Shield,
  Navigation
} from 'lucide-react';
import { WhatsAppIcon } from '../components/ui/whatsapp-icon';
import { GoogleMapsIcon } from '../components/ui/google-maps-icon';
import { LocationMultiSelect } from '../components/LeadFinder/LocationMultiSelect';
import { CategoryMultiSelect } from '../components/LeadFinder/CategoryMultiSelect';
import { ApiClient } from '../api/client';
import { Lead, LeadStatus } from '../types';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Card } from '../components/ui/card';

import { useToast } from '../context/ToastContext';
import { useI18n } from '../context/I18nContext';

interface LeadCRMPageProps {
  onRefreshStats: () => void;
}

export const LeadCRMPage: React.FC<LeadCRMPageProps> = ({ onRefreshStats }) => {
  const toast = useToast();
  const { t } = useI18n();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  
  // Search & Filter State
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [selectedCity, setSelectedCity] = useState('');
  const [selectedDistricts, setSelectedDistricts] = useState<string[]>([]);
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [waOnly, setWaOnly] = useState(false);
  const [loading, setLoading] = useState(false);

  // Debounce search input (300ms)
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(search);
    }, 300);
    return () => clearTimeout(handler);
  }, [search]);

  // Selection state (Gmail style)
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [selectAllMatching, setSelectAllMatching] = useState(false);

  // Delete Modal State
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [leadToDelete, setLeadToDelete] = useState<Lead | null>(null);
  const [isBulkDelete, setIsBulkDelete] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Blacklist Modal State
  const [isBlacklistModalOpen, setIsBlacklistModalOpen] = useState(false);
  const [leadToBlacklist, setLeadToBlacklist] = useState<Lead | null>(null);
  const [isBulkBlacklist, setIsBulkBlacklist] = useState(false);
  const [blacklistReason, setBlacklistReason] = useState('Kullanıcı talebi / İletişim reddi');
  const [isBlacklisting, setIsBlacklisting] = useState(false);

  // Add & Quick Send Modal State
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
        search: debouncedSearch || undefined,
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
  }, [page, debouncedSearch, selectedCity, selectedDistricts, selectedCategories, statusFilter, waOnly]);

  // Clear selection on page/filter change unless all-matching is active
  useEffect(() => {
    if (!selectAllMatching) {
      setSelectedIds([]);
    }
  }, [page, debouncedSearch, selectedCity, selectedDistricts, selectedCategories, statusFilter, waOnly]);

  // --- Gmail-style Checkbox logic ---
  const currentPageIds = leads.map((l) => l.id);
  const isAllCurrentPageSelected =
    leads.length > 0 && currentPageIds.every((id) => selectedIds.includes(id));
  const isSomeCurrentPageSelected =
    currentPageIds.some((id) => selectedIds.includes(id)) && !isAllCurrentPageSelected;

  const handleToggleSelectAllPage = () => {
    if (selectAllMatching) {
      setSelectAllMatching(false);
      setSelectedIds([]);
      return;
    }

    if (isAllCurrentPageSelected) {
      // Unselect current page
      setSelectedIds((prev) => prev.filter((id) => !currentPageIds.includes(id)));
    } else {
      // Select all on current page
      setSelectedIds((prev) => Array.from(new Set([...prev, ...currentPageIds])));
    }
  };

  const handleToggleSingleSelect = (id: number) => {
    if (selectAllMatching) {
      setSelectAllMatching(false);
      setSelectedIds(currentPageIds.filter((x) => x !== id));
      return;
    }

    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const handleSelectAllAcrossPages = () => {
    setSelectAllMatching(true);
    setSelectedIds(currentPageIds);
  };

  const handleClearSelection = () => {
    setSelectedIds([]);
    setSelectAllMatching(false);
  };

  // --- Delete Modal Handlers ---
  const handleOpenSingleDelete = (lead: Lead) => {
    setLeadToDelete(lead);
    setIsBulkDelete(false);
    setIsDeleteModalOpen(true);
  };

  const handleOpenBulkDelete = () => {
    setLeadToDelete(null);
    setIsBulkDelete(true);
    setIsDeleteModalOpen(true);
  };

  const handleConfirmDelete = async () => {
    setIsDeleting(true);
    try {
      if (isBulkDelete) {
        if (selectAllMatching) {
          await ApiClient.bulkDeleteLeads({
            delete_all_matching: true,
            search: search || undefined,
            city: selectedCity || undefined,
            districts: selectedDistricts.length > 0 ? selectedDistricts : undefined,
            categories: selectedCategories.length > 0 ? selectedCategories : undefined,
            status: statusFilter || undefined,
            whatsapp_eligible_only: waOnly,
          });
        } else {
          await ApiClient.bulkDeleteLeads({ lead_ids: selectedIds });
        }
        handleClearSelection();
        toast.success(`Seçilen ${selectedCount} müşteri adayı başarıyla silindi.`, 'Toplu Silme');
      } else if (leadToDelete) {
        await ApiClient.deleteLead(leadToDelete.id);
        toast.success(`${leadToDelete.name} başarıyla silindi.`, 'Lead Silindi');
      }

      setIsDeleteModalOpen(false);
      setLeadToDelete(null);
      fetchLeads();
      onRefreshStats();
    } catch (err: any) {
      toast.error(err.message, 'Silme Hatası');
    } finally {
      setIsDeleting(false);
    }
  };

  // --- Blacklist Modal Handlers ---
  const handleOpenSingleBlacklist = (lead: Lead) => {
    setLeadToBlacklist(lead);
    setIsBulkBlacklist(false);
    setBlacklistReason('Kullanıcı talebi / İletişim reddi');
    setIsBlacklistModalOpen(true);
  };

  const handleOpenBulkBlacklist = () => {
    setLeadToBlacklist(null);
    setIsBulkBlacklist(true);
    setBlacklistReason('Toplu kara listeye eklendi');
    setIsBlacklistModalOpen(true);
  };

  const handleConfirmBlacklist = async () => {
    setIsBlacklisting(true);
    try {
      if (isBulkBlacklist) {
        if (selectAllMatching) {
          const res = await ApiClient.bulkBlacklistLeads({
            blacklist_all_matching: true,
            reason: blacklistReason,
            search: debouncedSearch || undefined,
            city: selectedCity || undefined,
            districts: selectedDistricts.length > 0 ? selectedDistricts : undefined,
            categories: selectedCategories.length > 0 ? selectedCategories : undefined,
            status: statusFilter || undefined,
            whatsapp_eligible_only: waOnly,
          });
          handleClearSelection();
          toast.success(`${res.blacklisted_count} işletme numarası kara listeye eklendi (${res.leads_updated} kayıt güncellendi).`, 'Toplu Kara Liste');
        } else {
          await ApiClient.bulkBlacklistLeads({
            lead_ids: selectedIds,
            reason: blacklistReason,
          });
          handleClearSelection();
          toast.success(`${selectedIds.length} işletme numarası kara listeye eklendi.`, 'Toplu Kara Liste');
        }
      } else if (leadToBlacklist) {
        await ApiClient.addBlacklist({
          phone: leadToBlacklist.phone_e164 || leadToBlacklist.phone,
          reason: blacklistReason,
        });
        toast.success(`${leadToBlacklist.name} kara listeye alındı.`, 'Kara Listeye Eklendi');
      }

      setIsBlacklistModalOpen(false);
      setLeadToBlacklist(null);
      fetchLeads();
      onRefreshStats();
    } catch (err: any) {
      toast.error(err.message, 'Kara Liste Hatası');
    } finally {
      setIsBlacklisting(false);
    }
  };

  // --- Status & Add Lead Handlers ---
  const handleStatusChange = async (leadId: number, newStatus: LeadStatus) => {
    try {
      await ApiClient.updateLead(leadId, { status: newStatus });
      setLeads(leads.map((l) => (l.id === leadId ? { ...l, status: newStatus } : l)));
      toast.success(`Durum "${newStatus}" olarak güncellendi.`, 'Durum Güncellendi');
      onRefreshStats();
    } catch (err: any) {
      toast.error(err.message || 'Durum güncellenemedi', 'Hata');
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

      toast.success(`${newLeadName} başarıyla rehbere eklendi.`, 'Yeni Müşteri Adayı');
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

      toast.success(`${selectedLeadForSend.name} alıcısına mesaj başarıyla iletildi.`, 'Mesaj Gönderildi');
      setSendSuccessMsg('✅ Mesaj kuyruğa alındı ve iletildi!');
      setTimeout(() => {
        setIsSendModalOpen(false);
        fetchLeads();
        onRefreshStats();
      }, 1200);
    } catch (err: any) {
      toast.error(err.message, 'Mesaj Gönderilemedi');
    } finally {
      setIsSending(false);
    }
  };

  const getGoogleMapsUrl = (lead: Lead) => {
    if ((lead as any).maps_url) return (lead as any).maps_url;
    if ((lead as any).google_maps_url) return (lead as any).google_maps_url;
    if (lead.custom_data?.google_maps_url) return lead.custom_data.google_maps_url;
    if (lead.custom_data?.maps_url) return lead.custom_data.maps_url;
    const query = [lead.name, lead.address || [lead.district, lead.city].filter(Boolean).join(', ')].filter(Boolean).join(' ');
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
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

  const selectedCount = selectAllMatching ? total : selectedIds.length;

  return (
    <div className="space-y-4 sm:space-y-6 pb-16 select-none animate-fade-in">
      {/* Top Action Bar & Filter Header */}
      <Card className="p-4 sm:p-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <h2 className="text-lg sm:text-xl font-extrabold text-slate-800 dark:text-white flex items-center gap-2">
              <Users className="w-5 h-5 text-[#7367F0]" />
              {t('leads.title')} ({total})
            </h2>
            <p className="text-xs text-slate-500 dark:text-[#7E7F96] mt-0.5 font-medium">
              {t('titles.leadsSub')}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 sm:gap-2.5">
            <Button
              onClick={() => setIsAddModalOpen(true)}
              size="sm"
              className="space-x-1.5 font-bold shadow-md shadow-[#7367F0]/30 w-full sm:w-auto justify-center cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>{t('leads.addLead')}</span>
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
              className="space-x-1.5 flex-1 sm:flex-initial justify-center cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span>{t('leads.exportCsv')}</span>
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
              className="space-x-1.5 flex-1 sm:flex-initial justify-center cursor-pointer"
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
              placeholder={t('leads.searchPlaceholder')}
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
              className="w-full px-3 rounded-lg vuexy-input text-xs font-semibold h-10 cursor-pointer"
            >
              <option value="">{t('leads.filterByStatus')}</option>
              <option value="NEW">NEW</option>
              <option value="CONTACTED">CONTACTED</option>
              <option value="REPLIED">REPLIED</option>
              <option value="INTERESTED">INTERESTED</option>
              <option value="UNSUBSCRIBED">UNSUBSCRIBED</option>
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
              <span>{t('leads.whatsappOnly')}</span>
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
                  className="hover:text-[#EA5455] ml-0.5 cursor-pointer"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}

            {selectedDistricts.length > 0 && (
              <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-1 rounded-lg bg-slate-100 dark:bg-white/[0.06] text-slate-700 dark:text-slate-200">
                <span>{selectedDistricts.length} {t('common.location')}: {selectedDistricts.slice(0, 2).join(', ')}{selectedDistricts.length > 2 ? '...' : ''}</span>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedDistricts([]);
                    setPage(1);
                  }}
                  className="hover:text-[#EA5455] ml-0.5 cursor-pointer"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}

            {selectedCategories.length > 0 && (
              <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-1 rounded-lg bg-[#00CFE8]/15 text-[#00CFE8] dark:bg-[#00CFE8]/25 dark:text-[#00CFE8]">
                <span>{selectedCategories.length} {t('common.category')}: {selectedCategories.slice(0, 2).join(', ')}{selectedCategories.length > 2 ? '...' : ''}</span>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedCategories([]);
                    setPage(1);
                  }}
                  className="hover:text-[#EA5455] ml-0.5 cursor-pointer"
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
              className="text-xs font-bold text-slate-400 hover:text-[#EA5455] flex items-center gap-1.5 self-start sm:self-auto transition-colors cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>{t('leads.resetFilters')}</span>
            </button>
          )}
        </div>
      </Card>

      {/* Floating / Sticky Bulk Action Toolbar */}
      {selectedCount > 0 && (
        <div className="p-3.5 rounded-xl bg-gradient-to-r from-[#7367F0] to-[#867BFF] text-white shadow-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3 animate-fade-in">
          <div className="flex items-center space-x-2.5 flex-wrap">
            <span className="w-7 h-7 rounded-lg bg-white/20 flex items-center justify-center font-bold text-xs">
              {selectedCount}
            </span>
            <span className="text-xs font-extrabold tracking-wide">
              {selectAllMatching
                ? t('leads.allMatchingSelected', { total })
                : t('leads.bulkToolbarCount', { count: selectedCount })}
            </span>

            {/* Quick Button to Select All across all pages if not already done */}
            {!selectAllMatching && total > leads.length && (
              <button
                type="button"
                onClick={handleSelectAllAcrossPages}
                className="px-2.5 py-1 rounded-lg bg-white/20 hover:bg-white/30 text-white font-bold text-[11px] underline underline-offset-2 transition-all cursor-pointer"
              >
                {t('leads.selectAllTotal', { total })}
              </button>
            )}
          </div>

          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={handleOpenBulkBlacklist}
              className="px-3 py-1.5 rounded-lg bg-white/15 hover:bg-white/25 text-white font-bold text-xs flex items-center gap-1.5 transition-all active:scale-95 cursor-pointer"
            >
              <ShieldAlert className="w-3.5 h-3.5 text-[#FF9F43]" />
              <span>{t('leads.bulkBlacklist')}</span>
            </button>

            <button
              type="button"
              onClick={handleOpenBulkDelete}
              className="px-3 py-1.5 rounded-lg bg-rose-500 hover:bg-rose-600 text-white font-bold text-xs flex items-center gap-1.5 shadow-md transition-all active:scale-95 cursor-pointer"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>{selectAllMatching ? t('leads.bulkDeleteAll', { total }) : t('leads.bulkDelete', { count: selectedCount })}</span>
            </button>

            <button
              type="button"
              onClick={handleClearSelection}
              className="p-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white/80 hover:text-white transition-colors cursor-pointer"
              title={t('common.clearSelection')}
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}


      {/* Leads Table Card */}
      <Card className="overflow-hidden shadow-sm">
        <div className="overflow-x-auto min-w-full">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200/80 dark:border-white/[0.08] bg-slate-50/75 dark:bg-white/[0.02] text-slate-500 dark:text-[#7E7F96] font-bold uppercase tracking-wider text-[11px]">
                {/* Select All Checkbox Header */}
                <th className="py-3.5 px-4 w-10 text-center">
                  <button
                    type="button"
                    onClick={handleToggleSelectAllPage}
                    className="p-1 rounded hover:bg-slate-200 dark:hover:bg-white/[0.08] text-slate-500 dark:text-slate-300 transition-colors cursor-pointer"
                    title={isAllCurrentPageSelected ? t('common.clearSelection') : t('common.selectAll')}
                  >
                    {selectAllMatching || isAllCurrentPageSelected ? (
                      <CheckSquare className="w-4 h-4 text-[#7367F0]" />
                    ) : isSomeCurrentPageSelected ? (
                      <MinusSquare className="w-4 h-4 text-[#7367F0]" />
                    ) : (
                      <Square className="w-4 h-4 text-slate-400" />
                    )}
                  </button>
                </th>
                <th className="py-3.5 px-4">{t('leads.colProfile')}</th>
                <th className="py-3.5 px-4">{t('leads.colContact')}</th>
                <th className="py-3.5 px-4">{t('leads.colLocation')}</th>
                <th className="py-3.5 px-4">{t('leads.colRatingWeb')}</th>
                <th className="py-3.5 px-4">{t('leads.colStatus')}</th>
                <th className="py-3.5 px-4 text-right">{t('leads.colActions')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-white/[0.04]">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto text-[#7367F0] mb-2" />
                    <span>{t('common.loading')}</span>
                  </td>
                </tr>
              ) : leads.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    <Users className="w-8 h-8 mx-auto text-slate-300 dark:text-slate-600 mb-2" />
                    <p className="font-bold text-slate-700 dark:text-slate-200">{t('leadFinder.noJobsFound')}</p>
                  </td>
                </tr>
              ) : (
                leads.map((lead) => {
                  const isSelected = selectedIds.includes(lead.id) || selectAllMatching;
                  return (
                    <tr 
                      key={lead.id} 
                      className={`transition-colors group ${
                        isSelected
                          ? 'bg-[#7367F0]/10 dark:bg-[#7367F0]/15'
                          : 'hover:bg-slate-50/70 dark:hover:bg-white/[0.02]'
                      }`}
                    >
                      {/* Row Checkbox */}
                      <td className="py-3.5 px-4 text-center">
                        <button
                          type="button"
                          onClick={() => handleToggleSingleSelect(lead.id)}
                          className="p-1 rounded hover:bg-slate-200 dark:hover:bg-white/[0.08] text-slate-500 dark:text-slate-300 transition-colors cursor-pointer"
                        >
                          {isSelected ? (
                            <CheckSquare className="w-4 h-4 text-[#7367F0]" />
                          ) : (
                            <Square className="w-4 h-4 text-slate-300 dark:text-slate-600 group-hover:text-slate-400" />
                          )}
                        </button>
                      </td>

                      {/* Name & Category */}
                      <td className="py-3.5 px-4 max-w-[240px]">
                        <div className="font-bold text-slate-800 dark:text-white text-xs truncate">
                          {lead.name}
                        </div>
                        <div className="flex items-center gap-1.5 mt-1 flex-wrap">
                          <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-[#7367F0]/10 text-[#7367F0] dark:bg-[#7367F0]/20 dark:text-[#A59DF8]">
                            {lead.category || t('common.general')}
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
                          <span>{lead.phone_e164 || lead.phone || t('leads.noPhone')}</span>
                        </div>
                        <div className="mt-1">
                          {lead.is_whatsapp_eligible ? (
                            <span className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded-full bg-[#25D366]/15 text-[#25D366] font-bold text-[10px]">
                              <WhatsAppIcon className="w-3 h-3" />
                              <span>{t('leads.whatsappActive')}</span>
                            </span>
                          ) : (
                            <span className="text-[10px] text-slate-400 font-sans">
                              {t('leads.whatsappUnverified')}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Location (Clean address without redundant sub-link) */}
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
                          <span className="text-slate-400 text-[10px]">{t('leads.noRating')}</span>
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

                      {/* Actions: 1. Send, 2. Google Maps, 3. Blacklist, 4. Delete */}
                      <td className="py-3.5 px-4 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end space-x-1.5">
                          <button
                            type="button"
                            onClick={() => handleOpenSendModal(lead)}
                            title={t('leads.quickSendTitle')}
                            className="p-1.5 rounded-lg text-[#25D366] hover:bg-[#25D366]/15 transition-colors cursor-pointer"
                          >
                            <Send className="w-4 h-4" />
                          </button>
                          <a
                            href={getGoogleMapsUrl(lead)}
                            target="_blank"
                            rel="noreferrer"
                            title="Google Maps"
                            className="p-1.5 rounded-lg text-slate-400 hover:text-[#7367F0] hover:bg-slate-100 dark:hover:bg-white/[0.08] transition-colors cursor-pointer"
                          >
                            <GoogleMapsIcon className="w-4 h-4" />
                          </a>
                          <button
                            type="button"
                            onClick={() => handleOpenSingleBlacklist(lead)}
                            title={t('blacklist.addNumber')}
                            className="p-1.5 rounded-lg text-slate-400 hover:text-[#FF9F43] hover:bg-amber-50 dark:hover:bg-amber-500/10 transition-colors cursor-pointer"
                          >
                            <ShieldAlert className="w-4 h-4" />
                          </button>
                          <button
                            type="button"
                            onClick={() => handleOpenSingleDelete(lead)}
                            title={t('common.delete')}
                            className="p-1.5 rounded-lg text-slate-400 hover:text-[#EA5455] hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-colors cursor-pointer"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {total > pageSize && (
          <div className="p-4 border-t border-slate-100 dark:border-white/[0.06] flex items-center justify-between text-xs text-slate-500 dark:text-[#7E7F96]">
            <span>
              {t('common.showing')} <strong>{total}</strong> {t('common.entries')} <strong>{(page - 1) * pageSize + 1} - {Math.min(page * pageSize, total)}</strong>
            </span>
            <div className="flex items-center space-x-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
                className="cursor-pointer"
              >
                {t('common.previous')}
              </Button>
              <span className="font-bold text-slate-700 dark:text-slate-200">
                {t('common.page')} {page} / {Math.ceil(total / pageSize)}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page * pageSize >= total}
                onClick={() => setPage(page + 1)}
                className="cursor-pointer"
              >
                {t('common.next')}
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* ========================================================================= */}
      {/* BEAUTIFUL DELETE CONFIRMATION MODAL */}
      {/* ========================================================================= */}
      {isDeleteModalOpen && typeof document !== 'undefined' && createPortal(
        <div 
          className="fixed inset-0 z-[99999] flex items-center justify-center p-4 bg-slate-900/60 animate-fade-in select-none"
          onClick={() => !isDeleting && setIsDeleteModalOpen(false)}
        >
          <div 
            className="w-full max-w-md bg-white dark:bg-[#2F3349] rounded-2xl shadow-2xl border border-slate-200 dark:border-white/[0.08] p-6 animate-scale-up"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header with Danger Badge */}
            <div className="flex items-center space-x-3 mb-4">
              <div className="w-11 h-11 rounded-2xl bg-rose-50 dark:bg-rose-500/10 text-[#EA5455] flex items-center justify-center shrink-0 border border-rose-200 dark:border-rose-500/20">
                <Trash2 className="w-6 h-6 stroke-[2.2]" />
              </div>
              <div>
                <h3 className="text-base font-extrabold text-slate-800 dark:text-white">
                  {isBulkDelete 
                    ? (selectAllMatching ? t('leads.bulkDeleteAll', { total }) : t('leads.bulkDelete', { count: selectedCount })) 
                    : t('leads.deleteConfirmTitle')}
                </h3>
                <p className="text-[11px] text-slate-400 font-medium">{t('leads.deleteConfirmMsg')}</p>
              </div>
            </div>

            {/* Modal Body Info */}
            <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-[#25293C] border border-slate-200/60 dark:border-white/[0.05] text-xs text-slate-600 dark:text-slate-300 space-y-3 mb-5">
              {!isBulkDelete && leadToDelete ? (
                <p>
                  <strong className="text-slate-800 dark:text-white font-bold">{leadToDelete.name}</strong> - {t('leads.deleteConfirmMsg')}
                </p>
              ) : (
                <div className="space-y-2">
                  <label className="flex items-start space-x-2.5 p-2 rounded-lg border border-slate-200 dark:border-white/[0.08] cursor-pointer hover:bg-slate-100 dark:hover:bg-white/[0.03] transition-colors">
                    <input
                      type="radio"
                      name="deleteScope"
                      checked={!selectAllMatching}
                      onChange={() => setSelectAllMatching(false)}
                      className="mt-0.5 text-[#EA5455] focus:ring-0"
                    />
                    <div>
                      <span className="font-bold text-slate-800 dark:text-white">
                        {t('leads.bulkDelete', { count: selectedIds.length })}
                      </span>
                    </div>
                  </label>

                  {total > leads.length && (
                    <label className="flex items-start space-x-2.5 p-2 rounded-lg border border-rose-200 dark:border-rose-500/30 bg-rose-50/50 dark:bg-rose-500/10 cursor-pointer hover:bg-rose-50 dark:hover:bg-rose-500/20 transition-colors">
                      <input
                        type="radio"
                        name="deleteScope"
                        checked={selectAllMatching}
                        onChange={() => setSelectAllMatching(true)}
                        className="mt-0.5 text-[#EA5455] focus:ring-0"
                      />
                      <div>
                        <span className="font-bold text-[#EA5455]">
                          {t('leads.bulkDeleteAll', { total })}
                        </span>
                      </div>
                    </label>
                  )}
                </div>
              )}
            </div>

            {/* Modal Actions */}
            <div className="flex items-center justify-end space-x-2.5">
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={isDeleting}
                onClick={() => setIsDeleteModalOpen(false)}
                className="cursor-pointer"
              >
                {t('common.cancel')}
              </Button>
              <Button
                type="button"
                size="sm"
                disabled={isDeleting}
                onClick={handleConfirmDelete}
                className="bg-[#EA5455] hover:bg-[#D43B3C] text-white font-bold space-x-1.5 shadow-md shadow-[#EA5455]/30 cursor-pointer"
              >
                {isDeleting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>{t('common.loading')}</span>
                  </>
                ) : (
                  <>
                    <Trash2 className="w-4 h-4" />
                    <span>{t('common.delete')}</span>
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* ========================================================================= */}
      {/* BEAUTIFUL BLACKLIST CONFIRMATION MODAL */}
      {/* ========================================================================= */}
      {isBlacklistModalOpen && typeof document !== 'undefined' && createPortal(
        <div 
          className="fixed inset-0 z-[99999] flex items-center justify-center p-4 bg-slate-900/60 animate-fade-in select-none"
          onClick={() => !isBlacklisting && setIsBlacklistModalOpen(false)}
        >
          <div 
            className="w-full max-w-md bg-white dark:bg-[#2F3349] rounded-2xl shadow-2xl border border-slate-200 dark:border-white/[0.08] p-6 animate-scale-up"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header with Amber Warning Badge */}
            <div className="flex items-center space-x-3 mb-4">
              <div className="w-11 h-11 rounded-2xl bg-amber-50 dark:bg-amber-500/10 text-[#FF9F43] flex items-center justify-center shrink-0 border border-amber-200 dark:border-amber-500/20">
                <ShieldAlert className="w-6 h-6 stroke-[2.2]" />
              </div>
              <div>
                <h3 className="text-base font-extrabold text-slate-800 dark:text-white">
                  {isBulkBlacklist ? t('blacklist.confirmBulkRemoveTitle') : t('blacklist.modalTitle')}
                </h3>
                <p className="text-[11px] text-slate-400 font-medium">{t('blacklist.subtitle')}</p>
              </div>
            </div>

            {/* Info Message */}
            <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-[#25293C] border border-slate-200/60 dark:border-white/[0.05] text-xs text-slate-600 dark:text-slate-300 space-y-2 mb-4">
              {!isBulkBlacklist && leadToBlacklist ? (
                <p>
                  <strong className="text-slate-800 dark:text-white font-bold">{leadToBlacklist.name}</strong> ({leadToBlacklist.phone_e164 || leadToBlacklist.phone})
                </p>
              ) : (
                <p>
                  {t('blacklist.selectedToolbarCount', { count: selectedCount })}
                </p>
              )}
            </div>

            {/* Reason Selection */}
            <div className="space-y-2 mb-5 text-xs">
              <label className="text-slate-700 dark:text-slate-300 font-bold block">{t('blacklist.blockReasonLabel')}</label>
              <div className="flex flex-wrap gap-1.5 mb-2">
                {[
                  'USER_REQUEST',
                  'BOUNCED',
                  'SPAM_COMPLAINT',
                  'MANUAL_BLACKLIST'
                ].map((r) => (
                  <button
                    key={r}
                    type="button"
                    onClick={() => setBlacklistReason(r)}
                    className={`px-2.5 py-1 rounded-lg text-[10px] font-bold border transition-all cursor-pointer ${
                      blacklistReason === r
                        ? 'bg-[#FF9F43]/15 text-[#FF9F43] border-[#FF9F43]'
                        : 'bg-white dark:bg-white/[0.03] border-slate-200 dark:border-white/[0.08] text-slate-600 dark:text-slate-300 hover:bg-slate-50'
                    }`}
                  >
                    {r === 'USER_REQUEST' ? t('blacklist.reasonUserRequest') : r === 'BOUNCED' ? t('blacklist.reasonBounced') : r === 'SPAM_COMPLAINT' ? t('blacklist.reasonSpamComplaint') : t('blacklist.reasonManual')}
                  </button>
                ))}
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end space-x-2.5">
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={isBlacklisting}
                onClick={() => setIsBlacklistModalOpen(false)}
                className="cursor-pointer"
              >
                {t('common.cancel')}
              </Button>
              <Button
                type="button"
                size="sm"
                disabled={isBlacklisting}
                onClick={handleConfirmBlacklist}
                className="bg-[#FF9F43] hover:bg-[#E58A32] text-white font-bold space-x-1.5 shadow-md shadow-[#FF9F43]/30 cursor-pointer"
              >
                {isBlacklisting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>{t('common.loading')}</span>
                  </>
                ) : (
                  <>
                    <ShieldAlert className="w-4 h-4" />
                    <span>{t('blacklist.addNumber')}</span>
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* ========================================================================= */}
      {/* ADD NEW LEAD MODAL */}
      {/* ========================================================================= */}
      {isAddModalOpen && typeof document !== 'undefined' && createPortal(
        <div 
          className="fixed inset-0 z-[99999] flex items-center justify-center p-4 bg-slate-900/60 animate-fade-in select-none"
          onClick={() => setIsAddModalOpen(false)}
        >
          <div 
            className="w-full max-w-md bg-white dark:bg-[#2F3349] rounded-2xl shadow-2xl border border-slate-200 dark:border-white/[0.08] p-6 animate-scale-up"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100 dark:border-white/[0.06]">
              <h3 className="text-base font-extrabold text-slate-800 dark:text-white flex items-center gap-2">
                <Plus className="w-5 h-5 text-[#7367F0]" />
                {t('leads.addNewLeadTitle')}
              </h3>
              <button 
                onClick={() => setIsAddModalOpen(false)}
                className="text-slate-400 hover:text-slate-700 dark:hover:text-white p-1 rounded-lg cursor-pointer"
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
                <label className="text-slate-700 dark:text-slate-300 font-bold block mb-1">{t('leads.leadNameRequired')}</label>
                <input
                  type="text"
                  value={newLeadName}
                  onChange={(e) => setNewLeadName(e.target.value)}
                  placeholder="e.g. Dentgroup Ataşehir"
                  className="w-full px-3 py-2 rounded-lg vuexy-input"
                  required
                />
              </div>

              <div>
                <label className="text-slate-700 dark:text-slate-300 font-bold block mb-1">{t('leads.leadPhoneRequired')}</label>
                <input
                  type="text"
                  value={newLeadPhone}
                  onChange={(e) => setNewLeadPhone(e.target.value)}
                  placeholder="e.g. +905321234567"
                  className="w-full px-3 py-2 rounded-lg vuexy-input font-mono"
                  required
                />
              </div>

              <div>
                <label className="text-slate-700 dark:text-slate-300 font-bold block mb-1">{t('leads.categoryLabel')}</label>
                <input
                  type="text"
                  value={newLeadCategory}
                  onChange={(e) => setNewLeadCategory(e.target.value)}
                  placeholder="e.g. Dental Clinic"
                  className="w-full px-3 py-2 rounded-lg vuexy-input"
                />
              </div>

              <div className="grid grid-cols-2 gap-2.5">
                <div>
                  <label className="text-slate-700 dark:text-slate-300 font-bold block mb-1">{t('leads.cityLabel')}</label>
                  <input
                    type="text"
                    value={newLeadCity}
                    onChange={(e) => setNewLeadCity(e.target.value)}
                    placeholder="İstanbul"
                    className="w-full px-3 py-2 rounded-lg vuexy-input"
                  />
                </div>
                <div>
                  <label className="text-slate-700 dark:text-slate-300 font-bold block mb-1">{t('leads.districtLabel')}</label>
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
                  className="cursor-pointer"
                >
                  {t('common.cancel')}
                </Button>
                <Button 
                  type="submit" 
                  size="sm" 
                  className="font-bold shadow-md shadow-[#7367F0]/30 cursor-pointer"
                >
                  {t('common.save')}
                </Button>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}

      {/* ========================================================================= */}
      {/* QUICK SINGLE MESSAGE SEND MODAL */}
      {/* ========================================================================= */}
      {isSendModalOpen && selectedLeadForSend && typeof document !== 'undefined' && createPortal(
        <div 
          className="fixed inset-0 z-[99999] flex items-center justify-center p-4 bg-slate-900/60 animate-fade-in select-none"
          onClick={() => setIsSendModalOpen(false)}
        >
          <div 
            className="w-full max-w-md bg-white dark:bg-[#2F3349] rounded-2xl shadow-2xl border border-slate-200 dark:border-white/[0.08] p-6 animate-scale-up"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100 dark:border-white/[0.06]">
              <h3 className="text-base font-extrabold text-slate-800 dark:text-white flex items-center gap-2">
                <Send className="w-4 h-4 text-[#25D366]" />
                {t('leads.quickSendTitle')}
              </h3>
              <button 
                onClick={() => setIsSendModalOpen(false)}
                className="text-slate-400 hover:text-slate-700 dark:hover:text-white p-1 rounded-lg cursor-pointer"
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
                <label className="text-slate-700 dark:text-slate-300 font-bold block mb-1">{t('whatsapp.testMessageText')}</label>
                <textarea
                  value={customMessage}
                  onChange={(e) => setCustomMessage(e.target.value)}
                  rows={5}
                  className="w-full p-3 rounded-lg vuexy-input leading-relaxed"
                  placeholder={t('leads.messagePlaceholder')}
                />
              </div>

              <div className="flex items-center justify-end space-x-2 pt-2">
                <Button 
                  type="button" 
                  variant="outline" 
                  size="sm" 
                  onClick={() => setIsSendModalOpen(false)}
                  className="cursor-pointer"
                >
                  {t('common.close')}
                </Button>
                <Button 
                  type="button" 
                  size="sm" 
                  disabled={isSending || !customMessage}
                  onClick={handleSendSingleMessage}
                  className="bg-[#25D366] hover:bg-[#1EBE5D] text-white font-bold space-x-1.5 cursor-pointer"
                >
                  {isSending ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>{t('leads.sending')}</span>
                    </>
                  ) : (
                    <>
                      <Send className="w-3.5 h-3.5" />
                      <span>{t('leads.sendNow')}</span>
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
};
