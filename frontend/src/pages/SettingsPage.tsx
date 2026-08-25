import React from 'react';
import { 
  Settings, 
  Server, 
  Moon, 
  Sun, 
  Database,
  ShieldCheck,
  Zap,
  Globe,
  Languages
} from 'lucide-react';
import { Card } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { useTheme } from '../context/ThemeContext';
import { useI18n } from '../context/I18nContext';

export const SettingsPage: React.FC = () => {
  const { theme, toggleTheme } = useTheme();
  const { language, setLanguage, t } = useI18n();

  return (
    <div className="space-y-6 pb-16 max-w-4xl select-none animate-fade-in">
      {/* Page Header */}
      <div>
        <h2 className="text-xl font-extrabold text-slate-800 dark:text-white flex items-center gap-2">
          <Settings className="w-5 h-5 text-[#7367F0]" />
          {t('settings.title')}
        </h2>
        <p className="text-xs text-slate-500 dark:text-[#7E7F96] mt-0.5 font-medium">
          {t('settings.subtitle')}
        </p>
      </div>

      {/* Language & Localization Card */}
      <Card className="p-4 sm:p-6 space-y-4">
        <h3 className="text-sm font-bold text-slate-800 dark:text-white flex items-center gap-2">
          <Languages className="w-4 h-4 text-[#7367F0]" />
          {t('settings.languageSection')}
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <button
            type="button"
            onClick={() => setLanguage('en')}
            className={`p-4 rounded-xl border text-left transition-all cursor-pointer flex items-center justify-between ${
              language === 'en'
                ? 'border-[#7367F0] bg-[#7367F0]/10 ring-1 ring-[#7367F0]/50 shadow-sm'
                : 'border-slate-200 dark:border-white/[0.08] bg-slate-50/50 dark:bg-white/[0.02] hover:bg-slate-100 dark:hover:bg-white/[0.04]'
            }`}
          >
            <div>
              <span className="text-xs font-bold text-slate-800 dark:text-white block">
                🇺🇸 English (EN)
              </span>
              <span className="text-[11px] text-slate-400">Default system language</span>
            </div>
            {language === 'en' && (
              <Badge variant="primary" className="text-[10px]">Active</Badge>
            )}
          </button>

          <button
            type="button"
            onClick={() => setLanguage('tr')}
            className={`p-4 rounded-xl border text-left transition-all cursor-pointer flex items-center justify-between ${
              language === 'tr'
                ? 'border-[#7367F0] bg-[#7367F0]/10 ring-1 ring-[#7367F0]/50 shadow-sm'
                : 'border-slate-200 dark:border-white/[0.08] bg-slate-50/50 dark:bg-white/[0.02] hover:bg-slate-100 dark:hover:bg-white/[0.04]'
            }`}
          >
            <div>
              <span className="text-xs font-bold text-slate-800 dark:text-white block">
                🇹🇷 Türkçe (TR)
              </span>
              <span className="text-[11px] text-slate-400">Türkçe arayüz ve bildirimler</span>
            </div>
            {language === 'tr' && (
              <Badge variant="primary" className="text-[10px]">Aktif</Badge>
            )}
          </button>
        </div>
      </Card>

      {/* Theme Setting Card */}
      <Card className="p-4 sm:p-6 space-y-4">
        <h3 className="text-sm font-bold text-slate-800 dark:text-white flex items-center gap-2">
          {theme === 'light' ? <Sun className="w-4 h-4 text-[#FF9F43]" /> : <Moon className="w-4 h-4 text-[#7367F0]" />}
          {t('settings.themeSection')}
        </h3>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 rounded-lg bg-slate-50 dark:bg-[#25293C] border border-slate-200/60 dark:border-white/[0.05] gap-3">
          <div>
            <p className="text-xs font-bold text-slate-800 dark:text-slate-200">
              {theme === 'light' ? t('settings.themeLight') : t('settings.themeDark')}
            </p>
            <p className="text-[11px] text-slate-400 dark:text-[#7E7F96]">
              {theme === 'light' ? 'Light mode is currently active.' : 'Dark mode (Vuexy Sleek) is currently active.'}
            </p>
          </div>

          <button
            onClick={toggleTheme}
            className="px-4 py-2 rounded-lg bg-[#7367F0] hover:bg-[#685DD8] text-white font-bold text-xs shadow-md shadow-[#7367F0]/30 transition-all active:scale-95 flex items-center justify-center gap-2 shrink-0 cursor-pointer"
          >
            {theme === 'light' ? (
              <>
                <Moon className="w-4 h-4" />
                <span>{t('header.darkMode')}</span>
              </>
            ) : (
              <>
                <Sun className="w-4 h-4" />
                <span>{t('header.lightMode')}</span>
              </>
            )}
          </button>
        </div>
      </Card>

      {/* Services Connections Card */}
      <Card className="p-4 sm:p-6 space-y-4 sm:space-y-6">
        <h3 className="text-sm font-bold text-slate-800 dark:text-white flex items-center gap-2">
          <Server className="w-4 h-4 text-[#7367F0]" />
          System & Service Endpoints
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div className="p-4 rounded-xl bg-slate-50 dark:bg-[#25293C] border border-slate-200/60 dark:border-white/[0.05] space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-slate-700 dark:text-slate-200 flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-[#7367F0]" />
                FastAPI REST & WebSocket Core
              </span>
              <Badge variant="success">Active</Badge>
            </div>
            <p className="font-mono text-[#7367F0] text-[11px] font-bold">http://localhost:8000/api/v1</p>
            <p className="text-slate-400 dark:text-[#7E7F96] text-[10px]">Pydantic v2 & SQLAlchemy 2.0 Async Session</p>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 dark:bg-[#25293C] border border-slate-200/60 dark:border-white/[0.05] space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-slate-700 dark:text-slate-200 flex items-center gap-1.5">
                <Globe className="w-3.5 h-3.5 text-[#00CFE8]" />
                WhatsApp Gateway Sidecar
              </span>
              <Badge variant="success">Active</Badge>
            </div>
            <p className="font-mono text-[#00CFE8] text-[11px] font-bold">http://localhost:3001</p>
            <p className="text-slate-400 dark:text-[#7E7F96] text-[10px]">Baileys WebSocket Multi-Device Socket Engine</p>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 dark:bg-[#25293C] border border-slate-200/60 dark:border-white/[0.05] space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-slate-700 dark:text-slate-200 flex items-center gap-1.5">
                <Database className="w-3.5 h-3.5 text-[#28C76F]" />
                Database Engine
              </span>
              <Badge variant="success">SQLite + WAL</Badge>
            </div>
            <p className="font-mono text-[#28C76F] text-[11px] font-bold">sqlite+aiosqlite:///scoutify.db</p>
            <p className="text-slate-400 dark:text-[#7E7F96] text-[10px]">Async I/O non-blocking connection pool</p>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 dark:bg-[#25293C] border border-slate-200/60 dark:border-white/[0.05] space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-slate-700 dark:text-slate-200 flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-[#FF9F43]" />
                Crawler & Scraper Engine
              </span>
              <Badge variant="success">Playwright Chromium</Badge>
            </div>
            <p className="font-mono text-[#FF9F43] text-[11px] font-bold">Google Maps Live Playwright Engine</p>
            <p className="text-slate-400 dark:text-[#7E7F96] text-[10px]">Multi-line address extraction & stream feed</p>
          </div>
        </div>
      </Card>
    </div>
  );
};
