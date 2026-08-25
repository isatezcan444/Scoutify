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
