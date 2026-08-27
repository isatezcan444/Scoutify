import React, { useState, useEffect } from 'react';
import { ThemeProvider } from './context/ThemeContext';
import { ToastProvider, useToast } from './context/ToastContext';
import { I18nProvider, useI18n } from './context/I18nContext';
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

const AppContent: React.FC = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isWsConnected, setIsWsConnected] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const toast = useToast();
  const { t } = useI18n();

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
        // Broadcast to hooks/subscribers
        window.dispatchEvent(new CustomEvent('scoutify:ws_event', { detail: eventData }));

        // Handle Inbound Reply Event
        if (eventData.event === 'inbound_reply') {
          toast.reply(
            `${eventData.lead_name} (${eventData.phone}): "${eventData.message}"`,
            t('toast.newReplyTitle')
          );
          refreshStats();
        } else if (eventData.event === 'message_sent') {
          toast.success(
            `${eventData.lead_name} (${eventData.phone})`,
            t('toast.messageSentTitle')
          );
          refreshStats();
        } else if (eventData.event === 'scraper_completed') {
          toast.info(
            t('toast.scraperCompletedMsg', { found: eventData.total_found, leads: eventData.total_new_leads }),
            t('toast.scraperCompletedTitle')
          );
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
  }, [toast, t]);

  const getPageTitle = () => {
    switch (activeTab) {
      case 'dashboard':
        return t('titles.dashboard');
      case 'lead-finder':
        return t('titles.leadFinder');
      case 'leads':
        return t('titles.leads');
      case 'campaigns':
        return t('titles.campaigns');
      case 'whatsapp':
        return t('titles.whatsapp');
      case 'blacklist':
        return t('titles.blacklist');
      case 'settings':
        return t('titles.settings');
      default:
        return 'Scoutify';
    }
  };

  const getPageSubtitle = () => {
    switch (activeTab) {
      case 'dashboard':
        return t('titles.dashboardSub');
      case 'lead-finder':
        return t('titles.leadFinderSub');
      case 'leads':
        return t('titles.leadsSub');
      case 'campaigns':
        return t('titles.campaignsSub');
      case 'whatsapp':
        return t('titles.whatsappSub');
      case 'blacklist':
        return t('titles.blacklistSub');
      case 'settings':
        return t('titles.settingsSub');
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
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <I18nProvider>
        <ToastProvider>
          <AppContent />
        </ToastProvider>
      </I18nProvider>
    </ThemeProvider>
  );
};

export default App;
