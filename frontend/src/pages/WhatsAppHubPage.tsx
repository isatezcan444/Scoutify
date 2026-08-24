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
  Zap 
} from 'lucide-react';
import { ApiClient } from '../api/client';
import { WhatsAppSession, MessageLog } from '../types';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';

interface WhatsAppHubPageProps {
  onRefreshStats: () => void;
}

export const WhatsAppHubPage: React.FC<WhatsAppHubPageProps> = ({ onRefreshStats }) => {
  const [sessions, setSessions] = useState<WhatsAppSession[]>([]);
  const [logs, setLogs] = useState<MessageLog[]>([]);
  const [loading, setLoading] = useState(false);

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
    <div className="space-y-8 pb-16 select-none animate-fade-in">
      {/* Top Header & New Account Action */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-extrabold text-slate-800 dark:text-white flex items-center gap-2">
            <Smartphone className="w-5 h-5 text-[#28C76F]" />
            WhatsApp Oturumları & Anti-Ban Hub
          </h2>
          <p className="text-xs text-slate-500 dark:text-[#7E7F96] mt-0.5 font-medium">
            Çoklu hat yönetimi, kademeli hesap ısınma (warm-up) ve günlük kota güvenliği
          </p>
        </div>

        <Button
          onClick={handleCreateSession}
          size="sm"
          className="space-x-2 font-bold shadow-md shadow-[#7367F0]/30"
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
            <Card key={sess.id} className="p-6 hover:shadow-md transition-shadow flex flex-col justify-between h-full space-y-5">
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
                    className="gap-1 font-bold"
                  >
                    {sess.status === 'CONNECTED' && (
                      <span className="w-1.5 h-1.5 rounded-full bg-[#28C76F] live-dot" />
                    )}
                    {sess.status}
                  </Badge>
                </div>

                {/* Warm-Up Day & Quota Status */}
                <div className="mt-5 space-y-3 p-3.5 rounded-lg bg-slate-50 dark:bg-[#25293C] border border-slate-200/60 dark:border-white/[0.05]">
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
                    className="text-slate-500 hover:text-[#FF9F43] flex items-center gap-1 font-bold transition-colors"
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
                    className="text-[#7367F0] hover:text-[#685DD8] flex items-center gap-1 font-bold"
                  >
                    <QrCode className="w-3.5 h-3.5" />
                    <span>QR Kodu Tara</span>
                  </button>
                )}

                <button
                  onClick={() => handleDelete(sess.id)}
                  className="text-slate-400 hover:text-[#EA5455] p-1 transition-colors"
                  title="Oturumu Sil"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </Card>
          );
        })}
      </div>

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
                className="w-full font-bold shadow-md shadow-[#7367F0]/30 space-x-2"
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
                className="text-slate-400 hover:text-slate-700 dark:hover:text-white"
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
                className="w-full font-bold shadow-md shadow-[#7367F0]/30"
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
