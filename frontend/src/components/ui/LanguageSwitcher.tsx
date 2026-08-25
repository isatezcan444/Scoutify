import React from 'react';
import { useI18n } from '../../context/I18nContext';
import { Globe } from 'lucide-react';

export const LanguageSwitcher: React.FC = () => {
  const { language, setLanguage } = useI18n();

  const toggleLanguage = () => {
    setLanguage(language === 'en' ? 'tr' : 'en');
  };

  return (
    <button
      type="button"
      onClick={toggleLanguage}
      title={language === 'en' ? 'Türkçe Diline Geç' : 'Switch to English'}
      className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-white/[0.08] hover:border-[#7367F0]/40 bg-slate-50/80 dark:bg-white/[0.04] text-slate-700 dark:text-slate-200 hover:text-[#7367F0] dark:hover:text-[#A59DF8] text-xs font-extrabold transition-all duration-150 active:scale-95 cursor-pointer shadow-sm"
    >
      <Globe className="w-3.5 h-3.5 text-[#7367F0]" />
      <span className="tracking-wide">
        {language === 'en' ? '🇺🇸 EN' : '🇹🇷 TR'}
      </span>
    </button>
  );
};
