import React from 'react';
import { 
  Users, 
  CheckCircle2, 
  Send, 
  MessageSquareReply, 
  Smartphone, 
  Flame, 
  TrendingUp, 
  ArrowUpRight,
  Search,
  Sparkles,
  ShieldCheck,
  Clock,
  Zap,
  TrendingDown
} from 'lucide-react';
import { DashboardStats } from '../types';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';

interface DashboardPageProps {
  stats: DashboardStats | null;
  onNavigate: (tab: string) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ stats, onNavigate }) => {
  if (!stats) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-[#7367F0]"></div>
      </div>
    );
  }

  return (
    <div className="space-y-4 sm:space-y-6 pb-12 select-none animate-fade-in">
      {/* Vuexy Hero Welcome Card */}
      <div className="relative overflow-hidden rounded-xl bg-gradient-to-r from-[#7367F0] to-[#9E95F5] text-white p-4 sm:p-7 shadow-md">
        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center space-x-1.5 px-3 py-0.5 rounded-md bg-white/20 text-white text-xs font-bold mb-3 backdrop-blur-md">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Scoutify B2B Otomasyon Motoru</span>
          </div>
          <h2 className="text-lg sm:text-xl md:text-2xl font-extrabold text-white tracking-tight">
            Hedef Kitleni Bul, Spintax ile Kişiselleştir, Ban Riski Olmadan Ulaş!
          </h2>
          <p className="mt-2 text-xs md:text-sm text-white/90 leading-relaxed font-medium">
            Google Maps ve web dizinlerinden otomatik işletme numaralarını toplayın. Rastgele gecikmeler ve kademeli ısınma protokolüyle güvenle WhatsApp mesajı gönderin.
          </p>
          <div className="mt-5 flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 sm:gap-3">
            <Button
              onClick={() => onNavigate('lead-finder')}
              className="bg-white text-[#7367F0] hover:bg-white/95 font-bold shadow-md space-x-2 w-full sm:w-auto justify-center"
            >
              <Search className="w-4 h-4" />
              <span>Yeni Lead Taraması Başlat</span>
            </Button>
            <Button
              onClick={() => onNavigate('campaigns')}
              variant="outline"
              className="bg-white/10 hover:bg-white/20 border-white/30 text-white font-semibold space-x-2 w-full sm:w-auto justify-center"
            >
              <Send className="w-4 h-4" />
              <span>Kampanyaları Yönet</span>
            </Button>
          </div>
        </div>

        {/* Decorative Circles */}
        <div className="absolute right-0 top-0 bottom-0 w-80 bg-white/10 rounded-full blur-3xl pointer-events-none transform translate-x-1/3" />
      </div>

      {/* Vuexy 4-Column Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Card 1: Total Leads */}
        <Card className="hover:shadow-md transition-shadow">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-bold text-slate-500 dark:text-[#7E7F96] uppercase tracking-wider">
                  Toplam Lead
                </span>
                <div className="mt-2 text-2xl font-extrabold text-slate-800 dark:text-white">
                  {stats.total_leads}
                </div>
              </div>
              <div className="w-11 h-11 rounded-xl bg-[#7367F0]/15 text-[#7367F0] flex items-center justify-center font-bold">
                <Users className="w-5 h-5" />
              </div>
            </div>
            <div className="mt-3 flex items-center space-x-1.5 text-xs">
              <Badge variant="success" className="text-[10px]">
                {stats.whatsapp_eligible_leads} WA Uygun
              </Badge>
              <span className="text-slate-400 dark:text-[#7E7F96]">Kayıtlı işletme</span>
            </div>
          </CardContent>
        </Card>

        {/* Card 2: Messages Sent */}
        <Card className="hover:shadow-md transition-shadow">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-bold text-slate-500 dark:text-[#7E7F96] uppercase tracking-wider">
                  Gönderilen Mesaj
                </span>
                <div className="mt-2 text-2xl font-extrabold text-slate-800 dark:text-white">
                  {stats.total_messages_sent}
                </div>
              </div>
              <div className="w-11 h-11 rounded-xl bg-[#00CFE8]/15 text-[#00CFE8] flex items-center justify-center font-bold">
                <Send className="w-5 h-5" />
              </div>
            </div>
            <div className="mt-3 flex items-center space-x-1.5 text-xs">
              <Badge variant="info" className="text-[10px]">
                +{stats.messages_sent_today} Bugün
              </Badge>
              <span className="text-slate-400 dark:text-[#7E7F96]">Kademeli kuyruk</span>
            </div>
          </CardContent>
        </Card>

        {/* Card 3: Response Rate */}
        <Card className="hover:shadow-md transition-shadow">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-bold text-slate-500 dark:text-[#7E7F96] uppercase tracking-wider">
                  Geri Dönüş Oranı
                </span>
                <div className="mt-2 text-2xl font-extrabold text-slate-800 dark:text-white">
                  %{stats.response_rate_percentage}
                </div>
              </div>
              <div className="w-11 h-11 rounded-xl bg-[#28C76F]/15 text-[#28C76F] flex items-center justify-center font-bold">
                <MessageSquareReply className="w-5 h-5" />
              </div>
            </div>
            <div className="mt-3 flex items-center space-x-1.5 text-xs">
              <Badge variant="success" className="text-[10px]">
                {stats.replied_leads} Yanıt
              </Badge>
              <span className="text-slate-400 dark:text-[#7E7F96]">Dönüş sağlandı</span>
            </div>
          </CardContent>
        </Card>

        {/* Card 4: Connected WhatsApp Lines */}
        <Card className="hover:shadow-md transition-shadow">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-bold text-slate-500 dark:text-[#7E7F96] uppercase tracking-wider">
                  Bağlı Hat Sayısı
                </span>
                <div className="mt-2 text-2xl font-extrabold text-slate-800 dark:text-white">
                  {stats.connected_sessions} Hat
                </div>
              </div>
              <div className="w-11 h-11 rounded-xl bg-[#FF9F43]/15 text-[#FF9F43] flex items-center justify-center font-bold">
                <Smartphone className="w-5 h-5" />
              </div>
            </div>
            <div className="mt-3 flex items-center space-x-1.5 text-xs">
              <span className="w-2 h-2 rounded-full bg-[#28C76F] live-dot" />
              <span className="text-[#28C76F] font-bold">Online</span>
              <span className="text-slate-400 dark:text-[#7E7F96]">({stats.active_campaigns} Aktif Kampanya)</span>
            </div>
          </CardContent>
        </Card>
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
                  Dönüşüm Hunisi (Outreach Funnel)
                </h3>
                <p className="text-xs text-slate-400 dark:text-[#7E7F96] mt-0.5 font-medium">
                  Lead toplama ve WhatsApp mesajlaşma performans basamakları
                </p>
              </div>
              <Badge variant="primary">Canlı Metrikler</Badge>
            </div>

            <div className="space-y-4">
              {/* Step 1: Scraped */}
              <div>
                <div className="flex justify-between text-xs font-bold text-slate-700 dark:text-slate-200 mb-1.5">
                  <span>1. Taranan Toplam İşletmeler</span>
                  <span className="font-mono text-[#7367F0]">{stats.total_leads} Lead (%100)</span>
                </div>
                <div className="h-3 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden p-0.5">
                  <div className="h-full bg-[#7367F0] rounded-full w-full" />
                </div>
              </div>

              {/* Step 2: WA Eligible */}
              <div>
                <div className="flex justify-between text-xs font-bold text-slate-700 dark:text-slate-200 mb-1.5">
                  <span>2. Doğrulanmış WhatsApp Numaraları (Mobil E.164)</span>
                  <span className="font-mono text-[#00CFE8]">
                    {stats.whatsapp_eligible_leads} Numara (
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
                  <span>3. Mesaj İletilen (Contacted)</span>
                  <span className="font-mono text-[#FF9F43]">
                    {stats.contacted_leads} İşletme (
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
                  <span>4. Geri Dönüş Yapan (Replied / Interested)</span>
                  <span className="font-mono text-[#28C76F]">
                    {stats.replied_leads} Yanıt (%{stats.response_rate_percentage})
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
                  <p className="text-xs font-bold text-slate-800 dark:text-slate-100">Anti-Ban & Isınma Protokolü</p>
                  <p className="text-[11px] text-slate-500 dark:text-[#7E7F96] font-medium">
                    Her mesaj rastgele 45-120 saniye aralıkla gönderilir.
                  </p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onNavigate('whatsapp')}
                className="text-[#28C76F] hover:text-[#28C76F]/80 font-bold space-x-1"
              >
                <span>Hat Detayları</span>
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
                  Son Mesajlar
                </h3>
                <Badge variant="primary" className="font-mono text-[9px]">CANLI</Badge>
              </div>

              <div className="space-y-3">
                {stats.recent_activity.length === 0 ? (
                  <div className="text-center py-8 text-xs text-slate-400">
                    Henüz bir mesaj aktivitesi bulunmuyor.
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
              className="w-full mt-4 font-bold"
            >
              Tüm CRM Veritabanını Gör
            </Button>
          </Card>
        </div>
      </div>
    </div>
  );
};
