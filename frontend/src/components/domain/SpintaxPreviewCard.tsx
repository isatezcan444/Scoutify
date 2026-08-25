import React, { useState } from 'react';
import { Sparkles, RefreshCw, Copy, Check } from 'lucide-react';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { IconButton } from '../ui/IconButton';
import { cn } from '../../lib/utils';

export interface SpintaxPreviewCardProps {
  template: string;
  sampleLead?: {
    name?: string;
    city?: string;
    district?: string;
    category?: string;
    rating?: number;
  };
  className?: string;
}

export const SpintaxPreviewCard: React.FC<SpintaxPreviewCardProps> = ({
  template,
  sampleLead = {
    name: 'Özel DentaLine Polikliniği',
    city: 'İstanbul',
    district: 'Ataşehir',
    category: 'Diş Kliniği',
    rating: 4.9,
  },
  className,
}) => {
  const [copied, setCopied] = useState(false);
  const [iteration, setIteration] = useState(0);

  // Spintax Resolver: {opt1|opt2|opt3}
  const resolveSpintax = (text: string) => {
    let resolved = text;
    const spintaxRegex = /\{([^{}]+)\}/g;
    resolved = resolved.replace(spintaxRegex, (_, choices) => {
      const options = choices.split('|');
      return options[Math.floor(Math.random() * options.length)];
    });

    // Replace place tags
    resolved = resolved
      .replace(/\{name\}/gi, sampleLead.name || 'Yetkili')
      .replace(/\{city\}/gi, sampleLead.city || 'İstanbul')
      .replace(/\{district\}/gi, sampleLead.district || 'Merkez')
      .replace(/\{category\}/gi, sampleLead.category || 'İşletme')
      .replace(/\{rating\}/gi, String(sampleLead.rating || 5.0));

    return resolved;
  };

  const previewText = React.useMemo(() => {
    return resolveSpintax(template || 'Merhaba {name} yetkilisi, {city} {district} lokasyonundaki {category} profilinizi inceledik.');
  }, [template, iteration, sampleLead]);

  const handleCopy = () => {
    navigator.clipboard.writeText(previewText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Card className={cn('p-4 sm:p-5 space-y-3.5 bg-gradient-to-br from-slate-50 to-indigo-50/20 dark:from-[#25293C] dark:to-indigo-950/10 border border-indigo-100/60 dark:border-indigo-500/20', className)}>
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Sparkles className="w-4 h-4 text-[#7367F0]" />
          <h4 className="text-xs font-extrabold text-slate-800 dark:text-white uppercase tracking-wider">
            Spintax Canlı Önizleme
          </h4>
        </div>

        <div className="flex items-center space-x-1">
          <IconButton
            icon={RefreshCw}
            size="sm"
            variant="ghost"
            tooltip="Farklı Varyasyon Üret"
            onClick={() => setIteration((i) => i + 1)}
          />
          <IconButton
            icon={copied ? Check : Copy}
            size="sm"
            variant={copied ? 'success' : 'ghost'}
            tooltip={copied ? 'Kopyalandı' : 'Metni Kopyala'}
            onClick={handleCopy}
          />
        </div>
      </div>

      {/* WhatsApp Message Balloon Preview */}
      <div className="p-3.5 rounded-xl bg-white dark:bg-[#2F3349] border border-slate-200/80 dark:border-white/[0.08] shadow-sm relative text-xs text-slate-700 dark:text-slate-200 whitespace-pre-wrap font-sans leading-relaxed">
        {previewText}
      </div>

      <div className="flex items-center justify-between text-[10px] text-slate-400 font-medium">
        <span>Örnek Veri: {sampleLead.name} ({sampleLead.district})</span>
        <span>Varyasyon: #{iteration + 1}</span>
      </div>
    </Card>
  );
};
