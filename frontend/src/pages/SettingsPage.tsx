import React, { useState } from 'react';
import { 
  Settings, 
  Server, 
  ShieldCheck, 
  Moon, 
  Sun, 
  Clock, 
  Sliders, 
  Check, 
  RotateCcw, 
  AlertTriangle,
  Zap,
  Shield,
  Smartphone
} from 'lucide-react';
import { Card } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { useTheme } from '../context/ThemeContext';
import { 
  AntiBanConfig, 
  DEFAULT_ANTI_BAN_CONFIG, 
  ANTI_BAN_PRESETS, 
  getStoredAntiBanConfig, 
  saveAntiBanConfig, 
  calculateRiskLevel 
} from '../utils/antiBanSettings';

export const SettingsPage: React.FC = () => {
  const { theme, toggleTheme } = useTheme();
  
  // Anti-Ban Timing State
  const [config, setConfig] = useState<AntiBanConfig>(getStoredAntiBanConfig());
  const [saveSuccess, setSaveSuccess] = useState(false);

  const handlePresetSelect = (presetKey: 'ultra_safe' | 'standard_balanced' | 'fast_warmed') => {
    const presetData = ANTI_BAN_PRESETS[presetKey];
    setConfig({
      preset: presetKey,
      ...presetData
    });
  };

  const handleCustomChange = (field: keyof AntiBanConfig, value: any) => {
    setConfig((prev) => ({
      ...prev,
      preset: 'custom',
      [field]: value
    }));
  };

  const handleSave = () => {
    saveAntiBanConfig(config);
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3500);
  };

  const handleResetDefaults = () => {
    setConfig(DEFAULT_ANTI_BAN_CONFIG);
    saveAntiBanConfig(DEFAULT_ANTI_BAN_CONFIG);
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3500);
  };

  const riskInfo = calculateRiskLevel(config.minDelaySeconds, config.dailyMessageLimit);

  return (
    <div className="space-y-6 pb-16 max-w-4xl select-none animate-fade-in">
      {/* Page Header */}
      <div>
        <h2 className="text-xl font-extrabold text-slate-800 dark:text-white flex items-center gap-2">
          <Settings className="w-5 h-5 text-[#7367F0]" />
          Ayarlar
        </h2>
        <p className="text-xs text-slate-500 dark:text-[#7E7F96] mt-0.5 font-medium">
          WhatsApp bekleme süreleri, anti-ban koruma parametreleri, tema ve servis entegrasyonları
        </p>
      </div>

      {/* Anti-Ban & Timing Configuration Card */}
      <Card className="p-4 sm:p-6 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 dark:border-white/[0.08] pb-4">
          <div className="flex items-center space-x-2.5">
            <div className="w-9 h-9 rounded-xl bg-[#28C76F]/15 text-[#28C76F] flex items-center justify-center font-bold">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-extrabold text-slate-800 dark:text-white flex items-center gap-2">
                WhatsApp Anti-Ban Yapılandırması
              </h3>
              <p className="text-[11px] text-slate-400 dark:text-[#7E7F96] font-medium">
                Mesajlar arası bekleme süreleri (Jitter), insan taklidi ve günlük limit ayarları
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={handleResetDefaults}
              className="text-xs font-bold text-slate-500 hover:text-[#7367F0] dark:text-[#7E7F96] dark:hover:text-white flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-white/[0.08] hover:bg-slate-50 dark:hover:bg-white/[0.04] transition-all"
              title="WhatsApp için ban yemeyen önerilen standart ayarlara dön"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Güvenli Varsayılanlara Dön</span>
            </button>
          </div>
        </div>

        {/* Preset Selector Tabs */}
        <div>
          <label className="text-xs font-bold text-slate-700 dark:text-slate-200 block mb-2">
            Güvenlik Ön Ayar Modu (Preset)
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
            {/* Preset 1: Ultra Safe */}
            <button
              type="button"
              onClick={() => handlePresetSelect('ultra_safe')}
              className={`p-3 rounded-xl border text-left transition-all ${
                config.preset === 'ultra_safe'
                  ? 'border-[#28C76F] bg-[#28C76F]/10 ring-1 ring-[#28C76F]/50 shadow-sm'
                  : 'border-slate-200 dark:border-white/[0.08] bg-slate-50/50 dark:bg-white/[0.02] hover:bg-slate-100 dark:hover:bg-white/[0.04]'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-extrabold text-slate-800 dark:text-white flex items-center gap-1.5">
                  <Shield className="w-3.5 h-3.5 text-[#28C76F]" />
                  Ultra Güvenli
                </span>
                <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-[#28C76F]/15 text-[#28C76F]">
                  Yeni Hatlar
                </span>
              </div>
              <p className="text-[11px] text-slate-500 dark:text-[#7E7F96]">
                60 - 150 sn bekleme, 35 mesaj/gün. Sıfır risk.
              </p>
            </button>

            {/* Preset 2: Standard Balanced (Default) */}
            <button
              type="button"
              onClick={() => handlePresetSelect('standard_balanced')}
              className={`p-3 rounded-xl border text-left transition-all ${
                config.preset === 'standard_balanced'
                  ? 'border-[#7367F0] bg-[#7367F0]/10 ring-1 ring-[#7367F0]/50 shadow-sm'
                  : 'border-slate-200 dark:border-white/[0.08] bg-slate-50/50 dark:bg-white/[0.02] hover:bg-slate-100 dark:hover:bg-white/[0.04]'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-extrabold text-slate-800 dark:text-white flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-[#7367F0]" />
                  Dengeli Standart
                </span>
                <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-[#7367F0]/15 text-[#7367F0]">
                  Varsayılan ⭐
                </span>
              </div>
              <p className="text-[11px] text-slate-500 dark:text-[#7E7F96]">
                45 - 120 sn bekleme, 50 mesaj/gün. Optimum.
              </p>
            </button>

            {/* Preset 3: Fast Warmed */}
            <button
              type="button"
              onClick={() => handlePresetSelect('fast_warmed')}
              className={`p-3 rounded-xl border text-left transition-all ${
                config.preset === 'fast_warmed'
                  ? 'border-[#FF9F43] bg-[#FF9F43]/10 ring-1 ring-[#FF9F43]/50 shadow-sm'
                  : 'border-slate-200 dark:border-white/[0.08] bg-slate-50/50 dark:bg-white/[0.02] hover:bg-slate-100 dark:hover:bg-white/[0.04]'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-extrabold text-slate-800 dark:text-white flex items-center gap-1.5">
                  <Zap className="w-3.5 h-3.5 text-[#FF9F43]" />
                  Hızlı Gönderim
                </span>
                <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-[#FF9F43]/15 text-[#FF9F43]">
                  Isınmış Hatlar
                </span>
              </div>
              <p className="text-[11px] text-slate-500 dark:text-[#7E7F96]">
                20 - 60 sn bekleme, 100 mesaj/gün. Eski hesaplar.
              </p>
            </button>
          </div>
        </div>

        {/* Granular Timing Parameters Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3.5 pt-2">
          {/* Min Delay */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 dark:text-slate-200 flex items-center justify-between">
              <span>Min. Gecikme</span>
              <span className="text-[10px] text-slate-400 font-mono">Saniye</span>
            </label>
            <div className="relative">
              <input
                type="number"
                value={config.minDelaySeconds}
                onChange={(e) => handleCustomChange('minDelaySeconds', Math.max(5, Number(e.target.value)))}
                className="w-full px-3 py-2 rounded-lg vuexy-input text-xs font-mono font-bold"
                min={5}
                max={300}
              />
            </div>
            <span className="text-[10px] text-slate-400 block">En az bekleme (Örn: 45s)</span>
          </div>

          {/* Max Delay */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 dark:text-slate-200 flex items-center justify-between">
              <span>Max. Gecikme</span>
              <span className="text-[10px] text-slate-400 font-mono">Saniye</span>
            </label>
            <div className="relative">
              <input
                type="number"
                value={config.maxDelaySeconds}
                onChange={(e) => handleCustomChange('maxDelaySeconds', Math.max(config.minDelaySeconds, Number(e.target.value)))}
                className="w-full px-3 py-2 rounded-lg vuexy-input text-xs font-mono font-bold"
                min={config.minDelaySeconds}
                max={600}
              />
            </div>
            <span className="text-[10px] text-slate-400 block">En çok bekleme (Örn: 120s)</span>
          </div>

          {/* Typing Simulation Delay */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 dark:text-slate-200 flex items-center justify-between">
              <span>Yazıyor... Simülasyonu</span>
              <span className="text-[10px] text-slate-400 font-mono">Saniye</span>
            </label>
            <div className="relative">
              <input
                type="number"
                value={config.typingDelaySeconds}
                onChange={(e) => handleCustomChange('typingDelaySeconds', Math.max(1, Number(e.target.value)))}
                className="w-full px-3 py-2 rounded-lg vuexy-input text-xs font-mono font-bold"
                min={1}
                max={15}
              />
            </div>
            <span className="text-[10px] text-slate-400 block">İnsan yazım taklidi</span>
          </div>

          {/* Daily Limit Per Session */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 dark:text-slate-200 flex items-center justify-between">
              <span>Günlük Mesaj Limiti</span>
              <span className="text-[10px] text-slate-400 font-mono">Msg/Hat</span>
            </label>
            <div className="relative">
              <input
                type="number"
                value={config.dailyMessageLimit}
                onChange={(e) => handleCustomChange('dailyMessageLimit', Math.max(10, Number(e.target.value)))}
                className="w-full px-3 py-2 rounded-lg vuexy-input text-xs font-mono font-bold"
                min={10}
                max={300}
              />
            </div>
            <span className="text-[10px] text-slate-400 block">Güvenli kota tavanı</span>
          </div>
        </div>

        {/* Working Hours Guard Row */}
        <div className="p-4 rounded-xl bg-slate-50 dark:bg-[#25293C] border border-slate-200/60 dark:border-white/[0.05] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
          <label className="flex items-center space-x-2.5 text-slate-700 dark:text-slate-200 font-bold cursor-pointer">
            <input
              type="checkbox"
              checked={config.workingHoursEnabled}
              onChange={(e) => handleCustomChange('workingHoursEnabled', e.target.checked)}
              className="w-4 h-4 rounded border-slate-300 dark:border-slate-700 text-[#7367F0] focus:ring-[#7367F0]"
            />
            <div className="flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-[#7367F0]" />
              <span>Mesai Saatleri Dışı Otomatik Durdurma Kalkanı</span>
            </div>
          </label>

          <div className="flex items-center space-x-2 self-start sm:self-auto pl-6 sm:pl-0">
            <span className="text-slate-400 font-medium">Aralık:</span>
            <input
              type="text"
              value={config.workingHoursStart}
              onChange={(e) => handleCustomChange('workingHoursStart', e.target.value)}
              className="w-16 px-2 py-1 rounded-lg vuexy-input text-center font-mono text-xs font-bold"
              placeholder="09:00"
            />
            <span className="text-slate-400 font-bold">-</span>
            <input
              type="text"
              value={config.workingHoursEnd}
              onChange={(e) => handleCustomChange('workingHoursEnd', e.target.value)}
              className="w-16 px-2 py-1 rounded-lg vuexy-input text-center font-mono text-xs font-bold"
              placeholder="19:00"
            />
          </div>
        </div>

        {/* Realtime Anti-Ban Risk Analysis Meter */}
        <div 
          className="p-4 rounded-xl border flex items-start space-x-3 transition-colors"
          style={{ 
            backgroundColor: `${riskInfo.color}10`,
            borderColor: `${riskInfo.color}40`
          }}
        >
          <div className="shrink-0 mt-0.5" style={{ color: riskInfo.color }}>
            {riskInfo.level === 'high' ? (
              <AlertTriangle className="w-5 h-5" />
            ) : riskInfo.level === 'moderate' ? (
              <Zap className="w-5 h-5" />
            ) : (
              <ShieldCheck className="w-5 h-5" />
            )}
          </div>
          <div className="flex-1 text-xs">
            <h4 className="font-extrabold mb-0.5" style={{ color: riskInfo.color }}>
              {riskInfo.title}
            </h4>
            <p className="text-slate-600 dark:text-slate-300 leading-relaxed font-medium">
              {riskInfo.desc}
            </p>
          </div>
        </div>

        {/* Save Actions */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-2">
          <div>
            {saveSuccess && (
              <span className="inline-flex items-center gap-1.5 text-xs font-bold text-[#28C76F] bg-[#28C76F]/15 px-3 py-1.5 rounded-lg border border-[#28C76F]/30 animate-fade-in">
                <Check className="w-3.5 h-3.5" />
                <span>Anti-Ban ayarları başarıyla güncellendi ve sisteme uygulandı!</span>
              </span>
            )}
          </div>

          <Button
            onClick={handleSave}
            className="space-x-2 font-bold shadow-md shadow-[#7367F0]/30 w-full sm:w-auto justify-center"
          >
            <Check className="w-4 h-4" />
            <span>Ayarları Kaydet</span>
          </Button>
        </div>
      </Card>

      {/* Theme Setting Card */}
      <Card className="p-4 sm:p-6 space-y-4">
        <h3 className="text-sm font-bold text-slate-800 dark:text-white flex items-center gap-2">
          {theme === 'light' ? <Sun className="w-4 h-4 text-[#FF9F43]" /> : <Moon className="w-4 h-4 text-[#7367F0]" />}
          Tema
        </h3>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 rounded-lg bg-slate-50 dark:bg-[#25293C] border border-slate-200/60 dark:border-white/[0.05] gap-3">
          <div>
            <p className="text-xs font-bold text-slate-800 dark:text-slate-200">
              Mevcut Tema: <span className="text-[#7367F0] font-extrabold">{theme === 'light' ? 'Aydınlık (Light Mode - Vuexy Standard)' : 'Koyu (Dark Mode - Vuexy Slate)'}</span>
            </p>
            <p className="text-[11px] text-slate-400 dark:text-[#7E7F96]">
              Aydınlık ve koyu tema arasında dilediğiniz an geçiş yapabilirsiniz. Tercihiniz tarayıcınızda saklanır.
            </p>
          </div>

          <button
            onClick={toggleTheme}
            className="px-4 py-2 rounded-lg bg-[#7367F0] hover:bg-[#685DD8] text-white font-bold text-xs shadow-md shadow-[#7367F0]/30 transition-all active:scale-95 flex items-center justify-center gap-2 shrink-0"
          >
            {theme === 'light' ? (
              <>
                <Moon className="w-4 h-4" />
                <span>Koyu Moda Geç</span>
              </>
            ) : (
              <>
                <Sun className="w-4 h-4" />
                <span>Aydınlık Moda Geç</span>
              </>
            )}
          </button>
        </div>
      </Card>

      {/* Services Connections Card */}
      <Card className="p-4 sm:p-6 space-y-4 sm:space-y-6">
        <h3 className="text-sm font-bold text-slate-800 dark:text-white flex items-center gap-2">
          <Server className="w-4 h-4 text-[#7367F0]" />
          Servis Bağlantıları
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div className="p-4 rounded-lg bg-slate-50 dark:bg-[#25293C] border border-slate-200/60 dark:border-white/[0.05] space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-slate-700 dark:text-slate-200">FastAPI REST & WS Core</span>
              <Badge variant="success">Aktif</Badge>
            </div>
            <p className="font-mono text-[#7367F0] text-[11px] font-bold">http://localhost:8000/api/v1</p>
            <p className="text-slate-400 dark:text-[#7E7F96] text-[10px]">Pydantic v2 & SQLAlchemy 2.0 Async Session</p>
          </div>

          <div className="p-4 rounded-lg bg-slate-50 dark:bg-[#25293C] border border-slate-200/60 dark:border-white/[0.05] space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-slate-700 dark:text-slate-200">WhatsApp Gateway Sidecar</span>
              <Badge variant="success">Aktif</Badge>
            </div>
            <p className="font-mono text-[#00CFE8] text-[11px] font-bold">http://localhost:3001</p>
            <p className="text-slate-400 dark:text-[#7E7F96] text-[10px]">Baileys WebSocket Socket Engine</p>
          </div>
        </div>
      </Card>
    </div>
  );
};
