import React from 'react';
import { LucideIcon, Sparkles } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface HeroBannerProps {
  badgeText?: string;
  badgeIcon?: LucideIcon;
  title: string;
  subtitle: string;
  actions?: React.ReactNode;
  className?: string;
}

export const HeroBanner: React.FC<HeroBannerProps> = ({
  badgeText,
  badgeIcon: BadgeIcon = Sparkles,
  title,
  subtitle,
  actions,
  className,
}) => {
  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-2xl bg-gradient-to-r from-[#7367F0] via-[#867BFF] to-[#9E95F5] text-white p-5 sm:p-7 shadow-lg shadow-[#7367F0]/15 select-none animate-fade-in',
        className
      )}
    >
      <div className="relative z-10 max-w-2xl">
        {badgeText && (
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-lg bg-white/20 text-white text-xs font-extrabold mb-3 backdrop-blur-md border border-white/20 shadow-sm">
            <BadgeIcon className="w-3.5 h-3.5 text-amber-300" />
            <span>{badgeText}</span>
          </div>
        )}
        <h2 className="text-lg sm:text-xl md:text-2xl font-extrabold text-white tracking-tight leading-snug">
          {title}
        </h2>
        <p className="mt-2 text-xs md:text-sm text-white/90 leading-relaxed font-medium">
          {subtitle}
        </p>

        {actions && (
          <div className="mt-5 flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 sm:gap-3">
            {actions}
          </div>
        )}
      </div>

      {/* Decorative Blur Spheres */}
      <div className="absolute right-0 top-0 bottom-0 w-80 bg-white/10 rounded-full blur-3xl pointer-events-none transform translate-x-1/3" />
      <div className="absolute -left-10 -bottom-10 w-48 h-48 bg-purple-900/20 rounded-full blur-2xl pointer-events-none" />
    </div>
  );
};
