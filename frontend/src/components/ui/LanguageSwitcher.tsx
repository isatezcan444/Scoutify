import React, { useState, useRef, useEffect } from 'react';
import { useI18n } from '../../context/I18nContext';
import { Globe, ChevronDown, Check } from 'lucide-react';

export const LanguageSwitcher: React.FC = () => {
  const { language, setLanguage } = useI18n();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on click outside or escape key
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  const handleSelect = (lang: 'en' | 'tr') => {
    setLanguage(lang);
    setIsOpen(false);
  };

  const options = [
    { code: 'en' as const, label: 'English', subLabel: 'EN' },
    { code: 'tr' as const, label: 'Türkçe', subLabel: 'TR' },
  ];

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      {/* Vuexy Dropdown Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-haspopup="true"
        aria-expanded={isOpen}
        title={language === 'en' ? 'Switch Language' : 'Dili Değiştir'}
        className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border text-xs font-extrabold transition-all duration-150 cursor-pointer shadow-sm ${
          isOpen
            ? 'border-[#7367F0] bg-[#7367F0]/10 text-[#7367F0] ring-2 ring-[#7367F0]/20'
            : 'border-slate-200 dark:border-white/[0.08] hover:border-[#7367F0]/40 bg-slate-50/80 dark:bg-white/[0.04] text-slate-700 dark:text-slate-200 hover:text-[#7367F0] dark:hover:text-[#A59DF8]'
        }`}
      >
        <Globe className="w-3.5 h-3.5 text-[#7367F0] shrink-0" />
        <span className="tracking-wide uppercase font-mono">{language}</span>
        <ChevronDown className={`w-3 h-3 text-slate-400 transition-transform duration-200 ${isOpen ? 'rotate-180 text-[#7367F0]' : ''}`} />
      </button>

      {/* Vuexy Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-44 rounded-xl bg-white dark:bg-[#2F3349] border border-slate-200/80 dark:border-white/[0.08] shadow-2xl py-1.5 z-50 animate-scale-in">
          <div className="px-3 py-1 text-[10px] font-bold text-slate-400 dark:text-[#7E7F96] uppercase tracking-wider border-b border-slate-100 dark:border-white/[0.05] mb-1">
            {language === 'en' ? 'Select Language' : 'Dil Seçimi'}
          </div>

          <div className="p-1 space-y-0.5">
            {options.map((opt) => {
              const isSelected = language === opt.code;
              return (
                <button
                  key={opt.code}
                  type="button"
                  onClick={() => handleSelect(opt.code)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs font-semibold flex items-center justify-between transition-colors cursor-pointer ${
                    isSelected
                      ? 'bg-[#7367F0] text-white font-bold shadow-sm shadow-[#7367F0]/30'
                      : 'text-slate-700 dark:text-[#DBD7EC] hover:bg-slate-100 dark:hover:bg-white/[0.06] hover:text-[#7367F0] dark:hover:text-white'
                  }`}
                >
                  <div className="flex items-center space-x-2">
                    <span>{opt.label}</span>
                    <span className={`text-[10px] font-mono px-1.5 py-0.2 rounded ${isSelected ? 'bg-white/20 text-white' : 'bg-slate-100 dark:bg-white/[0.06] text-slate-400'}`}>
                      {opt.subLabel}
                    </span>
                  </div>
                  {isSelected && <Check className="w-3.5 h-3.5 text-white" />}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
