import React, { useState, useEffect } from 'react';
import { ThemeProvider } from './context/ThemeContext';
import { Sidebar } from './components/Layout/Sidebar';
import { TopHeader } from './components/Layout/TopHeader';
import { DashboardPage } from './pages/DashboardPage';
import { LeadFinderPage } from './pages/LeadFinderPage';
import { LeadCRMPage } from './pages/LeadCRMPage';
import { CampaignsPage } from './pages/CampaignsPage';
import { WhatsAppHubPage } from './pages/WhatsAppHubPage';
import { BlacklistPage } from './pages/BlacklistPage';
import { SettingsPage } from './pages/SettingsPage';
import { ApiClient, createWebSocket } from './api/client';
import { DashboardStats } from './types';
import { Sparkles, CheckCircle2, MessageCircle, X } from 'lucide-react';

const AppContent: React.FC = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isWsConnected, setIsWsConnected] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [notifications, setNotifications] = useState<Array<{ id: string; title: string; desc: string; type: 'success' | 'info' | 'reply' }>>([]);

  const refreshStats = async () => {
    try {
      const data = await ApiClient.getDashboardStats();
      setStats(data);
    } catch (err) {
      console.error('Error loading stats:', err);
    }
  };

  useEffect(() => {
    refreshStats();

    // Setup Realtime WebSocket connection
    let ws: WebSocket | null = null;
    try {
      ws = createWebSocket((eventData) => {
        setIsWsConnected(true);
        // Handle Inbound Reply Event
        if (eventData.event === 'inbound_reply') {
          addNotification({
            title: '📩 Yeni WhatsApp Yanıtı!',
            desc: `${eventData.lead_name} (${eventData.phone}): "${eventData.message}"`,
            type: 'reply'
          });
          refreshStats();
        } else if (eventData.event === 'message_sent') {
          addNotification({
            title: '✅ Mesaj İletildi',
            desc: `${eventData.lead_name} (${eventData.phone}) alıcısına güvenle iletildi.`,
            type: 'success'
          });
          refreshStats();
        } else if (eventData.event === 'scraper_completed') {
          addNotification({
            title: '🎉 Tarama Tamamlandı',
            desc: `Toplam ${eventData.total_found} işletme bulundu, ${eventData.total_new_leads} yeni lead eklendi.`,
            type: 'info'
          });
          refreshStats();
        }
      });
    } catch (e) {
      console.warn('WS Init failed:', e);
    }

    const interval = setInterval(refreshStats, 8000);

    return () => {
      clearInterval(interval);
      if (ws) ws.close();
    };
  }, []);

  const addNotification = (notif: { title: string; desc: string; type: 'success' | 'info' | 'reply' }) => {
    const id = Math.random().toString(36).substring(2, 9);
    setNotifications((prev) => [{ id, ...notif }, ...prev.slice(0, 3)]);
    setTimeout(() => {
      setNotifications((prev) => prev.filter((n) => n.id !== id));
    }, 5000);
  };

  const getPageTitle = () => {
    switch (activeTab) {
      case 'dashboard':
        return 'Genel Bakış & Dönüşüm Paneli';
      case 'lead-finder':
        return 'İşletme Ara';
      case 'leads':
        return 'Müşteri Adayları (CRM) Veritabanı';
      case 'campaigns':
        return 'WhatsApp Kampanyaları & Spintax Studio';
      case 'whatsapp':
        return 'WhatsApp Oturumları & Anti-Ban Kalkanı';
      case 'blacklist':
        return 'Kara Liste & Opt-Out Filtresi';
      case 'settings':
        return 'Ayarlar';
      default:
        return 'Scoutify';
    }
  };

  const getPageSubtitle = () => {
    switch (activeTab) {
      case 'dashboard':
        return 'Gerçek zamanlı lead ve WhatsApp erişim metrikleri';
      case 'lead-finder':
        return 'Sektör ve lokasyon bazlı otomatik işletme ve telefon toplama';
      case 'leads':
        return 'Toplanan işletme profilleri, telefon doğrulaması ve iletişim geçmişi';
      case 'campaigns':
        return 'Metin çeşitlendirme (Spintax), rastgele gecikmeler ve kademeli gönderim';
      case 'whatsapp':
        return 'Cihaz QR kod eşleme, ısınma takvimi ve günlük kota takibi';
      case 'blacklist':
        return 'Otomatik veya manuel engellenen numaralar';
      case 'settings':
        return 'WhatsApp bekleme süreleri, anti-ban koruma parametreleri ve tema';
      default:
        return undefined;
    }
  };

  return (
    <div className="min-h-screen bg-[#F8F7FA] dark:bg-[#25293C] text-[#4B465C] dark:text-[#DBD7EC] flex font-sans transition-colors duration-200">
      {/* Sidebar with Desktop fixed & Mobile drawer support */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isWsConnected={isWsConnected}
        totalLeadsCount={stats?.total_leads}
        activeCampaignsCount={stats?.active_campaigns}
        isOpenMobile={isMobileMenuOpen}
        onCloseMobile={() => setIsMobileMenuOpen(false)}
      />

      {/* Main Content Area: Responsive left padding (pl-0 on mobile, pl-64 on desktop) */}
      <div className="flex-1 lg:pl-64 pl-0 flex flex-col min-h-screen w-full overflow-x-hidden">
        {/* Floating Top Header */}
        <TopHeader
          title={getPageTitle()}
          subtitle={getPageSubtitle()}
          onOpenQuickScrape={() => setActiveTab('lead-finder')}
          onOpenQuickTest={() => setActiveTab('whatsapp')}
          onOpenSettings={() => setActiveTab('settings')}
          onToggleMobileMenu={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
        />

        {/* Dynamic Page Container with Responsive Padding */}
        <main className="flex-1 p-3.5 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
          {activeTab === 'dashboard' && (
            <DashboardPage stats={stats} onNavigate={setActiveTab} />
          )}
          {activeTab === 'lead-finder' && (
            <LeadFinderPage onNavigate={setActiveTab} onRefreshStats={refreshStats} />
          )}
          {activeTab === 'leads' && (
            <LeadCRMPage onRefreshStats={refreshStats} />
          )}
          {activeTab === 'campaigns' && (
            <CampaignsPage onRefreshStats={refreshStats} />
          )}
          {activeTab === 'whatsapp' && (
            <WhatsAppHubPage onRefreshStats={refreshStats} />
          )}
          {activeTab === 'blacklist' && (
            <BlacklistPage />
          )}
          {activeTab === 'settings' && (
            <SettingsPage />
          )}
        </main>
      </div>

      {/* Realtime Toast Notifications Floating Container */}
      <div className="fixed bottom-4 right-4 sm:bottom-6 sm:right-6 z-50 space-y-2 max-w-[calc(100vw-2rem)] sm:max-w-sm w-full pointer-events-none">
        {notifications.map((notif) => (
          <div
            key={notif.id}
            className={`pointer-events-auto p-3.5 sm:p-4 rounded-xl shadow-lg border flex items-start space-x-3 animate-fade-in ${
              notif.type === 'reply'
                ? 'bg-white dark:bg-[#2F3349] border-[#7367F0]/40 text-slate-800 dark:text-slate-100'
                : notif.type === 'success'
                ? 'bg-white dark:bg-[#2F3349] border-[#28C76F]/40 text-slate-800 dark:text-slate-100'
                : 'bg-white dark:bg-[#2F3349] border-[#00CFE8]/40 text-slate-800 dark:text-slate-100'
            }`}
          >
            <div className="shrink-0 mt-0.5">
              {notif.type === 'reply' ? (
                <MessageCircle className="w-4 h-4 sm:w-5 sm:h-5 text-[#7367F0]" />
              ) : notif.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4 sm:w-5 sm:h-5 text-[#28C76F]" />
              ) : (
                <Sparkles className="w-4 h-4 sm:w-5 sm:h-5 text-[#00CFE8]" />
              )}
            </div>
            <div className="flex-1 text-xs">
              <h4 className="font-bold text-slate-900 dark:text-white mb-0.5">{notif.title}</h4>
              <p className="text-slate-500 dark:text-[#7E7F96] leading-tight">{notif.desc}</p>
            </div>
            <button
              onClick={() => setNotifications((prev) => prev.filter((n) => n.id !== notif.id))}
              className="text-slate-400 hover:text-slate-700 dark:hover:text-white shrink-0 p-1"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
};

export default App;
