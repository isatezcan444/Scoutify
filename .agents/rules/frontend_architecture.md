# Frontend Architecture & UI Rules

## 1. Design System (Vuexy Aesthetic)
- Colors: Primary indigo (`#7367F0`), Success green (`#28C76F`), Warning orange (`#FF9F43`), Danger red (`#EA5455`), Info blue (`#00CFE8`).
- Dark mode support is mandatory across all cards, modals, popovers, and tables (`dark:bg-[#2F3349]`, `dark:border-[#434968]`).

## 2. Modal Portaling & Dialogs
- All full-screen overlay modals must be rendered via `createPortal(modalJSX, document.body)`.
- Modals must use `z-[99999]` and avoid nested stacking blur collisions.
- No native `alert()` or `confirm()`. All user notifications and confirmation dialogs must use `ToastContext` (`useToast()`).

## 3. Asynchronous Data Handling
- Search inputs must debounce by 300ms.
- Always handle loading, error, and empty states cleanly.
- Keep table selection logic (Gmail-style select page vs select all matching) in sync with backend filtering parameters.
