# Scoutify - AI Agent Development & System Rules

Scoutify is an AI-assisted, production-grade B2B Lead Generation & Automated WhatsApp Outreach Platform.
This document defines the core architecture, non-negotiable rules, invariants, and guidelines for any AI agent or engineer extending the codebase.

---

## 1. Core Architectural Invariants

### 1.1 Truthfulness & WhatsApp Simulation Layer
- **No False Positives**: Never mask exceptions or failures as `{"success": True}`. If an outreach fails or gateway is unreachable, it MUST be reported as failed (`success: False`, `MessageStatus.FAILED`).
- **SimulatedSender vs GatewaySender**:
  - `settings.SIMULATION_MODE = True` -> Uses `SimulatedSender`. Dispatches are explicitly marked with `is_simulated: True` and labeled as DEMO.
  - `settings.SIMULATION_MODE = False` -> Uses `GatewaySender` calling `wa-gateway`.
- All message dispatching goes through the `WhatsAppSender` protocol.

### 1.2 Single Source of Truth for Anti-Ban Policy
- All jitter delays, mesai (working hours) limits, and humanized delays MUST be resolved via `AntibanPolicy`.
- Working hours validation is **FAIL-CLOSED** (`is_within_working_hours` returns `False` if parsing fails).
- Anti-Ban settings are persisted in the database via `/api/v1/settings/antiban` and synced to the UI.

### 1.3 Data Integrity & Phone Numbers
- `Lead.phone_e164` is **nullable**. Never synthesize fake phone numbers (`+90000...`) for places without a phone number.
- Places without a phone number are saved with `phone_e164 = None` and `is_whatsapp_eligible = False`.
- `place_id` must use deterministic hashing: `hashlib.sha256(url.encode()).hexdigest()[:16]` (never process-local `hash()`).
- Ingestion and deduplication are handled centrally by `LeadIngestService`.

### 1.4 Scraper Pipeline Integrity ("İşletme Ara")
- The Google Maps / Places scraper with Playwright and streaming HTTP extraction must NEVER be degraded.
- Multi-district expansion, satellite-tuner dynamic streaming, and real-time WebSocket progress broadcasts (`scraper_progress`, `scraper_completed`) must be preserved.
- Scraper concurrency is bounded by `settings.SCRAPER_MAX_CONCURRENT_TASKS` via semaphore.

---

## 2. Backend Coding Standards

- **Language & Framework**: Python 3.12+, FastAPI, SQLAlchemy 2.0 (AsyncIO), Pydantic v2.
- **Strict Typing**: All service methods and endpoints must have complete type hints.
- **Thin Routers / Fat Services (SRP)**: Endpoints in `backend/app/api/v1/endpoints/` handle HTTP validation, query parsing, and delegating to domain services (`LeadIngestService`, `CampaignRunner`, `OutreachManager`, `ExportService`).
- **Security**:
  - Webhooks require `X-Webhook-Secret` verification matching `settings.WA_GATEWAY_WEBHOOK_SECRET`.
  - CORS origins are loaded from `settings.BACKEND_CORS_ORIGINS`.
  - Opt-out detection uses regex word-boundaries (`\b(istemiyorum|iptal|sil|stop|unsubscribe)\b`).

---

## 3. Frontend Standards (Vuexy Design System)

- **Framework**: React 18, TypeScript, Vite, Tailwind CSS.
- **UI Aesthetic**: Rich, modern Vuexy theme with glassmorphism card surfaces, dark mode support, and vibrant badges.
- **Modal & Dialog Stacking**:
  - Full-screen fixed modals must be portaled to `document.body` via `createPortal(..., document.body)` with `z-[99999]`.
  - Native `window.alert()` and `window.confirm()` are strictly forbidden. Always use `useToast()` (`toast.success`, `toast.error`, `await toast.confirm(...)`).
- **Performance & Responsiveness**:
  - Search inputs must use debouncing (e.g. 300ms) to avoid request storms and race conditions.
  - File exports must check `res.ok` and revoke blob URLs (`window.URL.revokeObjectURL`).
  - Base URLs must respect `import.meta.env.VITE_API_URL`.

---

## 4. Test Discipline

- All backend changes must be verified against pytest:
  ```bash
  source venv/bin/activate && PYTHONPATH=. pytest backend/tests/ -v
  ```
- All frontend changes must pass TypeScript compilation and build:
  ```bash
  cd frontend && npm run build
  ```
