import React, { useState, useEffect, useRef } from 'react';
import { 
  Search, 
  MapPin, 
  Sparkles, 
  Play, 
  CheckCircle2, 
  Check,
  Terminal, 
  ExternalLink, 
  Phone, 
  Star, 
  Globe, 
  Send,
  Loader2,
  Navigation
} from 'lucide-react';
import { ApiClient, createWebSocket } from '../api/client';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Card } from '../components/ui/card';
import { SectorAutocomplete } from '../components/LeadFinder/SectorAutocomplete';
import { LocationMultiSelect } from '../components/LeadFinder/LocationMultiSelect';
import { WhatsAppIcon } from '../components/ui/whatsapp-icon';
import { GoogleMapsIcon } from '../components/ui/google-maps-icon';

interface LeadFinderPageProps {
  onNavigate: (tab: string) => void;
  onRefreshStats: () => void;
}

export const LeadFinderPage: React.FC<LeadFinderPageProps> = ({ onNavigate, onRefreshStats }) => {
  const [keyword, setKeyword] = useState('');
  const [selectedCity, setSelectedCity] = useState('');
  const [selectedDistricts, setSelectedDistricts] = useState<string[]>([]);
  const [maxResults, setMaxResults] = useState<number>(0); // 0 means Sınırsız
  const [isScraping, setIsScraping] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [discoveredLeads, setDiscoveredLeads] = useState<any[]>([]);
  const [progress, setProgress] = useState(0);

  const terminalContainerRef = useRef<HTMLDivElement>(null);
  const resultsSectionRef = useRef<HTMLDivElement>(null);
  const activeJobIdRef = useRef<number | null>(null);

  // Auto-scroll ONLY inside the terminal container without moving the browser viewport
  useEffect(() => {
    if (terminalContainerRef.current) {
      terminalContainerRef.current.scrollTop = terminalContainerRef.current.scrollHeight;
    }
  }, [logs]);

  const handleStartScrape = async () => {
    if (!keyword.trim() || !selectedCity) return;

    const locationDisplay = selectedDistricts.length > 0
      ? `${selectedCity} > ${selectedDistricts.join(', ')}`
      : `${selectedCity} (Tüm İl Geneli)`;

    setIsScraping(true);
    setProgress(5);
    setLogs([
      `[${new Date().toLocaleTimeString()}] 🚀 Arama Başlatıldı: "${keyword}"`,
      `[${new Date().toLocaleTimeString()}] 📍 Lokasyon: ${locationDisplay}`,
      `[${new Date().toLocaleTimeString()}] 🎯 Hedef: ${maxResults === 0 ? 'Sınırsız' : `${maxResults} İşletme`}`
    ]);
    setDiscoveredLeads([]);

    try {
      const job = await ApiClient.startScraper({
        keyword: keyword.trim(),
        city: selectedCity,
        districts: selectedDistricts,
        max_results: maxResults,
      });

      activeJobIdRef.current = job.id;

      setLogs((prev) => [
        ...prev,
        `[${new Date().toLocaleTimeString()}] 📡 Görev #${job.id} devrede. ${locationDisplay} taranıyor...`,
      ]);

      // Connect to WebSocket to stream live results — filter by job_id
      const ws = createWebSocket((eventData) => {
        // === JOB ISOLATION: Only process events for the active job ===
        if (eventData.job_id !== undefined && eventData.job_id !== activeJobIdRef.current) {
          return; // Ignore events from other jobs
        }

        if (eventData.event === 'scraper_progress') {
          const d = eventData.data;
          if (d.type === 'log') {
            setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ${d.message}`]);
            if (d.progress) setProgress(d.progress);
          } else if (d.type === 'lead_found' && d.lead) {
            setDiscoveredLeads((prev) => {
              const exists = prev.some(
                (l) =>
                  (l.place_id && d.lead.place_id && l.place_id === d.lead.place_id) ||
                  (l.phone_e164 && d.lead.phone_e164 && l.phone_e164 === d.lead.phone_e164) ||
                  (l.name.toLowerCase() === d.lead.name.toLowerCase() && l.district === d.lead.district)
              );
              if (exists) return prev;
              return [...prev, d.lead];
            });
          }
        } else if (eventData.event === 'scraper_completed') {
          setProgress(100);
          setIsScraping(false);
          if (eventData.leads && eventData.leads.length > 0) {
            setDiscoveredLeads(eventData.leads);
          }
          const m = eventData.metrics;
          const metricLogs = m ? [
            `[${new Date().toLocaleTimeString()}] 📊 Keşif Özeti: ${m.queries_executed || 0} sorgu, ${m.pages_visited || 0} sayfa tarandı.`,
            `[${new Date().toLocaleTimeString()}] 🔎 ${m.raw_results_found || 0} ham aday bulundu → ${m.duplicate_merged || 0} tekrar birleştirildi → ${eventData.total_found || eventData.total_new_leads} işletme kaydedildi.`
          ] : [];
          setLogs((prev) => [
            ...prev,
            ...metricLogs,
            `[${new Date().toLocaleTimeString()}] ✅ Tarama tamamlandı! Toplam ${eventData.total_found || eventData.total_new_leads} işletme listelendi.`,
          ]);
          onRefreshStats();
          ws.close();

          // Smoothly scroll down to the results section ONLY after all results have been found
          setTimeout(() => {
            resultsSectionRef.current?.scrollIntoView({ behavior: 'smooth' });
          }, 300);
        } else if (eventData.event === 'scraper_failed') {
          setIsScraping(false);
          setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ❌ Tarama hatası: ${eventData.error}`]);
          ws.close();
        }
      });

    } catch (err: any) {
      setIsScraping(false);
      setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ❌ Hata: ${err.message}`]);
    }
  };

  const getGoogleMapsUrl = (lead: any) => {
    if (lead.maps_url) return lead.maps_url;
    if (lead.google_maps_url) return lead.google_maps_url;
    if (lead.latitude && lead.longitude && lead.latitude !== 0) {
      return `https://www.google.com/maps/search/?api=1&query=${lead.latitude},${lead.longitude}`;
    }
    const query = `${lead.name} ${lead.address || ''} ${lead.city || ''}`.trim();
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
  };

  return (
    <div className="space-y-4 sm:space-y-6 pb-16 select-none animate-fade-in">
      {/* Search Filter Card */}
      <Card className="p-4 sm:p-6 lg:p-7 relative overflow-visible z-20">
        <div className="flex items-center space-x-1.5 text-xs font-bold text-[#7367F0] uppercase tracking-wider mb-2">
          <Sparkles className="w-4 h-4" />
          <span>İşletme Ara</span>
        </div>
        <h2 className="text-lg sm:text-xl lg:text-2xl font-extrabold text-slate-800 dark:text-white tracking-tight">
          Sektör ve Lokasyona Göre İşletmeleri Otomatik Toplayın
        </h2>
        <p className="text-xs lg:text-sm text-slate-500 dark:text-[#7E7F96] mt-1 max-w-3xl leading-relaxed font-medium">
          İl ve ilçe seçerek işletmelerin doğrulanmış telefon numaralarını, adreslerini, puanlarını ve web sitelerini canlı dizinlerden toplayın.
        </p>

        {/* Form Controls Grid */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3.5 mt-5 sm:mt-6 items-end">
          {/* Sector Autocomplete Input */}
          <div className="md:col-span-5 relative">
            <SectorAutocomplete
              value={keyword}
              onChange={setKeyword}
              disabled={isScraping}
            />
          </div>

          {/* Location Multi-Select (City + Districts) */}
          <div className="md:col-span-4 relative">
            <LocationMultiSelect
              selectedCity={selectedCity}
              selectedDistricts={selectedDistricts}
              onChange={(city, districts) => {
                setSelectedCity(city);
                setSelectedDistricts(districts);
              }}
              onCityChange={(city) => setSelectedCity(city)}
              onDistrictsChange={(districts) => setSelectedDistricts(districts)}
              disabled={isScraping}
            />
          </div>

          {/* Target Limit Selector */}
          <div className="md:col-span-1 space-y-1.5">
            <label className="text-xs font-bold text-slate-700 dark:text-slate-200">Hedef</label>
            <select
              value={maxResults}
              onChange={(e) => setMaxResults(Number(e.target.value))}
              className="w-full h-11 px-2.5 rounded-lg vuexy-input text-xs font-bold"
              disabled={isScraping}
            >
              <option value={0}>Sınırsız</option>
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={35}>35</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>

          {/* Search Button */}
          <div className="md:col-span-2">
            <Button
              onClick={handleStartScrape}
              disabled={isScraping || !keyword || !selectedCity}
              className="w-full h-11 font-bold shadow-md shadow-[#7367F0]/30 space-x-2 flex items-center justify-center text-xs"
            >
              {isScraping ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Aranıyor...</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>İşletmeleri Bul</span>
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Selected Summary Bar */}
        <div className="mt-4 pt-3 border-t border-slate-100 dark:border-white/[0.06] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-xs">
          <div className="flex items-center space-x-1.5 flex-wrap gap-y-1">
            <span className="text-slate-400 dark:text-[#7E7F96] font-medium">Bölge:</span>
            {selectedCity ? (
              <>
                <Badge variant="primary" className="font-bold text-[11px]">
                  {selectedCity}
                </Badge>
                {selectedDistricts.length > 0 ? (
                  selectedDistricts.map((dist) => (
                    <span
                      key={dist}
                      className="text-[11px] font-bold px-2 py-0.5 rounded bg-slate-100 dark:bg-white/[0.05] text-slate-700 dark:text-slate-200"
                    >
                      {dist}
                    </span>
                  ))
                ) : (
                  <span className="text-[11px] text-slate-400 italic">(Tüm İl Geneli)</span>
                )}
              </>
            ) : (
              <span className="text-[11px] text-slate-400 italic">Henüz Lokasyon Seçilmedi</span>
            )}
          </div>

          <div className="text-[11px] text-slate-500 dark:text-[#7E7F96] shrink-0">
            Hedef: <strong className="text-slate-800 dark:text-white font-bold">{maxResults === 0 ? 'Sınırsız' : `${maxResults} İşletme`}</strong>
          </div>
        </div>
      </Card>

      {/* Progress & Live Console Output */}
      {(isScraping || logs.length > 0) && (
        <Card className="p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Terminal className="w-4 h-4 text-[#7367F0]" />
              <span className="text-xs font-bold text-slate-800 dark:text-white uppercase tracking-wider">
                Arama Terminali & İlerleme
              </span>
            </div>
            <Badge variant="primary" className="font-mono">%{progress}</Badge>
          </div>

          <div className="h-2 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden p-0.5">
            <div 
              className="h-full bg-gradient-to-r from-[#7367F0] to-[#9E95F5] rounded-full transition-all duration-500 shadow-sm"
              style={{ width: `${progress}%` }}
            />
          </div>

          <div 
            ref={terminalContainerRef}
            className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-[#00CFE8] font-mono text-xs max-h-48 overflow-y-auto space-y-1.5 shadow-inner"
          >
            {logs.map((log, i) => (
              <div key={i} className="leading-relaxed">
                {log}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Discovered Real Leads Grid */}
      {discoveredLeads.length > 0 && (
        <div ref={resultsSectionRef} className="space-y-4 pt-2 animate-fade-in">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-extrabold text-slate-800 dark:text-white">
                Keşfedilen Gerçek İşletmeler ({discoveredLeads.length})
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Google Maps ve harita servislerinden doğrulanmış güncel işletme profilleri
              </p>
            </div>
            <div className="flex items-center space-x-3">
              <Button
                variant="outline"
                onClick={() => onNavigate('leads')}
                className="text-xs font-bold space-x-1.5"
              >
                CRM Tablosunda Gör
              </Button>
            </div>
          </div>

          {/* Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {discoveredLeads.map((lead, idx) => (
              <Card key={lead.id || `lead-${idx}`} className="p-5 hover:shadow-md transition-shadow flex flex-col justify-between h-full space-y-4">
                <div>
                  {/* Full Business Name & Entity Badges */}
                  <div className="flex items-start justify-between gap-2">
                    <h4 className="text-sm font-extrabold text-slate-800 dark:text-white leading-snug break-words">
                      {lead.name}
                    </h4>
                    {lead.is_verified ? (
                      <span className="shrink-0 inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-[#28C76F]/15 text-[#28C76F] border border-[#28C76F]/20">
                        <Check className="w-2.5 h-2.5" />
                        <span>Doğrulandı</span>
                      </span>
                    ) : (
                      <span className="shrink-0 inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded bg-[#FF9F43]/15 text-[#FF9F43] border border-[#FF9F43]/20">
                        <span>Aday Profil</span>
                      </span>
                    )}
                  </div>
                  
                  {/* Category & Entity Type placed below the title */}
                  <div className="mt-1.5 flex items-center gap-1.5 flex-wrap">
                    <span className="inline-block text-[10px] font-bold px-2 py-0.5 rounded bg-[#7367F0]/10 text-[#7367F0] dark:bg-[#7367F0]/20 dark:text-[#A59DF8]">
                      {lead.category || keyword}
                    </span>
                    {lead.entity_type && (
                      <span className="inline-block text-[9px] font-mono uppercase px-1.5 py-0.5 rounded bg-slate-100 dark:bg-white/[0.08] text-slate-600 dark:text-slate-300">
                        {lead.entity_type === 'CLINIC' ? '🏥 Klinik' : lead.entity_type === 'COMPANY' ? '🏢 Şirket' : lead.entity_type === 'PERSON' ? '👤 Şahıs' : '🏬 İşletme'}
                      </span>
                    )}
                  </div>

                  <div className="mt-3.5 space-y-2 text-xs text-slate-500 dark:text-[#7E7F96]">
                    {/* Phone Box with WhatsApp Brand Icon */}
                    <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 dark:bg-[#25293C] border border-slate-200/60 dark:border-white/[0.05]">
                      <div className="flex items-center space-x-2 text-[#7367F0] font-mono font-bold text-xs">
                        <Phone className="w-3.5 h-3.5 shrink-0" />
                        <span className="truncate">
                          {lead.phone_e164 && !lead.phone_e164.startsWith('+90000')
                            ? lead.phone_e164
                            : (lead.phone && !lead.phone.startsWith('+90000') && lead.phone !== 'Belirtilmemiş' ? lead.phone : 'Telefon Belirtilmemiş')}
                        </span>
                      </div>

                      {lead.is_whatsapp_eligible ? (
                        <div 
                          className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full bg-[#25D366]/15 text-[#25D366] font-bold text-[11px] shadow-sm shrink-0"
                          title="Doğrulanmış WhatsApp Numarası"
                        >
                          <WhatsAppIcon className="w-3.5 h-3.5 fill-current" />
                          <span>WhatsApp</span>
                        </div>
                      ) : lead.phone_e164 && !lead.phone_e164.startsWith('+90000') ? (
                        <Badge variant="default" className="text-[9px] px-1.5 py-0 font-sans shrink-0">
                          Sabit Hat
                        </Badge>
                      ) : (
                        <span className="text-[9px] font-sans px-1.5 py-0.5 rounded bg-slate-200/60 dark:bg-white/[0.06] text-slate-500 shrink-0">
                          Numara Yok
                        </span>
                      )}
                    </div>

                    {/* Address & District */}
                    <div className="flex items-center space-x-2">
                      <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                      <span className="line-clamp-2 text-slate-600 dark:text-slate-300">
                        {lead.address || `${lead.district ? `${lead.district}, ` : ''}${lead.city}`}
                      </span>
                    </div>

                    {/* Rating & Reviews */}
                    {lead.rating ? (
                      <div className="flex items-center space-x-2">
                        <Star className="w-3.5 h-3.5 text-[#FF9F43] fill-[#FF9F43] shrink-0" />
                        <span className="text-slate-800 dark:text-white font-bold">{lead.rating}</span>
                        {lead.reviews_count ? (
                          <span className="text-slate-400">({lead.reviews_count} yorum)</span>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                </div>

                {/* Card Action Footer with Google Maps & Clean Website Links */}
                <div className="pt-3 border-t border-slate-100 dark:border-white/[0.06] flex items-center justify-between gap-2 text-xs">
                  {/* Google Maps Button */}
                  <a
                    href={getGoogleMapsUrl(lead)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-white/[0.06] hover:bg-slate-200 dark:hover:bg-white/[0.1] text-slate-700 dark:text-slate-200 border border-slate-200/60 dark:border-white/[0.08] font-bold transition-all active:scale-95 text-[11px] group"
                    title="Google Maps'te Aç"
                  >
                    <GoogleMapsIcon className="w-3.5 h-3.5 group-hover:scale-110 transition-transform" />
                    <span>Google Maps'te Aç</span>
                    <ExternalLink className="w-2.5 h-2.5 text-slate-400" />
                  </a>

                  {/* Clean Website Link: Only render if valid website exists */}
                  {lead.website ? (
                    <a
                      href={lead.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-slate-500 hover:text-[#7367F0] font-medium transition-colors text-[11px] truncate max-w-[140px]"
                      title={lead.website}
                    >
                      <Globe className="w-3.5 h-3.5 shrink-0" />
                      <span className="truncate">{lead.website.replace(/^https?:\/\/(www\.)?/, '')}</span>
                      <ExternalLink className="w-2.5 h-2.5 shrink-0" />
                    </a>
                  ) : (
                    <span className="text-[10px] text-slate-400 italic">Web Sitesi Yok</span>
                  )}
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
