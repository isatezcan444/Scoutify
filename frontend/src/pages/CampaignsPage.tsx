import React, { useState, useEffect } from 'react';
import { 
  Send, 
  Sparkles, 
  Play, 
  Clock, 
  ShieldCheck, 
  Shuffle, 
  Eye, 
  Loader2, 
  Sliders, 
  Layers 
} from 'lucide-react';
import { ApiClient } from '../api/client';
import { Campaign, CampaignStatus } from '../types';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { getStoredAntiBanConfig, ANTI_BAN_PRESETS } from '../utils/antiBanSettings';
import { useToast } from '../context/ToastContext';

interface CampaignsPageProps {
  onRefreshStats: () => void;
}

export const CampaignsPage: React.FC<CampaignsPageProps> = ({ onRefreshStats }) => {
  const toast = useToast();
  const storedConfig = getStoredAntiBanConfig();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'list' | 'builder'>('list');

  // Campaign Builder Form
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [template, setTemplate] = useState(
    "{Merhaba|Selamlar|İyi günler} {name} Yetkilisi,\n\n{city} {district} bölgesindeki {category} profilinizi inceledik. Google'daki {rating} yıldızlı puanınız çok başarılı! 🌟\n\nKlinikler için geliştirdiğimiz otomatik WhatsApp randevu ve hatırlatma sistemimizle hasta kaçırma oranını %40 azaltıyoruz. Size 2 dakikalık kısa bir demo sunabilir miyiz?\n\n{İyi çalışmalar dileriz|Saygılarımızla}."
  );
  const [minDelay, setMinDelay] = useState(storedConfig.minDelaySeconds);
  const [maxDelay, setMaxDelay] = useState(storedConfig.maxDelaySeconds);
  const [typingDelay, setTypingDelay] = useState(storedConfig.typingDelaySeconds);
  const [workingHoursEnabled, setWorkingHoursEnabled] = useState(storedConfig.workingHoursEnabled);
  const [workingHoursStart, setWorkingHoursStart] = useState(storedConfig.workingHoursStart);
  const [workingHoursEnd, setWorkingHoursEnd] = useState(storedConfig.workingHoursEnd);

  // Spintax Preview State
  const [permutationsCount, setPermutationsCount] = useState(1);
  const [previewSamples, setPreviewSamples] = useState<string[]>([]);
  const [launchingId, setLaunchingId] = useState<number | null>(null);

  const fetchCampaigns = async () => {
    setLoading(true);
    try {
      const data = await ApiClient.getCampaigns();
      setCampaigns(data);
    } catch (err) {
      console.error('Error fetching campaigns:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCampaigns();
  }, []);

  const updateSpintaxPreview = async (text: string) => {
    try {
      const res = await ApiClient.previewSpintax(text, 4);
      setPermutationsCount(res.permutations_count);
      setPreviewSamples(res.samples);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    updateSpintaxPreview(template);
  }, [template]);

  const insertTag = (tag: string) => {
    setTemplate((prev) => prev + ` {${tag}}`);
  };

  const handleCreateCampaign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !template) {
      toast.warning('Lütfen kampanya adı ve mesaj şablonunu eksiksiz doldurun.');
      return;
    }

    try {
      await ApiClient.createCampaign({
        name,
        description,
        message_template: template,
        min_delay_seconds: minDelay,
        max_delay_seconds: maxDelay,
        typing_delay_seconds: typingDelay,
        working_hours_enabled: workingHoursEnabled,
        working_hours_start: workingHoursStart,
        working_hours_end: workingHoursEnd,
      });

      toast.success('Yeni WhatsApp kampanyası başarıyla oluşturuldu.', 'Kampanya Kaydedildi');
      setActiveTab('list');
      setName('');
      setDescription('');
      fetchCampaigns();
      onRefreshStats();
    } catch (err: any) {
      toast.error(err.message, 'Kampanya Oluşturulamadı');
    }
  };

  const handleLaunchCampaign = async (campaignId: number) => {
    setLaunchingId(campaignId);
    try {
      await ApiClient.launchCampaign(campaignId, { limit: 50 });
      toast.success('Kampanya gönderim kuyruğuna alındı ve arka planda güvenle işleniyor!', '🚀 Kampanya Başlatıldı');
      fetchCampaigns();
      onRefreshStats();
    } catch (err: any) {
      toast.error(err.message, 'Kampanya Başlatılamadı');
    } finally {
      setLaunchingId(null);
    }
  };

  return (
    <div className="space-y-6 pb-16 select-none animate-fade-in">
      {/* Top Header & Mode Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-extrabold text-slate-800 dark:text-white flex items-center gap-2">
            <Send className="w-5 h-5 text-[#7367F0]" />
            Otomatik WhatsApp Kampanyaları & Spintax Studio
          </h2>
          <p className="text-xs text-slate-500 dark:text-[#7E7F96] mt-0.5 font-medium">
            Akıllı metin varyasyonları ve rastgele gecikmeli kuyruk yönetimi
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <Button
            variant={activeTab === 'list' ? 'outline' : 'ghost'}
            size="sm"
            onClick={() => setActiveTab('list')}
            className={activeTab === 'list' ? 'border-[#7367F0] text-[#7367F0] font-bold' : ''}
          >
            Kampanyalarım ({campaigns.length})
          </Button>
          <Button
            variant={activeTab === 'builder' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setActiveTab('builder')}
            className="space-x-1.5 font-bold shadow-md shadow-[#7367F0]/30"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Yeni Kampanya Oluştur</span>
          </Button>
        </div>
      </div>

      {activeTab === 'list' ? (
        /* Campaigns List View */
        <div className="space-y-4">
          {campaigns.length === 0 ? (
            <Card className="p-12 text-center space-y-3">
              <Send className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto" />
              <h3 className="text-base font-bold text-slate-800 dark:text-slate-200">Henüz Kampanya Oluşturulmadı</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto">
                Spintax destekli ilk kampanyanızı oluşturarak lead veri tabanınıza güvenle WhatsApp mesajı göndermeye başlayın.
              </p>
              <Button
                onClick={() => setActiveTab('builder')}
                className="mt-2 font-bold"
              >
                İlk Kampanyayı Oluştur
              </Button>
            </Card>
          ) : (
            <div className="grid grid-cols-1 gap-4">
              {campaigns.map((camp) => {
                const completionRate =
                  camp.total_leads_target > 0
                    ? Math.round((camp.sent_count / camp.total_leads_target) * 100)
                    : 0;
                return (
                  <Card key={camp.id} className="p-6 hover:shadow-md transition-shadow space-y-4">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                      <div>
                        <div className="flex items-center space-x-2.5">
                          <h3 className="text-base font-bold text-slate-800 dark:text-white">{camp.name}</h3>
                          <Badge
                            variant={
                              camp.status === 'ACTIVE'
                                ? 'success'
                                : camp.status === 'COMPLETED'
                                ? 'info'
                                : 'warning'
                            }
                          >
                            {camp.status}
                          </Badge>
                        </div>
                        {camp.description && (
                          <p className="text-xs text-slate-500 dark:text-[#7E7F96] mt-1 font-medium">{camp.description}</p>
                        )}
                      </div>

                      <div className="flex items-center space-x-3">
                        <Button
                          onClick={() => handleLaunchCampaign(camp.id)}
                          disabled={launchingId === camp.id}
                          className="space-x-2 font-bold shadow-md shadow-[#7367F0]/30"
                        >
                          {launchingId === camp.id ? (
                            <>
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              <span>Başlatılıyor...</span>
                            </>
                          ) : (
                            <>
                              <Play className="w-3.5 h-3.5 fill-current" />
                              <span>Kampanyayı Başlat</span>
                            </>
                          )}
                        </Button>
                      </div>
                    </div>

                    {/* Progress Bar & Counters */}
                    <div className="p-4 rounded-lg bg-slate-50 dark:bg-[#25293C] border border-slate-200/60 dark:border-white/[0.05] space-y-3">
                      <div className="flex justify-between text-xs font-bold">
                        <span className="text-slate-600 dark:text-slate-400">Gönderim İlerlemesi</span>
                        <span className="text-[#7367F0] font-mono">
                          {camp.sent_count} / {camp.total_leads_target || 25} Mesaj (%{completionRate})
                        </span>
                      </div>

                      <div className="h-2 w-full bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden p-0.5">
                        <div
                          className="h-full bg-gradient-to-r from-[#7367F0] to-[#00CFE8] rounded-full transition-all duration-300"
                          style={{ width: `${Math.min(completionRate, 100)}%` }}
                        />
                      </div>

                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-xs font-semibold">
                        <div className="text-slate-500 dark:text-[#7E7F96]">
                          İletildi: <strong className="text-slate-800 dark:text-white font-mono">{camp.delivered_count || camp.sent_count}</strong>
                        </div>
                        <div className="text-slate-500 dark:text-[#7E7F96]">
                          Yanıt: <strong className="text-[#28C76F] font-mono">{camp.replied_count}</strong>
                        </div>
                        <div className="text-slate-500 dark:text-[#7E7F96]">
                          Rastgele Gecikme: <strong className="text-slate-800 dark:text-white font-mono">{camp.min_delay_seconds}-{camp.max_delay_seconds}s</strong>
                        </div>
                        <div className="text-slate-500 dark:text-[#7E7F96]">
                          Mesai Kilidi: <strong className="text-slate-800 dark:text-white font-mono">{camp.working_hours_start}-{camp.working_hours_end}</strong>
                        </div>
                      </div>
                    </div>

                    {/* Template Snippet */}
                    <div className="text-xs font-mono bg-slate-100 dark:bg-[#1E2235] p-3 rounded-md border border-slate-200 dark:border-white/[0.05] text-slate-700 dark:text-slate-300 line-clamp-2">
                      {camp.message_template}
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      ) : (
        /* Spintax Studio & Campaign Builder View */
        <form onSubmit={handleCreateCampaign} className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Column: Form Controls & Template Editor */}
            <div className="lg:col-span-7 space-y-6">
              <Card className="p-6 space-y-4">
                <h3 className="text-base font-bold text-slate-800 dark:text-white flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-[#7367F0]" />
                  1. Kampanya Bilgileri & Şablon
                </h3>

                <div className="space-y-3 text-xs">
                  <div>
                    <label className="text-slate-700 dark:text-slate-300 font-bold block mb-1">Kampanya Adı *</label>
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Örn: İstanbul Kadıköy Diş Klinikleri Outreach"
                      className="w-full px-3 py-2.5 rounded-lg vuexy-input text-xs font-semibold"
                      required
                    />
                  </div>

                  <div>
                    <label className="text-slate-700 dark:text-slate-300 font-bold block mb-1">Açıklama</label>
                    <input
                      type="text"
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      placeholder="Kampanya hedefi ve notlar..."
                      className="w-full px-3 py-2.5 rounded-lg vuexy-input text-xs font-medium"
                    />
                  </div>

                  {/* Spintax Helper Chips */}
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <label className="text-slate-700 dark:text-slate-300 font-bold">
                        Spintax Mesaj Şablonu *
                      </label>
                      <Badge variant="primary" className="font-mono">
                        {permutationsCount} Farklı Varyasyon
                      </Badge>
                    </div>

                    <div className="flex flex-wrap gap-1.5 mb-2">
                      <span className="text-[10px] text-slate-400 self-center mr-1 font-semibold">Değişken Ekle:</span>
                      {['name', 'category', 'city', 'district', 'rating', 'website'].map((tag) => (
                        <button
                          key={tag}
                          type="button"
                          onClick={() => insertTag(tag)}
                          className="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-white/[0.05] hover:bg-[#7367F0]/15 text-slate-700 dark:text-slate-300 hover:text-[#7367F0] border border-slate-200 dark:border-white/[0.08] text-[10px] font-mono font-bold transition-all active:scale-95"
                        >
                          {`{${tag}}`}
                        </button>
                      ))}
                    </div>

                    <textarea
                      value={template}
                      onChange={(e) => setTemplate(e.target.value)}
                      rows={8}
                      className="w-full p-3 rounded-lg vuexy-input text-xs font-mono leading-relaxed"
                      placeholder="{Merhaba|Selam} {name} Yetkilisi..."
                      required
                    />
                    <p className="text-[11px] text-slate-500 dark:text-[#7E7F96] mt-1 font-medium">
                      💡 <strong>Spintax İpucu:</strong> Farklı alternatifler için <code className="text-[#7367F0] font-mono font-bold">`{'{Merhaba|Selam|İyi günler}'}`</code> formatını kullanın. Sistem her alıcıya farklı kombinasyon gönderecektir.
                    </p>
                  </div>
                </div>
              </Card>

              {/* Anti-Ban & Safeguards Config */}
              <Card className="p-6 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <h3 className="text-base font-bold text-slate-800 dark:text-white flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-[#28C76F]" />
                    2. Anti-Ban Güvenlik & Zamanlama Ayarları
                  </h3>

                  <div className="flex flex-wrap items-center gap-1.5">
                    <button
                      type="button"
                      onClick={() => {
                        const p = ANTI_BAN_PRESETS.ultra_safe;
                        setMinDelay(p.minDelaySeconds);
                        setMaxDelay(p.maxDelaySeconds);
                        setTypingDelay(p.typingDelaySeconds);
                        setWorkingHoursEnabled(p.workingHoursEnabled);
                        setWorkingHoursStart(p.workingHoursStart);
                        setWorkingHoursEnd(p.workingHoursEnd);
                      }}
                      className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-[#28C76F]/10 text-[#28C76F] border border-[#28C76F]/30 hover:bg-[#28C76F]/20"
                    >
                      🛡️ Ultra Güvenli
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        const p = ANTI_BAN_PRESETS.standard_balanced;
                        setMinDelay(p.minDelaySeconds);
                        setMaxDelay(p.maxDelaySeconds);
                        setTypingDelay(p.typingDelaySeconds);
                        setWorkingHoursEnabled(p.workingHoursEnabled);
                        setWorkingHoursStart(p.workingHoursStart);
                        setWorkingHoursEnd(p.workingHoursEnd);
                      }}
                      className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-[#7367F0]/10 text-[#7367F0] border border-[#7367F0]/30 hover:bg-[#7367F0]/20"
                    >
                      ⚡ Standart
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        const p = ANTI_BAN_PRESETS.fast_warmed;
                        setMinDelay(p.minDelaySeconds);
                        setMaxDelay(p.maxDelaySeconds);
                        setTypingDelay(p.typingDelaySeconds);
                        setWorkingHoursEnabled(p.workingHoursEnabled);
                        setWorkingHoursStart(p.workingHoursStart);
                        setWorkingHoursEnd(p.workingHoursEnd);
                      }}
                      className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-[#FF9F43]/10 text-[#FF9F43] border border-[#FF9F43]/30 hover:bg-[#FF9F43]/20"
                    >
                      🚀 Hızlı
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
                  <div>
                    <label className="text-slate-700 dark:text-slate-300 font-bold block mb-1">
                      Min. Gecikme (sn)
                    </label>
                    <input
                      type="number"
                      value={minDelay}
                      onChange={(e) => setMinDelay(Number(e.target.value))}
                      className="w-full px-3 py-2 rounded-lg vuexy-input text-xs font-mono font-bold"
                      min={10}
                      max={300}
                    />
                  </div>

                  <div>
                    <label className="text-slate-700 dark:text-slate-300 font-bold block mb-1">
                      Max. Gecikme (sn)
                    </label>
                    <input
                      type="number"
                      value={maxDelay}
                      onChange={(e) => setMaxDelay(Number(e.target.value))}
                      className="w-full px-3 py-2 rounded-lg vuexy-input text-xs font-mono font-bold"
                      min={minDelay}
                      max={600}
                    />
                  </div>

                  <div>
                    <label className="text-slate-700 dark:text-slate-300 font-bold block mb-1">
                      Yazıyor... Simülasyonu (sn)
                    </label>
                    <input
                      type="number"
                      value={typingDelay}
                      onChange={(e) => setTypingDelay(Number(e.target.value))}
                      className="w-full px-3 py-2 rounded-lg vuexy-input text-xs font-mono font-bold"
                      min={1}
                      max={15}
                    />
                  </div>
                </div>

                {/* Working Hours Guard */}
                <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#25293C] border border-slate-200/60 dark:border-white/[0.05] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                  <label className="flex items-center space-x-2 text-slate-700 dark:text-slate-200 font-bold cursor-pointer">
                    <input
                      type="checkbox"
                      checked={workingHoursEnabled}
                      onChange={(e) => setWorkingHoursEnabled(e.target.checked)}
                      className="rounded border-slate-300 dark:border-slate-700 text-[#7367F0]"
                    />
                    <span>Mesai Saatleri Koruması (Business Hours)</span>
                  </label>

                  <div className="flex items-center space-x-2">
                    <input
                      type="text"
                      value={workingHoursStart}
                      onChange={(e) => setWorkingHoursStart(e.target.value)}
                      className="w-16 px-2 py-1 rounded-md vuexy-input text-center font-mono text-xs font-bold"
                      placeholder="09:30"
                    />
                    <span className="text-slate-400 font-bold">-</span>
                    <input
                      type="text"
                      value={workingHoursEnd}
                      onChange={(e) => setWorkingHoursEnd(e.target.value)}
                      className="w-16 px-2 py-1 rounded-md vuexy-input text-center font-mono text-xs font-bold"
                      placeholder="18:30"
                    />
                  </div>
                </div>
              </Card>

              <div className="flex items-center justify-end space-x-3">
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => setActiveTab('list')}
                >
                  Vazgeç
                </Button>
                <Button
                  type="submit"
                  size="lg"
                  className="font-bold shadow-md shadow-[#7367F0]/30 space-x-2"
                >
                  <Send className="w-4 h-4" />
                  <span>Kampanyayı Kaydet</span>
                </Button>
              </div>
            </div>

            {/* Right Column: Live Permutation Previews */}
            <div className="lg:col-span-5 space-y-4">
              <Card className="p-6 space-y-4 sticky top-24">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-slate-800 dark:text-white flex items-center gap-2">
                    <Eye className="w-4 h-4 text-[#00CFE8]" />
                    Canlı Spintax Önizleme ({permutationsCount} Kombinasyon)
                  </h3>
                  <button
                    type="button"
                    onClick={() => updateSpintaxPreview(template)}
                    className="text-[11px] text-[#7367F0] hover:text-[#685DD8] flex items-center gap-1 font-bold active:scale-95"
                  >
                    <Shuffle className="w-3 h-3" />
                    Yeniden Üret
                  </button>
                </div>

                <p className="text-xs text-slate-500 dark:text-[#7E7F96] font-medium">
                  Farklı müşteri adaylarına gidecek örnek mesaj varyasyonları:
                </p>

                <div className="space-y-3">
                  {previewSamples.map((sample, idx) => (
                    <div
                      key={idx}
                      className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#25293C] border border-slate-200/60 dark:border-white/[0.06] text-xs text-slate-700 dark:text-slate-300 space-y-1.5 font-sans"
                    >
                      <div className="flex items-center justify-between text-[10px] text-slate-400">
                        <span className="font-mono font-bold text-[#7367F0]">
                          Varyasyon #{idx + 1}
                        </span>
                        <span className="font-medium">WhatsApp Formatı</span>
                      </div>
                      <p className="whitespace-pre-wrap leading-relaxed text-slate-800 dark:text-slate-200">{sample}</p>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          </div>
        </form>
      )}
    </div>
  );
};
