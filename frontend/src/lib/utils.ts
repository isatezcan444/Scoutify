import * as React from "react";
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Safely renders an icon prop that could be either a rendered ReactNode (like `<Sun />`)
 * or a component definition (function / forwardRef object from Lucide React).
 */
export function renderIcon(
  icon: any,
  defaultClassName: string = "w-4 h-4"
): React.ReactNode {
  if (!icon) return null;
  if (React.isValidElement(icon)) {
    return icon;
  }
  if (typeof icon === "function" || (typeof icon === "object" && icon !== null && "$$typeof" in icon)) {
    return React.createElement(icon, { className: defaultClassName });
  }
  return icon;
}

/**
 * Normalizes text for case-insensitive and Turkish diacritic-insensitive search.
 * Handles 'i' <-> 'İ', 'ı' <-> 'I', 'ş' <-> 's', 'ç' <-> 'c', 'ğ' <-> 'g', 'ü' <-> 'u', 'ö' <-> 'o'.
 */
export function normalizeTurkishText(text: string): string {
  if (!text) return '';
  return text
    .replace(/İ/g, 'i')
    .replace(/I/g, 'ı')
    .replace(/Ğ/g, 'ğ')
    .replace(/Ü/g, 'ü')
    .replace(/Ö/g, 'ö')
    .replace(/Ş/g, 'ş')
    .replace(/Ç/g, 'ç')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/ı/g, 'i');
}

/**
 * Returns true if target text matches search query regardless of casing or Turkish characters.
 */
export function matchTurkishSearch(target: string | undefined | null, search: string): boolean {
  if (!target || !search) return false;
  return normalizeTurkishText(target).includes(normalizeTurkishText(search));
}
