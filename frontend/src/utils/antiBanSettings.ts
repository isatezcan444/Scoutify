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
    workingHoursStart: '09:30',
    workingHoursEnd: '18:30',
  },
  // Standard Balanced (Recommended Default): Zero-ban algorithm compliance
  standard_balanced: {
    minDelaySeconds: 45,
    maxDelaySeconds: 120,
    typingDelaySeconds: 4,
    dailyMessageLimit: 50,
    workingHoursEnabled: true,
    workingHoursStart: '09:00',
    workingHoursEnd: '19:00',
  },
  // Fast: Only for heavily warmed-up and established WhatsApp Business numbers (> 6 months)
  fast_warmed: {
    minDelaySeconds: 20,
    maxDelaySeconds: 60,
    typingDelaySeconds: 2,
    dailyMessageLimit: 100,
    workingHoursEnabled: true,
    workingHoursStart: '09:00',
    workingHoursEnd: '20:00',
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
      return { ...DEFAULT_ANTI_BAN_CONFIG, ...JSON.parse(saved) };
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
  level: 'safe' | 'moderate' | 'high';
  title: string;
  desc: string;
  color: string;
} => {
  if (minDelay < 20 || dailyLimit > 120) {
    return {
      level: 'high',
      title: '⚠️ Yüksek Ban Riski',
      desc: 'Çok kısa gecikmeler veya yüksek günlük limitler WhatsApp spam tespit algoritmalarını tetikleyebilir.',
      color: '#EA5455'
    };
  }
  if (minDelay < 40 || dailyLimit > 70) {
    return {
      level: 'moderate',
      title: '⚡ Orta Düzey Risk (Isınmış Hatlar)',
      desc: 'Bu ayar yalnızca en az 3-6 aydır aktif kullanılan ve ısınmış WhatsApp hesapları için uygundur.',
      color: '#FF9F43'
    };
  }
  return {
    level: 'safe',
    title: '🛡️ Maksimum Ban Koruması (Önerilen)',
    desc: 'Gaussian Jitter ve doğal insan bekleme süreleriyle WhatsApp algoritmalarına %100 uyumludur.',
    color: '#28C76F'
  };
};
