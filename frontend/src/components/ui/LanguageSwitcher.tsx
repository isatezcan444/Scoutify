import React from 'react';
import { useI18n } from '../../context/I18nContext';
import { Globe, ChevronDown } from 'lucide-react';

export const LanguageSwitcher: React.FC = () => {
  const { language, setLanguage } = useI18n();

  return (
    <div className="relative inline-flex items-center">
      <div className="flex items-center pl-2.5 pr-2 py-1.5 rounded-lg border border-slate-200 dark:border-white/[0.08] hover:border-[#7367F0]/40 bg-slate-50/80 dark:bg-white/[0.04] text-slate-700 dark:text-slate-200 text-xs font-bold transition-all shadow-sm group">
        <Globe className="w-3.5 h-3.5 text-[#7367F0] shrink-0 mr-1.5 pointer-events-none" />
        <select
          value={language}
          onChange={(e) => setLanguage(e.target.value as 'en' | 'tr')}
          className="bg-transparent text-slate-700 dark:text-slate-200 text-xs font-extrabold focus:outline-none cursor-pointer pr-4 appearance-none"
          title="Select Language / Dil Seçin"
        >
          <option value="en" className="dark:bg-[#2F3349] dark:text-white text-slate-800">
            🇺🇸 EN
          </option>
          <option value="tr" className="dark:bg-[#2F3349] dark:text-white text-slate-800">
            🇹🇷 TR
          </option>
        </select>
        <ChevronDown className="w-3 h-3 text-slate-400 pointer-events-none -ml-3.5 group-hover:text-[#7367F0] transition-colors" />
      </div>
    </div>
  );
};
