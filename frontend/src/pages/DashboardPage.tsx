import React from 'react';
import { 
  Users, 
  Send, 
  MessageSquareReply, 
  Smartphone, 
  TrendingUp, 
  ArrowUpRight,
  Search,
  ShieldCheck,
  Clock,
  Loader2
} from 'lucide-react';
import { DashboardStats } from '../types';
import { Button, Badge, Card, HeroBanner, StatsCard } from '../components/ui';
import { useI18n } from '../context/I18nContext';

interface DashboardPageProps {
  stats: DashboardStats | null;
  onNavigate: (tab: string) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ stats, onNavigate }) => {
  const { t } = useI18n();

  if (!stats) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-10 h-10 animate-spin text-[#7367F0]" />
      </div>
    );
  }

  return (
    <div className="space-y-4 sm:space-y-6 pb-12 select-none animate-fade-in">
      {/* Vuexy Hero Welcome Card */}
      <HeroBanner
        badgeText={t('dashboard.heroBadge')}
        title={t('dashboard.heroTitle')}
        subtitle={t('dashboard.heroSubtitle')}
        actions={
          <>
            <Button
              onClick={() => onNavigate('lead-finder')}
              className="bg-white text-[#7367F0] hover:bg-white/95 font-bold shadow-md space-x-2 w-full sm:w-auto justify-center cursor-pointer"
            >
              <Search className="w-4 h-4" />
              <span>{t('dashboard.discoverNewLeads')}</span>
            </Button>
            <Button
              onClick={() => onNavigate('campaigns')}
              variant="outline"
              className="bg-white/10 hover:bg-white/20 border-white/30 text-white font-semibold space-x-2 w-full sm:w-auto justify-center cursor-pointer"
            >
              <Send className="w-4 h-4" />
              <span>{t('dashboard.quickStartCampaign')}</span>
            </Button>
          </>
        }
      />

      {/* Vuexy 4-Column Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <StatsCard
          title={t('dashboard.totalLeads')}
          value={stats.total_leads}
          icon={Users}
          iconVariant="primary"
          badge={{
            text: `${stats.whatsapp_eligible_leads} ${t('dashboard.whatsappEligible')}`,
            variant: 'success',
          }}
          subText="CRM"
          onClick={() => onNavigate('leads')}
        />

        <StatsCard
          title={t('dashboard.contactedLeads')}
          value={stats.total_messages_sent}
          icon={Send}
          iconVariant="info"
          badge={{
            text: `+${stats.messages_sent_today} ${t('dashboard.today')}`,
            variant: 'info',
          }}
          subText={t('dashboard.queue')}
          onClick={() => onNavigate('campaigns')}
        />

        <StatsCard
          title={t('dashboard.responseRate')}
          value={`%${stats.response_rate_percentage}`}
          icon={MessageSquareReply}
          iconVariant="success"
          badge={{
            text: `${stats.replied_leads} ${t('dashboard.repliedLeads')}`,
            variant: 'success',
          }}
          subText={t('dashboard.inbound')}
        />

        <StatsCard
          title={t('dashboard.connectedSessions')}
          value={stats.connected_sessions}
          icon={Smartphone}
          iconVariant="warning"
          badge={{
            text: t('dashboard.online'),
            variant: 'success',
          }}
          subText={`(${stats.active_campaigns} ${t('dashboard.activeCampaigns')})`}
          onClick={() => onNavigate('whatsapp')}
        />
      </div>

      {/* Vuexy Outreach Funnel & Activity Stream */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Funnel */}
        <div className="lg:col-span-8">
          <Card className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-base font-extrabold text-slate-800 dark:text-white flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-[#7367F0]" />
                  {t('dashboard.outreachFunnel')}
                </h3>
                <p className="text-xs text-slate-400 dark:text-[#7E7F96] mt-0.5 font-medium">
                  {t('titles.dashboardSub')}
                </p>
              </div>
              <Badge variant="primary">{t('dashboard.realtime')}</Badge>
            </div>

            <div className="space-y-4">
              {/* Step 1: Scraped */}
              <div>
                <div className="flex justify-between text-xs font-bold text-slate-700 dark:text-slate-200 mb-1.5">
                  <span>1. {t('dashboard.funnelTotal')}</span>
                  <span className="font-mono text-[#7367F0]">{stats.total_leads} (%100)</span>
                </div>
                <div className="h-3 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden p-0.5">
                  <div className="h-full bg-[#7367F0] rounded-full w-full" />
                </div>
              </div>

              {/* Step 2: WA Eligible */}
              <div>
                <div className="flex justify-between text-xs font-bold text-slate-700 dark:text-slate-200 mb-1.5">
                  <span>2. {t('dashboard.funnelWaReady')}</span>
                  <span className="font-mono text-[#00CFE8]">
                    {stats.whatsapp_eligible_leads} (
                    {stats.total_leads > 0 ? Math.round((stats.whatsapp_eligible_leads / stats.total_leads) * 100) : 0}%)
                  </span>
                </div>
                <div className="h-3 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden p-0.5">
                  <div 
                    className="h-full bg-[#00CFE8] rounded-full transition-all duration-500" 
                    style={{ width: `${stats.total_leads > 0 ? (stats.whatsapp_eligible_leads / stats.total_leads) * 100 : 0}%` }}
                  />
                </div>
              </div>

              {/* Step 3: Contacted */}
              <div>
                <div className="flex justify-between text-xs font-bold text-slate-700 dark:text-slate-200 mb-1.5">
                  <span>3. {t('dashboard.funnelContacted')}</span>
                  <span className="font-mono text-[#FF9F43]">
                    {stats.contacted_leads} (
                    {stats.whatsapp_eligible_leads > 0 ? Math.round((stats.contacted_leads / stats.whatsapp_eligible_leads) * 100) : 0}%)
                  </span>
                </div>
                <div className="h-3 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden p-0.5">
                  <div 
                    className="h-full bg-[#FF9F43] rounded-full transition-all duration-500" 
                    style={{ width: `${stats.whatsapp_eligible_leads > 0 ? (stats.contacted_leads / stats.whatsapp_eligible_leads) * 100 : 0}%` }}
                  />
                </div>
              </div>

              {/* Step 4: Replied */}
              <div>
                <div className="flex justify-between text-xs font-bold text-slate-700 dark:text-slate-200 mb-1.5">
                  <span>4. {t('dashboard.funnelReplied')}</span>
                  <span className="font-mono text-[#28C76F]">
                    {stats.replied_leads} (%{stats.response_rate_percentage})
                  </span>
                </div>
                <div className="h-3 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden p-0.5">
                  <div 
                    className="h-full bg-[#28C76F] rounded-full transition-all duration-500" 
                    style={{ width: `${Math.min(stats.response_rate_percentage * 2, 100)}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Vuexy Safeguard Banner */}
            <div className="mt-6 p-4 rounded-lg bg-[#28C76F]/10 border border-[#28C76F]/20 flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <ShieldCheck className="w-5 h-5 text-[#28C76F]" />
                <div>
                  <p className="text-xs font-bold text-slate-800 dark:text-slate-100">{t('dashboard.cooldownPolicyTitle')}</p>
                  <p className="text-[11px] text-slate-500 dark:text-[#7E7F96] font-medium">
                    {t('dashboard.cooldownPolicyDesc')}
                  </p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onNavigate('whatsapp')}
                className="text-[#28C76F] hover:text-[#28C76F]/80 font-bold space-x-1 cursor-pointer"
              >
                <span>{t('dashboard.manageSessions')}</span>
                <ArrowUpRight className="w-3.5 h-3.5" />
              </Button>
            </div>
          </Card>
        </div>

        {/* Right Column: Recent Activity Feed */}
        <div className="lg:col-span-4">
          <Card className="p-6 h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base font-extrabold text-slate-800 dark:text-white flex items-center gap-2">
                  <Clock className="w-4 h-4 text-[#7367F0]" />
                  {t('campaigns.logsTitle')}
                </h3>
                <Badge variant="primary" className="font-mono text-[9px]">{t('dashboard.live')}</Badge>
              </div>

              <div className="space-y-3">
                {stats.recent_activity.length === 0 ? (
                  <div className="text-center py-8 text-xs text-slate-400">
                    {t('dashboard.noRecentLeads')}
                  </div>
                ) : (
                  stats.recent_activity.map((act) => (
                    <div
                      key={act.id}
                      className="p-3 rounded-lg bg-slate-50 dark:bg-[#25293C] border border-slate-200/60 dark:border-white/[0.05] transition-all"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-mono text-xs text-slate-800 dark:text-slate-200 font-bold">
                          {act.phone}
                        </span>
                        <Badge variant="success" className="text-[9px]">
                          {act.status}
                        </Badge>
                      </div>
                      <p className="text-[11px] text-slate-500 dark:text-[#7E7F96] line-clamp-1 italic">
                        "{act.message_snippet}"
                      </p>
                      <div className="mt-1 text-[10px] text-slate-400 dark:text-slate-500 text-right font-mono">{act.time}</div>
                    </div>
                  ))
                )}
              </div>
            </div>

            <Button
              variant="outline"
              onClick={() => onNavigate('leads')}
              className="w-full mt-4 font-bold cursor-pointer"
            >
              {t('dashboard.viewAllLeads')}
            </Button>
          </Card>
        </div>
      </div>
    </div>
  );
};
