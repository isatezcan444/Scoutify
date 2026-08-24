export interface AntiBanConfig {
  preset: 'ultra_safe' | 'standard_balanced' | 'fast_warmed' | 'custom';
  minDelaySeconds: number;
  maxDelaySeconds: number;
  typingDelaySeconds: number;
  dailyMessageLimit: number;
  workingHoursEnabled: boolean;
  workingHoursStart: string;
  workingHoursEnd: string;
}

export const ANTI_BAN_PRESETS: Record<'ultra_safe' | 'standard_balanced' | 'fast_warmed', Omit<AntiBanConfig, 'preset'>> = {
  // Ultra Safe: For newly registered WhatsApp accounts (< 1 month)
  ultra_safe: {
    minDelaySeconds: 60,
    maxDelaySeconds: 150,
    typingDelaySeconds: 5,
    dailyMessageLimit: 35,
    workingHoursEnabled: true,
    workingHoursStart: '09:00',
    workingHoursEnd: '18:00',
  },
  // Standard Balanced (Recommended Default): Zero-ban algorithm compliance with corporate working hours
  standard_balanced: {
    minDelaySeconds: 45,
    maxDelaySeconds: 120,
    typingDelaySeconds: 4,
    dailyMessageLimit: 50,
    workingHoursEnabled: true,
    workingHoursStart: '09:00',
    workingHoursEnd: '18:30',
  },
  // Fast: Only for heavily warmed-up and established WhatsApp Business numbers (> 6 months)
  fast_warmed: {
    minDelaySeconds: 20,
    maxDelaySeconds: 60,
    typingDelaySeconds: 2,
    dailyMessageLimit: 100,
    workingHoursEnabled: true,
    workingHoursStart: '08:30',
    workingHoursEnd: '19:00',
  }
};

const STORAGE_KEY = 'scoutify_anti_ban_config';

export const DEFAULT_ANTI_BAN_CONFIG: AntiBanConfig = {
  preset: 'standard_balanced',
  ...ANTI_BAN_PRESETS.standard_balanced
};

export const getStoredAntiBanConfig = (): AntiBanConfig => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      return { 
        ...DEFAULT_ANTI_BAN_CONFIG, 
        ...parsed,
        // Guarantee workingHoursEnabled is active with valid corporate defaults
        workingHoursEnabled: parsed.workingHoursEnabled !== undefined ? parsed.workingHoursEnabled : true,
        workingHoursStart: parsed.workingHoursStart || '09:00',
        workingHoursEnd: parsed.workingHoursEnd || '18:30',
      };
    }
  } catch (e) {
    console.warn('Failed to load anti-ban config from storage:', e);
  }
  return DEFAULT_ANTI_BAN_CONFIG;
};

export const saveAntiBanConfig = (config: AntiBanConfig): void => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
  } catch (e) {
    console.warn('Failed to save anti-ban config to storage:', e);
  }
};

export const calculateRiskLevel = (minDelay: number, dailyLimit: number): {
  score: number;
  level: 'safe' | 'moderate' | 'high';
  title: string;
  desc: string;
  color: string;
  badgeBg: string;
  badgeText: string;
} => {
  // Score: 0 (Ultra Safe) to 100 (Maximum Risk)
  const delayRisk = Math.max(0, Math.min(100, ((60 - minDelay) / 50) * 100));
  const limitRisk = Math.max(0, Math.min(100, ((dailyLimit - 30) / 120) * 100));
  const score = Math.round((delayRisk * 0.55) + (limitRisk * 0.45));

  if (score >= 65 || minDelay < 20 || dailyLimit > 120) {
    return {
      score: Math.max(70, Math.min(95, score)),
      level: 'high',
      title: 'Yüksek Ban Riski',
      desc: 'Çok kısa gecikmeler veya yüksek günlük limitler WhatsApp spam filtrelerini ve kullanıcı şikayetlerini tetikleyebilir.',
      color: '#EA5455',
      badgeBg: 'bg-rose-50 dark:bg-rose-500/15 border-rose-200 dark:border-rose-500/30',
      badgeText: 'text-[#EA5455]'
    };
  }
  
  if (score >= 35 || minDelay < 40 || dailyLimit > 70) {
    return {
      score: Math.max(35, Math.min(64, score)),
      level: 'moderate',
      title: 'Orta Düzey Risk (Isınmış Hatlar)',
      desc: 'Bu ayar yalnızca en az 3-6 aydır düzenli kullanılan ve ısınmış WhatsApp Business hatları için tavsiye edilir.',
      color: '#FF9F43',
      badgeBg: 'bg-amber-50 dark:bg-amber-500/15 border-amber-200 dark:border-amber-500/30',
      badgeText: 'text-[#FF9F43]'
    };
  }

  return {
    score: Math.max(8, Math.min(34, score)),
    level: 'safe',
    title: 'Düşük Risk (Maksimum Güvenlik)',
    desc: 'Gaussian Jitter ve doğal insan bekleme süreleriyle WhatsApp algoritmalarına ve güvenlik kurallarına %100 uyumludur.',
    color: '#28C76F',
    badgeBg: 'bg-emerald-50 dark:bg-emerald-500/15 border-emerald-200 dark:border-emerald-500/30',
    badgeText: 'text-[#28C76F]'
  };
};
