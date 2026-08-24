import React, { useState, useEffect } from 'react';
import { 
  Smartphone, 
  QrCode, 
  ShieldCheck, 
  BatteryCharging, 
  Send, 
  Flame, 
  CheckCircle2, 
  Trash2, 
  PowerOff, 
  Loader2, 
  X, 
  Zap,
  Clock,
  Sliders,
  Check,
  RotateCcw,
  AlertTriangle,
  Shield,
  Building2,
  Sparkles
} from 'lucide-react';
import { ApiClient } from '../api/client';
import { WhatsAppSession, MessageLog } from '../types';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Card } from '../components/ui/card';
import { 
  AntiBanConfig, 
  DEFAULT_ANTI_BAN_CONFIG, 
  ANTI_BAN_PRESETS, 
  getStoredAntiBanConfig, 
  saveAntiBanConfig, 
  calculateRiskLevel 
} from '../utils/antiBanSettings';

interface WhatsAppHubPageProps {
  onRefreshStats: () => void;
}

export const WhatsAppHubPage: React.FC<WhatsAppHubPageProps> = ({ onRefreshStats }) => {
  const [sessions, setSessions] = useState<WhatsAppSession[]>([]);
  const [logs, setLogs] = useState<MessageLog[]>([]);
  const [loading, setLoading] = useState(false);

  // Anti-Ban Timing State
  const [config, setConfig] = useState<AntiBanConfig>(getStoredAntiBanConfig());
  const [saveSuccess, setSaveSuccess] = useState(false);

  // New Line / QR Pairing Modal
  const [isQRModalOpen, setIsQRModalOpen] = useState(false);
  const [newSessionName, setNewSessionName] = useState('Satış Hattı 2');
  const [pairingSessionId, setPairingSessionId] = useState<number | null>(null);
  const [isPairingSuccess, setIsPairingSuccess] = useState(false);

  // Test Sandbox State
  const [testPhone, setTestPhone] = useState('0532 100 20 30');
  const [testMsg, setTestMsg] = useState('Scoutify WhatsApp Gateway bağlantı test mesajıdır.');
  const [selectedSessionForTest, setSelectedSessionForTest] = useState<number | undefined>(undefined);
  const [testSending, setTestSending] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);

  const fetchSessionsAndLogs = async () => {
    setLoading(true);
    try {
      const [sessData, logsData] = await Promise.all([
        ApiClient.getWhatsAppSessions(),
        ApiClient.getMessageLogs()
      ]);
      setSessions(sessData);
      setLogs(logsData);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSessionsAndLogs();
  }, []);

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

  const handleSaveAntiBan = () => {
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

  const handleCreateSession = async () => {
    if (!newSessionName) return;
    try {
      const session = await ApiClient.createWhatsAppSession(newSessionName);
      setPairingSessionId(session.id);
      setIsQRModalOpen(true);
      setIsPairingSuccess(false);
      fetchSessionsAndLogs();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleSimulateScan = async () => {
    if (!pairingSessionId) return;
    try {
      await ApiClient.simulateConnectSession(pairingSessionId);
      setIsPairingSuccess(true);
      setTimeout(() => {
        setIsQRModalOpen(false);
        fetchSessionsAndLogs();
        onRefreshStats();
      }, 1500);
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleDisconnect = async (sessionId: number) => {
    try {
      await ApiClient.disconnectSession(sessionId);
      fetchSessionsAndLogs();
      onRefreshStats();
    } catch (err) {
      alert('Bağlantı kesilemedi');
    }
  };

  const handleDelete = async (sessionId: number) => {
    if (!confirm('Bu WhatsApp oturumunu silmek istediğinize emin misiniz?')) return;
    try {
      await ApiClient.deleteSession(sessionId);
      fetchSessionsAndLogs();
      onRefreshStats();
    } catch (err) {
      alert('Oturum silinemedi');
    }
  };

  const handleSendTest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!testPhone || !testMsg) return;
    setTestSending(true);
    setTestResult(null);

    try {
      const res = await ApiClient.sendTestMessage(testPhone, testMsg, selectedSessionForTest);
      setTestResult(res.message);
      fetchSessionsAndLogs();
      onRefreshStats();
    } catch (err: any) {
      setTestResult(`Hata: ${err.message}`);
    } finally {
      setTestSending(false);
    }
  };

  return (
    <div className="space-y-6 pb-16 select-none animate-fade-in">
      {/* Top Header & New Account Action */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-extrabold text-slate-800 dark:text-white flex items-center gap-2">
            <Smartphone className="w-5 h-5 text-[#28C76F]" />
            WhatsApp Oturumları & Anti-Ban Hub
          </h2>
          <p className="text-xs text-slate-500 dark:text-[#7E7F96] mt-0.5 font-medium">
            Çoklu hat yönetimi, QR eşleme, Gaussian Jitter bekleme süreleri ve anti-ban koruma parametreleri
          </p>
        </div>

        <Button
          onClick={handleCreateSession}
          size="sm"
          className="space-x-2 font-bold shadow-md shadow-[#7367F0]/30 cursor-pointer"
        >
          <QrCode className="w-4 h-4" />
          <span>Yeni WhatsApp Hattı Bağla (QR)</span>
        </Button>
      </div>

      {/* Connected Sessions Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {sessions.map((sess) => {
          const quotaPercent = Math.round((sess.daily_sent_count / sess.max_daily_limit) * 100);
          return (
            <Card key={sess.id} className="p-5 hover:shadow-md transition-shadow flex flex-col justify-between h-full space-y-4">
              <div>
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 rounded-xl bg-[#28C76F]/15 text-[#28C76F] flex items-center justify-center font-bold">
                      <Smartphone className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-slate-800 dark:text-white">{sess.session_name}</h3>
                      <p className="text-xs font-mono text-[#28C76F] font-bold">
                        {sess.phone_number || 'Numara Bekleniyor'}
                      </p>
                    </div>
                  </div>

                  <Badge
                    variant={
                      sess.status === 'CONNECTED'
                        ? 'success'
                        : sess.status === 'SCAN_QR'
                        ? 'warning'
                        : 'danger'
                    }
                    className="gap-1 font-bold text-[10px]"
                  >
                    {sess.status === 'CONNECTED' && (
                      <span className="w-1.5 h-1.5 rounded-full bg-[#28C76F] live-dot" />
                    )}
                    {sess.status}
                  </Badge>
                </div>

                {/* Warm-Up Day & Quota Status */}
                <div className="mt-4 space-y-2.5 p-3 rounded-lg bg-slate-50 dark:bg-[#25293C] border border-slate-200/60 dark:border-white/[0.05]">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500 dark:text-[#7E7F96] flex items-center gap-1 font-semibold">
                      <Flame className="w-3.5 h-3.5 text-[#FF9F43]" />
                      Hesap Isınma (Warm-Up):
                    </span>
                    <span className="font-bold text-[#FF9F43] font-mono">Gün #{sess.warm_up_day}</span>
                  </div>

                  <div>
                    <div className="flex justify-between text-[11px] font-bold text-slate-700 dark:text-slate-300 mb-1">
                      <span>Günlük Gönderim Kotası</span>
                      <span className="font-mono text-[#7367F0]">
                        {sess.daily_sent_count} / {sess.max_daily_limit} Mesaj
                      </span>
                    </div>
                    <div className="h-1.5 w-full bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden p-0.5">
                      <div
                        className="h-full bg-gradient-to-r from-[#7367F0] to-[#28C76F] rounded-full transition-all duration-300"
                        style={{ width: `${Math.min(quotaPercent, 100)}%` }}
                      />
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1 font-semibold">
                    <span className="flex items-center gap-1">
                      <BatteryCharging className="w-3 h-3 text-[#28C76F]" />
                      Pil: %{sess.battery_level || 90}
                    </span>
                    <span>Durum: Güvenli & Sağlıklı</span>
                  </div>
                </div>
              </div>

              {/* Card Actions */}
              <div className="pt-2 flex items-center justify-between border-t border-slate-100 dark:border-white/[0.06] text-xs">
                {sess.status === 'CONNECTED' ? (
                  <button
                    onClick={() => handleDisconnect(sess.id)}
                    className="text-slate-500 hover:text-[#FF9F43] flex items-center gap-1 font-bold transition-colors text-xs cursor-pointer"
                  >
                    <PowerOff className="w-3.5 h-3.5" />
                    <span>Bağlantıyı Kes</span>
                  </button>
                ) : (
                  <button
                    onClick={() => {
                      setPairingSessionId(sess.id);
                      setIsQRModalOpen(true);
                    }}
                    className="text-[#7367F0] hover:text-[#685DD8] flex items-center gap-1 font-bold text-xs cursor-pointer"
                  >
                    <QrCode className="w-3.5 h-3.5" />
                    <span>QR Kodu Tara</span>
                  </button>
                )}

                <button
                  onClick={() => handleDelete(sess.id)}
                  className="text-slate-400 hover:text-[#EA5455] p-1 transition-colors cursor-pointer"
                  title="Oturumu Sil"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </Card>
          );
        })}
      </div>

      {/* ========================================================================= */}
      {/* WHATSAPP ANTI-BAN YAPILANDIRMASI SUITE */}
      {/* ========================================================================= */}
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
                Mesajlar arası bekleme süreleri (Jitter), insan taklidi ve kurumsal mesai saatleri koruması
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={handleResetDefaults}
              className="text-xs font-bold text-slate-500 hover:text-[#7367F0] dark:text-[#7E7F96] dark:hover:text-white flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-white/[0.08] hover:bg-slate-50 dark:hover:bg-white/[0.04] transition-all cursor-pointer"
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
              className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
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
              className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
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
                45 - 120 sn bekleme, 50 mesaj/gün. Önerilen altın denge.
              </p>
            </button>

            {/* Preset 3: Fast Warmed */}
            <button
              type="button"
              onClick={() => handlePresetSelect('fast_warmed')}
              className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
                config.preset === 'fast_warmed'
                  ? 'border-[#FF9F43] bg-[#FF9F43]/10 ring-1 ring-[#FF9F43]/50 shadow-sm'
                  : 'border-slate-200 dark:border-white/[0.08] bg-slate-50/50 dark:bg-white/[0.02] hover:bg-slate-100 dark:hover:bg-white/[0.04]'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-extrabold text-slate-800 dark:text-white flex items-center gap-1.5">
                  <Zap className="w-3.5 h-3.5 text-[#FF9F43]" />
                  Hızlı & Isınmış
                </span>
                <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-[#FF9F43]/15 text-[#FF9F43]">
                  Eski Hatlar
                </span>
              </div>
              <p className="text-[11px] text-slate-500 dark:text-[#7E7F96]">
                20 - 60 sn bekleme, 100 mesaj/gün. Isınmış numaralar.
              </p>
            </button>
          </div>
        </div>

        {/* ===================================================================== */}
        {/* DETAILED SLIDER CONTROLS - UNIFIED HARMONIOUS BACKGROUNDS */}
        {/* ===================================================================== */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
          {/* Slider 1: Min Delay */}
          <div className="p-4 rounded-xl bg-slate-50 dark:bg-[#25293C] border border-slate-200/60 dark:border-white/[0.05] space-y-2.5 shadow-sm hover:border-[#7367F0]/30 transition-all">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-slate-700 dark:text-slate-200 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-[#7367F0]" />
                Minimum Bekleme Süresi
              </label>
              <span className="text-xs font-extrabold font-mono text-[#7367F0] bg-[#7367F0]/10 px-2.5 py-0.5 rounded-lg border border-[#7367F0]/20">
                {config.minDelaySeconds} saniye
              </span>
            </div>
            <input
              type="range"
              min={10}
              max={120}
              step={5}
              value={config.minDelaySeconds}
              onChange={(e) => {
                const val = Number(e.target.value);
                handleCustomChange('minDelaySeconds', val);
                if (val >= config.maxDelaySeconds) {
                  handleCustomChange('maxDelaySeconds', val + 15);
                }
              }}
              className="w-full accent-[#7367F0] cursor-pointer"
            />
            <p className="text-[11px] text-slate-400 dark:text-[#7E7F96]">
              İki mesaj arasında beklenecek en az süre (WhatsApp bot tespitini engeller).
            </p>
          </div>

          {/* Slider 2: Max Delay */}
          <div className="p-4 rounded-xl bg-slate-50 dark:bg-[#25293C] border border-slate-200/60 dark:border-white/[0.05] space-y-2.5 shadow-sm hover:border-[#7367F0]/30 transition-all">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-slate-700 dark:text-slate-200 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-[#7367F0]" />
                Maksimum Bekleme Süresi
              </label>
              <span className="text-xs font-extrabold font-mono text-[#7367F0] bg-[#7367F0]/10 px-2.5 py-0.5 rounded-lg border border-[#7367F0]/20">
                {config.maxDelaySeconds} saniye
              </span>
            </div>
            <input
              type="range"
              min={config.minDelaySeconds + 5}
              max={240}
              step={5}
              value={config.maxDelaySeconds}
              onChange={(e) => handleCustomChange('maxDelaySeconds', Number(e.target.value))}
              className="w-full accent-[#7367F0] cursor-pointer"
            />
            <p className="text-[11px] text-slate-400 dark:text-[#7E7F96]">
              İki mesaj arasında beklenecek en fazla süre (Gaussian Jitter rastgele aralığı).
            </p>
          </div>

          {/* Slider 3: Typing Simulation */}
          <div className="p-4 rounded-xl bg-slate-50 dark:bg-[#25293C] border border-slate-200/60 dark:border-white/[0.05] space-y-2.5 shadow-sm hover:border-[#7367F0]/30 transition-all">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-slate-700 dark:text-slate-200 flex items-center gap-1.5">
                <Sliders className="w-3.5 h-3.5 text-[#7367F0]" />
                "Yazıyor..." İnsan Taklidi Süresi
              </label>
              <span className="text-xs font-extrabold font-mono text-[#7367F0] bg-[#7367F0]/10 px-2.5 py-0.5 rounded-lg border border-[#7367F0]/20">
                {config.typingDelaySeconds} saniye
              </span>
            </div>
            <input
              type="range"
              min={1}
              max={15}
              step={1}
              value={config.typingDelaySeconds}
              onChange={(e) => handleCustomChange('typingDelaySeconds', Number(e.target.value))}
              className="w-full accent-[#7367F0] cursor-pointer"
            />
            <p className="text-[11px] text-slate-400 dark:text-[#7E7F96]">
              Mesaj gönderilmeden önce WhatsApp soketinde aktif insan gibi yazıyor gösterilir.
            </p>
          </div>

          {/* Slider 4: Daily Limit */}
          <div className="p-4 rounded-xl bg-slate-50 dark:bg-[#25293C] border border-slate-200/60 dark:border-white/[0.05] space-y-2.5 shadow-sm hover:border-[#7367F0]/30 transition-all">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-slate-700 dark:text-slate-200 flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 text-[#7367F0]" />
                Hat Başına Günlük Mesaj Limiti
              </label>
              <span className="text-xs font-extrabold font-mono text-[#7367F0] bg-[#7367F0]/10 px-2.5 py-0.5 rounded-lg border border-[#7367F0]/20">
                {config.dailyMessageLimit} mesaj / gün
              </span>
            </div>
            <input
              type="range"
              min={10}
              max={250}
              step={5}
              value={config.dailyMessageLimit}
              onChange={(e) => handleCustomChange('dailyMessageLimit', Number(e.target.value))}
              className="w-full accent-[#7367F0] cursor-pointer"
            />
            <p className="text-[11px] text-slate-400 dark:text-[#7E7F96]">
              Günlük limit dolduğunda kampanya güvenli şekilde bir sonraki güne ertelenir.
            </p>
          </div>
        </div>

        {/* ===================================================================== */}
        {/* WORKING HOURS PROTECTION & SMOOTH DYNAMIC RISK GAUGE */}
        {/* ===================================================================== */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
          {/* Working Hours Box with Corporate Presets */}
          <div className="p-4 rounded-xl bg-slate-50 dark:bg-[#25293C] border border-slate-200/60 dark:border-white/[0.05] space-y-3 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Building2 className="w-4 h-4 text-[#7367F0]" />
                <div>
                  <span className="text-xs font-extrabold text-slate-800 dark:text-white block">
                    Güvenli Çalışma Saatleri Koruması
                  </span>
                  <span className="text-[10px] text-slate-400">Kurumsal mesai saatleri otomatik aktif</span>
                </div>
              </div>

              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.workingHoursEnabled !== false}
                  onChange={(e) => handleCustomChange('workingHoursEnabled', e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-9 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-[#7367F0]"></div>
              </label>
            </div>

            {config.workingHoursEnabled !== false && (
              <div className="space-y-2.5 pt-1 animate-fade-in">
                {/* Quick Corporate Time Presets */}
                <div className="flex items-center gap-1.5 flex-wrap">
                  <button
                    type="button"
                    onClick={() => {
                      handleCustomChange('workingHoursStart', '09:00');
                      handleCustomChange('workingHoursEnd', '18:00');
                    }}
                    className={`px-2 py-1 rounded-lg text-[10px] font-bold border transition-all cursor-pointer ${
                      config.workingHoursStart === '09:00' && config.workingHoursEnd === '18:00'
                        ? 'bg-[#7367F0]/15 text-[#7367F0] border-[#7367F0]/40'
                        : 'bg-white dark:bg-white/[0.04] text-slate-500 border-slate-200 dark:border-white/[0.08] hover:bg-slate-100'
                    }`}
                  >
                    🏢 Standart (09:00 - 18:00)
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      handleCustomChange('workingHoursStart', '09:00');
                      handleCustomChange('workingHoursEnd', '18:30');
                    }}
                    className={`px-2 py-1 rounded-lg text-[10px] font-bold border transition-all cursor-pointer ${
                      config.workingHoursStart === '09:00' && config.workingHoursEnd === '18:30'
                        ? 'bg-[#7367F0]/15 text-[#7367F0] border-[#7367F0]/40'
                        : 'bg-white dark:bg-white/[0.04] text-slate-500 border-slate-200 dark:border-white/[0.08] hover:bg-slate-100'
                    }`}
                  >
                    💼 Kurumsal Ortalama (09:00 - 18:30)
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      handleCustomChange('workingHoursStart', '09:00');
                      handleCustomChange('workingHoursEnd', '20:00');
                    }}
                    className={`px-2 py-1 rounded-lg text-[10px] font-bold border transition-all cursor-pointer ${
                      config.workingHoursStart === '09:00' && config.workingHoursEnd === '20:00'
                        ? 'bg-[#7367F0]/15 text-[#7367F0] border-[#7367F0]/40'
                        : 'bg-white dark:bg-white/[0.04] text-slate-500 border-slate-200 dark:border-white/[0.08] hover:bg-slate-100'
                    }`}
                  >
                    🌙 Esnek (09:00 - 20:00)
                  </button>
                </div>

                {/* Custom Time Inputs */}
                <div className="grid grid-cols-2 gap-2 text-xs pt-1">
                  <div>
                    <label className="text-[10px] font-bold text-slate-500 dark:text-[#7E7F96] block mb-1">
                      Başlangıç Saati
                    </label>
                    <input
                      type="time"
                      value={config.workingHoursStart || '09:00'}
                      onChange={(e) => handleCustomChange('workingHoursStart', e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded-lg vuexy-input text-xs font-mono font-bold"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-slate-500 dark:text-[#7E7F96] block mb-1">
                      Bitiş Saati
                    </label>
                    <input
                      type="time"
                      value={config.workingHoursEnd || '18:30'}
                      onChange={(e) => handleCustomChange('workingHoursEnd', e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded-lg vuexy-input text-xs font-mono font-bold"
                    />
                  </div>
                </div>
              </div>
            )}
            <p className="text-[10px] text-slate-400">
              Mesai saatleri dışında (gece/hafta sonu) spam şikayetlerini ve ban riskini sıfırlar.
            </p>
          </div>

          {/* =================================================================== */}
          {/* SMOOTH ANIMATED RISK METER SLIDER / GAUGE */}
          {/* =================================================================== */}
          <div className="p-4 rounded-xl bg-slate-50 dark:bg-[#25293C] border border-slate-200/60 dark:border-white/[0.05] flex flex-col justify-between space-y-3 shadow-sm">
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-bold text-slate-700 dark:text-slate-200 flex items-center gap-1.5">
                  <AlertTriangle className={`w-4 h-4 ${riskInfo.color}`} />
                  Anlık Ban Riski Seviyesi
                </span>
                <span className={`text-[11px] font-extrabold px-2.5 py-0.5 rounded-lg border font-mono uppercase transition-all duration-300 ${riskInfo.badgeBg} ${riskInfo.badgeText}`}>
                  {riskInfo.title} (%{riskInfo.score})
                </span>
              </div>
              <p className="text-[11px] text-slate-500 dark:text-[#7E7F96] leading-relaxed">
                {riskInfo.desc}
              </p>
            </div>

            {/* Smooth Risk Slider Track & Needle */}
            <div className="space-y-1.5 pt-1">
              <div className="relative w-full h-3 rounded-full bg-slate-200 dark:bg-slate-700 overflow-visible p-0.5">
                {/* Smooth Gradient Bar */}
                <div 
                  className="w-full h-full rounded-full bg-gradient-to-r from-[#28C76F] via-[#FF9F43] to-[#EA5455] opacity-90"
                />
                {/* Smooth Moving Thumb / Needle Indicator */}
                <div 
                  className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-4 h-4 bg-white dark:bg-slate-900 border-2 rounded-full shadow-md transition-all duration-500 ease-out z-10 flex items-center justify-center"
                  style={{ 
                    left: `${Math.max(4, Math.min(96, riskInfo.score))}%`,
                    borderColor: riskInfo.color 
                  }}
                >
                  <div 
                    className="w-1.5 h-1.5 rounded-full"
                    style={{ backgroundColor: riskInfo.color }}
                  />
                </div>
              </div>

              {/* Risk Range Scale Labels */}
              <div className="flex items-center justify-between text-[9px] font-bold text-slate-400 font-mono px-0.5">
                <span className="text-[#28C76F]">0% Güvenli</span>
                <span className="text-[#FF9F43]">50% Dengeli</span>
                <span className="text-[#EA5455]">100% Yüksek</span>
              </div>
            </div>
          </div>
        </div>

        {/* Save Actions */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-2">
          <div>
            {saveSuccess && (
              <span className="inline-flex items-center gap-1.5 text-xs font-bold text-[#28C76F] bg-[#28C76F]/15 px-3 py-1.5 rounded-lg border border-[#28C76F]/30 animate-fade-in">
                <Check className="w-3.5 h-3.5" />
                <span>Anti-Ban ayarları başarıyla kaydedildi ve uygulandı!</span>
              </span>
            )}
          </div>

          <Button
            onClick={handleSaveAntiBan}
            className="space-x-2 font-bold shadow-md shadow-[#7367F0]/30 w-full sm:w-auto justify-center cursor-pointer"
          >
            <Check className="w-4 h-4" />
            <span>Ayarları Kaydet</span>
          </Button>
        </div>
      </Card>

      {/* Two-Column: Test Sandbox & Anti-Ban Protocols */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Direct Test Sandbox */}
        <div className="lg:col-span-6">
          <Card className="p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-800 dark:text-white flex items-center gap-2">
                <Zap className="w-4 h-4 text-[#FF9F43]" />
                Doğrudan Test Mesajı Gönderimi
              </h3>
              <Badge variant="warning" className="font-mono text-[9px]">SANDBOX</Badge>
            </div>
            <p className="text-xs text-slate-500 dark:text-[#7E7F96] font-medium">
              Bağlı hattınızın sağlığını ve mesaj iletimini anlık olarak test edin.
            </p>

            <form onSubmit={handleSendTest} className="space-y-3 text-xs">
              <div>
                <label className="text-slate-700 dark:text-slate-300 font-bold block mb-1">
                  Alıcı Telefon Numarası *
                </label>
                <input
                  type="text"
                  value={testPhone}
                  onChange={(e) => setTestPhone(e.target.value)}
                  placeholder="0532 123 45 67"
                  className="w-full px-3 py-2 rounded-lg vuexy-input text-xs font-mono font-bold"
                  required
                />
              </div>

              <div>
                <label className="text-slate-700 dark:text-slate-300 font-bold block mb-1">Mesaj Metni *</label>
                <textarea
                  value={testMsg}
                  onChange={(e) => setTestMsg(e.target.value)}
                  rows={3}
                  className="w-full p-3 rounded-lg vuexy-input text-xs leading-relaxed font-medium"
                  placeholder="Test mesajı..."
                  required
                />
              </div>

              {testResult && (
                <div
                  className={`p-3 rounded-lg text-xs font-bold ${
                    testResult.includes('Hata')
                      ? 'bg-[#EA5455]/15 border border-[#EA5455]/30 text-[#EA5455]'
                      : 'bg-[#28C76F]/15 border border-[#28C76F]/30 text-[#28C76F]'
                  }`}
                >
                  {testResult}
                </div>
              )}

              <Button
                type="submit"
                disabled={testSending || !testPhone || !testMsg}
                size="lg"
                className="w-full font-bold shadow-md shadow-[#7367F0]/30 space-x-2 cursor-pointer"
              >
                {testSending ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>İletiliyor...</span>
                  </>
                ) : (
                  <>
                    <Send className="w-3.5 h-3.5" />
                    <span>Test Mesajını Gönder</span>
                  </>
                )}
              </Button>
            </form>
          </Card>
        </div>

        {/* Anti-Ban Safeguard Guidelines */}
        <div className="lg:col-span-6">
          <Card className="p-6 space-y-4">
            <h3 className="text-base font-bold text-slate-800 dark:text-white flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-[#28C76F]" />
              Scoutify Anti-Ban Güvenlik İlkeleri
            </h3>

            <div className="space-y-2.5 text-xs text-slate-700 dark:text-slate-300 font-medium">
              <div className="p-3 rounded-lg bg-slate-50 dark:bg-[#25293C] border border-slate-200/60 dark:border-white/[0.05] space-y-1">
                <span className="font-bold text-[#28C76F]">1. Kademeli Isınma (Warm-Up Schedule)</span>
                <p className="text-slate-500 dark:text-[#7E7F96] text-[11px]">
                  Yeni bağlanan hatlarda 1. Gün: 15 mesaj, 2. Gün: 25 mesaj, 5. Gün: 50 mesaj olarak limit kademeli artar.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 dark:bg-[#25293C] border border-slate-200/60 dark:border-white/[0.05] space-y-1">
                <span className="font-bold text-[#00CFE8]">2. İnsansı Gaussian Rastgele Gecikme</span>
                <p className="text-slate-500 dark:text-[#7E7F96] text-[11px]">
                  Her mesaj arasına 45-120 saniye rastgele bekleme ve öncesinde 3-7 saniye "Yazıyor..." simülasyonu eklenir.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 dark:bg-[#25293C] border border-slate-200/60 dark:border-white/[0.05] space-y-1">
                <span className="font-bold text-[#7367F0]">3. Spintax Varyasyon Zorunluluğu</span>
                <p className="text-slate-500 dark:text-[#7E7F96] text-[11px]">
                  Her alıcıya giden mesajın metin ve hash imzası farklılaşarak spam filtrelerine takılma riski minimize edilir.
                </p>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* QR Pairing Modal */}
      {isQRModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="vuexy-card max-w-sm w-full p-6 text-center space-y-5 shadow-xl border border-slate-200 dark:border-white/[0.1]">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-800 dark:text-white">WhatsApp Hattı Eşle</h3>
              <button
                onClick={() => setIsQRModalOpen(false)}
                className="text-slate-400 hover:text-slate-700 dark:hover:text-white cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-500 dark:text-[#7E7F96] font-medium">
              Telefonunuzda <strong>WhatsApp &gt; Bağlı Cihazlar &gt; Cihaz Bağla</strong> seçeneğine tıklayarak aşağıdaki QR kodu taratın.
            </p>

            {/* QR Code Presentation */}
            <div className="p-4 bg-white rounded-xl mx-auto inline-block shadow-md border border-slate-200">
              <svg viewBox="0 0 100 100" className="w-44 h-44">
                <rect width="100" height="100" fill="white" />
                <rect x="10" y="10" width="25" height="25" fill="#2F3349" />
                <rect x="15" y="15" width="15" height="15" fill="white" />
                <rect x="18" y="18" width="9" height="9" fill="#2F3349" />

                <rect x="65" y="10" width="25" height="25" fill="#2F3349" />
                <rect x="70" y="15" width="15" height="15" fill="white" />
                <rect x="73" y="18" width="9" height="9" fill="#2F3349" />

                <rect x="10" y="65" width="25" height="25" fill="#2F3349" />
                <rect x="15" y="70" width="15" height="15" fill="white" />
                <rect x="18" y="73" width="9" height="9" fill="#2F3349" />

                <rect x="42" y="15" width="6" height="6" fill="#2F3349" />
                <rect x="52" y="25" width="6" height="6" fill="#2F3349" />
                <rect x="42" y="35" width="6" height="6" fill="#2F3349" />
                <rect x="65" y="45" width="6" height="6" fill="#2F3349" />
                <rect x="45" y="55" width="6" height="6" fill="#2F3349" />
                <rect x="55" y="65" width="6" height="6" fill="#2F3349" />
                <rect x="42" y="75" width="6" height="6" fill="#2F3349" />
                <rect x="75" y="75" width="6" height="6" fill="#2F3349" />
              </svg>
            </div>

            {isPairingSuccess ? (
              <div className="p-3 rounded-lg bg-[#28C76F]/15 border border-[#28C76F]/30 text-[#28C76F] text-xs font-bold flex items-center justify-center gap-2">
                <CheckCircle2 className="w-4 h-4" />
                <span>Oturum Başarıyla Bağlandı!</span>
              </div>
            ) : (
              <Button
                onClick={handleSimulateScan}
                size="lg"
                className="w-full font-bold shadow-md shadow-[#7367F0]/30 cursor-pointer"
              >
                (Demo) QR Taramasını Onayla & Bağlan
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
