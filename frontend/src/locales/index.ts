import { en } from './en';
import { tr } from './tr';

export type Language = 'en' | 'tr';

export const translations = {
  en,
  tr,
};

export type Translations = typeof en;
