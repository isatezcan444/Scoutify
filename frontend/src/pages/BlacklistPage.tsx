import React, { useState, useEffect, useRef } from 'react';
import { 
  ShieldAlert, 
  Plus, 
  Trash2, 
  Loader2, 
  Phone, 
  Search, 
  Building2, 
  Save,
  CheckSquare,
  Square,
  MinusSquare,
  RotateCcw
} from 'lucide-react';
import { ApiClient } from '../api/client';
import { BlacklistEntry, Lead } from '../types';
import {
  Button,
  Badge,
  Card,
  PageHeader,
  BulkActionToolbar,
  ToolbarActionButton,
  Modal,
  EmptyState,
  Pagination
} from '../components/ui';
import { SearchInput, Select } from '../components/forms';
import { useToast } from '../context/ToastContext';
import { useI18n } from '../context/I18nContext';

export const BlacklistPage: React.FC = () => {
  const toast = useToast();
  const { t } = useI18n();
  const [blacklist, setBlacklist] = useState<BlacklistEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(false);
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Table Search & Filter State (SearchInput debounces internally)
  const [search, setSearch] = useState('');
  const [reasonFilter, setReasonFilter] = useState('');

  // Multi-Selection State (Gmail-style)
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [selectAllMatching, setSelectAllMatching] = useState(false);
  const [isBulkRemoving, setIsBulkRemoving] = useState(false);

  // Form & Lead Search State
  const [newReason, setNewReason] = useState('USER_REQUEST');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Lead[]>([]);
  const [isSearchingLeads, setIsSearchingLeads] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const searchContainerRef = useRef<HTMLDivElement>(null);

  // Fetch paginated blacklist from server
  const fetchBlacklist = async () => {
    setLoading(true);
    try {
      const data = await ApiClient.getBlacklist({
        page,
        size: pageSize,
        search: search.trim() || undefined,
        reason: reasonFilter || undefined,
      });
      setBlacklist(data.items || []);
      setTotal(data.total || 0);
    } catch (err: any) {
      toast.error(err.message || t('common.error'), t('toast.errorTitle'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBlacklist();
  }, [page, pageSize, search, reasonFilter]);

  // Clear selection on page/filter change unless all-matching is active
  useEffect(() => {
    if (!selectAllMatching) {
      setSelectedIds([]);
    }
  }, [page, pageSize, search, reasonFilter]);

  // Selection Checkbox Logic
  const currentPageIds = blacklist.map((item) => item.id);
  const isAllCurrentPageSelected =
    blacklist.length > 0 && currentPageIds.every((id) => selectedIds.includes(id));
  const isSomeCurrentPageSelected =
    currentPageIds.some((id) => selectedIds.includes(id)) && !isAllCurrentPageSelected;

  const handleToggleSelectAllPage = () => {
    if (selectAllMatching) {
      setSelectAllMatching(false);
      setSelectedIds([]);
      return;
    }

    if (isAllCurrentPageSelected) {
      setSelectedIds((prev) => prev.filter((id) => !currentPageIds.includes(id)));
    } else {
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

  const selectedCount = selectAllMatching ? total : selectedIds.length;

  // Debounced Lead Search in Modal
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
        console.error('Lead search error in blacklist modal:', err);
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
      toast.error(t('blacklist.leadNotSelectedError'), t('common.warning'));
      return;
    }

    const phoneToSubmit = (selectedLead.phone_e164 || selectedLead.phone || '').trim();
    if (!phoneToSubmit) {
      toast.error(t('blacklist.noPhoneInLead'), t('common.error'));
      return;
    }

    setSubmitting(true);
    try {
      await ApiClient.addToBlacklist(phoneToSubmit, newReason);
      toast.success(
        t('blacklist.addedSuccess', { name: selectedLead.name, phone: phoneToSubmit }),
        t('common.success')
      );
      setIsAddOpen(false);
      handleClearSelectedLead();
      fetchBlacklist();
    } catch (err: any) {
      toast.error(err.message || t('common.error'), t('toast.errorTitle'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleRemove = async (id: number, phone: string, leadName?: string) => {
    const displayName = leadName || phone;
    const ok = await toast.confirm({
      title: t('blacklist.confirmRemoveTitle'),
      message: t('blacklist.confirmRemoveMsg', { name: displayName, phone }),
      confirmText: t('blacklist.unblockButton'),
      cancelText: t('common.cancel'),
      variant: 'warning',
    });
    if (!ok) return;

    try {
      await ApiClient.removeFromBlacklist(id);
      toast.success(t('blacklist.removedSuccess'), t('common.success'));
      setSelectedIds((prev) => prev.filter((x) => x !== id));
      fetchBlacklist();
    } catch (err: any) {
      toast.error(err.message || t('common.error'), t('toast.errorTitle'));
    }
  };

  const handleBulkRemove = async () => {
    if (selectedCount === 0) return;

    const ok = await toast.confirm({
      title: selectAllMatching ? t('blacklist.confirmClearAllTitle') : t('blacklist.confirmBulkRemoveTitle'),
      message: selectAllMatching
        ? t('blacklist.confirmClearAllMsg', { total })
        : t('blacklist.confirmBulkRemoveMsg', { count: selectedCount }),
      confirmText: selectAllMatching ? t('blacklist.unblockAllButton', { total }) : t('blacklist.unblockBulkButton', { count: selectedCount }),
      cancelText: t('common.cancel'),
      variant: 'warning',
    });
    if (!ok) return;

    setIsBulkRemoving(true);
    try {
      const res = await ApiClient.bulkRemoveFromBlacklist(
        selectAllMatching
          ? {
              delete_all_matching: true,
              search: search.trim() || undefined,
              reason: reasonFilter || undefined,
            }
          : { ids: selectedIds }
      );
      toast.success(t('blacklist.bulkRemovedSuccess', { count: res.deleted_count }), t('common.success'));
      handleClearSelection();
      fetchBlacklist();
    } catch (err: any) {
      toast.error(err.message || t('common.error'), t('toast.errorTitle'));
    } finally {
      setIsBulkRemoving(false);
    }
  };

  const getReasonLabel = (reason: string) => {
    switch (reason) {
      case 'USER_REQUEST':
        return t('blacklist.reasonUserRequest');
      case 'BOUNCED':
        return t('blacklist.reasonBounced');
      case 'SPAM_COMPLAINT':
        return t('blacklist.reasonSpamComplaint');
      case 'MANUAL_BLACKLIST':
        return t('blacklist.reasonManual');
      default:
        return reason;
    }
  };

  return (
    <div className="space-y-6 pb-16 select-none animate-fade-in">
      {/* Page Header & Top Actions */}
      <PageHeader
        title={`${t('blacklist.title')} ${t('blacklist.countBadge', { count: total })}`}
        subtitle={t('blacklist.subtitle')}
        icon={ShieldAlert}
        actions={
          <Button
            variant="destructive"
            size="sm"
            onClick={handleOpenAddModal}
            className="space-x-1.5 font-bold cursor-pointer shadow-md shadow-[#EA5455]/20"
          >
            <Plus className="w-4 h-4" />
            <span>{t('blacklist.addNumber')}</span>
          </Button>
        }
      />

      {/* Filter & Search Bar */}
      <Card className="p-4">
        <div className="flex flex-col md:flex-row items-center gap-3">
          <div className="flex-1 w-full">
            <SearchInput
              value={search}
              onChange={(val) => {
                setSearch(val);
                setPage(1);
              }}
              placeholder={t('blacklist.searchPlaceholder')}
            />
          </div>

          <div className="flex items-center gap-2 w-full md:w-auto">
            <div className="w-full md:w-56">
              <Select
                value={reasonFilter}
                onChange={(e) => {
                  setReasonFilter(e.target.value);
                  setPage(1);
                }}
                options={[
                  { value: '', label: t('blacklist.filterAllReasons') },
                  { value: 'USER_REQUEST', label: t('blacklist.reasonUserRequest') },
                  { value: 'BOUNCED', label: t('blacklist.reasonBounced') },
                  { value: 'SPAM_COMPLAINT', label: t('blacklist.reasonSpamComplaint') },
                  { value: 'MANUAL_BLACKLIST', label: t('blacklist.reasonManual') },
                ]}
              />
            </div>

            {(search || reasonFilter) && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setSearch('');
                  setReasonFilter('');
                  setPage(1);
                }}
                className="text-xs font-bold shrink-0 space-x-1 cursor-pointer"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>{t('common.clear')}</span>
              </Button>
            )}
          </div>
        </div>
      </Card>

      {/* Centralized Bulk Action Toolbar */}
      <BulkActionToolbar
        selectedCount={selectedCount}
        totalCount={total}
        selectAllMatching={selectAllMatching}
        onSelectAllMatching={handleSelectAllAcrossPages}
        onClearSelection={handleClearSelection}
        actions={
          <ToolbarActionButton
            tone="danger"
            disabled={isBulkRemoving}
            onClick={handleBulkRemove}
          >
            {isBulkRemoving ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>{t('common.loading')}</span>
              </>
            ) : (
              <>
                <Trash2 className="w-3.5 h-3.5" />
                <span>
                  {selectAllMatching
                    ? t('blacklist.bulkDeleteAllButton', { total })
                    : t('blacklist.bulkDeleteButton', { count: selectedCount })}
                </span>
              </>
            )}
          </ToolbarActionButton>
        }
      />

      {/* Blacklist Table */}
      <Card className="overflow-hidden shadow-sm">
        <div className="overflow-x-auto min-w-full">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200/80 dark:border-white/[0.08] bg-slate-50/75 dark:bg-white/[0.02] text-slate-500 dark:text-[#7E7F96] font-bold uppercase tracking-wider text-[11px]">
                {/* Checkbox Header */}
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
                <th className="py-3.5 px-4">{t('blacklist.blockReasonLabel')}</th>
                <th className="py-3.5 px-4">{t('common.date')}</th>
                <th className="py-3.5 px-4 text-right">{t('common.actions')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-white/[0.04] text-slate-700 dark:text-slate-300 font-medium">
              {loading ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-400">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto text-[#EA5455] mb-2" />
                    <span className="text-xs font-bold block">{t('common.loading')}</span>
                  </td>
                </tr>
              ) : blacklist.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-0">
                    <EmptyState
                      icon={ShieldAlert}
                      title={total === 0 ? t('blacklist.emptyList') : t('blacklist.emptySearch')}
                      description={t('blacklist.subtitle')}
                    />
                  </td>
                </tr>
              ) : (
                blacklist.map((entry) => {
                  const isSelected = selectedIds.includes(entry.id) || selectAllMatching;
                  return (
                    <tr 
                      key={entry.id} 
                      className={`transition-colors group ${
                        isSelected 
                          ? 'bg-[#7367F0]/10 dark:bg-[#7367F0]/15' 
                          : 'hover:bg-slate-50/60 dark:hover:bg-white/[0.02]'
                      }`}
                    >
                      {/* Checkbox Cell */}
                      <td className="py-3.5 px-4 text-center">
                        <button
                          type="button"
                          onClick={() => handleToggleSingleSelect(entry.id)}
                          className="p-1 rounded hover:bg-slate-200 dark:hover:bg-white/[0.08] text-slate-500 dark:text-slate-300 transition-colors cursor-pointer"
                        >
                          {isSelected ? (
                            <CheckSquare className="w-4 h-4 text-[#7367F0]" />
                          ) : (
                            <Square className="w-4 h-4 text-slate-300 dark:text-slate-600 group-hover:text-slate-400" />
                          )}
                        </button>
                      </td>

                      {/* 1. Business Profile */}
                      <td className="py-3.5 px-4 max-w-[280px]">
                        <div className="font-bold text-slate-800 dark:text-white text-xs truncate">
                          {entry.lead_name || t('leads.noPhone')}
                        </div>
                        <div className="flex items-center gap-1.5 mt-1 flex-wrap">
                          <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-[#7367F0]/10 text-[#7367F0] dark:bg-[#7367F0]/20 dark:text-[#A59DF8]">
                            {entry.lead_category || t('common.general')}
                          </span>
                          {(entry.lead_district || entry.lead_city) && (
                            <span className="text-[10px] text-slate-400 font-medium">
                              • {[entry.lead_district, entry.lead_city].filter(Boolean).join(', ')}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* 2. Contact */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <div className="flex items-center space-x-2 font-mono font-bold text-xs text-slate-700 dark:text-slate-200">
                          <Phone className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                          <span>{entry.phone_e164}</span>
                        </div>
                      </td>

                      {/* 3. Block Reason */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <Badge variant="danger" className="text-[11px] font-bold">
                          {getReasonLabel(entry.reason)}
                        </Badge>
                      </td>

                      {/* 4. Date */}
                      <td className="py-3.5 px-4 whitespace-nowrap text-slate-500 dark:text-[#7E7F96] font-sans">
                        {new Date(entry.created_at).toLocaleString()}
                      </td>

                      {/* 5. Actions */}
                      <td className="py-3.5 px-4 text-right whitespace-nowrap">
                        <button
                          onClick={() => handleRemove(entry.id, entry.phone_e164, entry.lead_name)}
                          className="text-slate-400 hover:text-[#EA5455] p-1.5 rounded-lg hover:bg-[#EA5455]/10 transition-colors cursor-pointer"
                          title={t('blacklist.confirmRemoveTitle')}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Centralized Pagination */}
        {total > 0 && (
          <Pagination
            currentPage={page}
            totalItems={total}
            pageSize={pageSize}
            onPageChange={(newPage) => setPage(newPage)}
            onPageSizeChange={(newSize) => {
              setPageSize(newSize);
              setPage(1);
            }}
          />
        )}
      </Card>

      {/* Centralized Add to Blacklist Modal */}
      <Modal
        isOpen={isAddOpen}
        onClose={() => setIsAddOpen(false)}
        title={t('blacklist.modalTitle')}
        subtitle={t('blacklist.modalSubtitle')}
        icon={ShieldAlert}
        variant="danger"
        maxWidth="md"
      >
        <form onSubmit={handleAdd} className="space-y-4">
          {/* Mandatory Lead Search Field */}
          <div ref={searchContainerRef} className="relative">
            <label className="text-slate-700 dark:text-slate-300 font-bold block mb-1 flex items-center justify-between">
              <span>{t('blacklist.leadSearchLabel')}</span>
              {selectedLead && (
                <button
                  type="button"
                  onClick={handleClearSelectedLead}
                  className="text-[10px] text-[#7367F0] hover:underline font-bold cursor-pointer"
                >
                  {t('blacklist.changeSelection')}
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
                  placeholder={t('blacklist.leadSearchPlaceholder')}
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
                    <span>{selectedLead.phone_e164 || selectedLead.phone || t('leads.noPhone')}</span>
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
                    {t('common.selected')}
                  </Badge>
                  <button
                    type="button"
                    onClick={handleClearSelectedLead}
                    className="text-[10px] text-[#7367F0] hover:underline font-bold cursor-pointer"
                  >
                    {t('blacklist.changeSelection')}
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
                          <span>
                            {[lead.district, lead.city].filter(Boolean).join(', ')}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="text-right">
                      <span className="text-xs font-mono font-bold text-slate-700 dark:text-slate-300 block">
                        {lead.phone_e164 || lead.phone || t('leads.noPhone')}
                      </span>
                      <span className="text-[9px] text-[#7367F0] group-hover:underline font-bold">
                        {t('common.selected')} ↵
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
              {t('blacklist.blockReasonLabel')}
            </label>
            <select
              value={newReason}
              onChange={(e) => setNewReason(e.target.value)}
              className="w-full p-2.5 rounded-lg vuexy-input text-xs font-bold cursor-pointer"
            >
              <option value="USER_REQUEST">{t('blacklist.reasonUserRequest')}</option>
              <option value="BOUNCED">{t('blacklist.reasonBounced')}</option>
              <option value="SPAM_COMPLAINT">{t('blacklist.reasonSpamComplaint')}</option>
              <option value="MANUAL_BLACKLIST">{t('blacklist.reasonManual')}</option>
            </select>
          </div>

          {/* Modal Actions */}
          <div className="pt-3 flex items-center space-x-2 border-t border-slate-100 dark:border-white/[0.08]">
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsAddOpen(false)}
              className="w-1/2 font-bold cursor-pointer"
              disabled={submitting}
            >
              {t('common.cancel')}
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
                  <span>{t('common.loading')}</span>
                </>
              ) : (
                <>
                  <Save className="w-3.5 h-3.5" />
                  <span>{t('common.save')}</span>
                </>
              )}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
