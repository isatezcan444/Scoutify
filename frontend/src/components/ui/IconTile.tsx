import React from 'react';
import { LucideIcon } from 'lucide-react';
import { cn } from '../../lib/utils';
import { toneSoftVariants, ToneVariantProps } from '../../lib/designTokens';

/**
 * Vuexy icon tile — the single scale for rounded icon containers.
 *
 * size  → box + radius pairing (kept in one place so tiles never diverge):
 *   sm = w-9  h-9  rounded-lg    (page headers, inline rows)
 *   md = w-11 h-11 rounded-xl    (stat cards, modal headers)
 *   lg = w-14 h-14 rounded-2xl   (empty states, hero illustrations)
 */
export type IconTileSize = 'sm' | 'md' | 'lg';

const sizeStyles: Record<IconTileSize, { box: string; icon: string; stroke?: number }> = {
  sm: { box: 'w-9 h-9 rounded-lg', icon: 'w-5 h-5' },
  md: { box: 'w-11 h-11 rounded-xl', icon: 'w-5 h-5', stroke: 2.2 },
  lg: { box: 'w-14 h-14 rounded-2xl', icon: 'w-7 h-7', stroke: 1.8 },
};

export interface IconTileProps extends ToneVariantProps {
  icon: LucideIcon | React.ComponentType<{ className?: string }>;
  size?: IconTileSize;
  className?: string;
}

export const IconTile: React.FC<IconTileProps> = ({
  icon: Icon,
  size = 'md',
  tone = 'primary',
  className,
}) => {
  const currentSize = sizeStyles[size];
  return (
    <div
      className={cn(
        'flex items-center justify-center shrink-0',
        currentSize.box,
        toneSoftVariants({ tone }),
        className
      )}
    >
      <Icon className={cn(currentSize.icon)} strokeWidth={currentSize.stroke} />
    </div>
  );
};
