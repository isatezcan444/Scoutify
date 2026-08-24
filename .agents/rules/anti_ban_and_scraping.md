# Anti-Ban Engine & Scraping Rules

## 1. Anti-Ban Engine
- **Jitter**: Must use Gaussian distribution clamped strictly between `min_delay_seconds` and `max_delay_seconds`.
- **Working Hours**: Fail-closed validation. Messages must never dispatch outside permitted corporate hours.
- **Warm-Up Schedules**:
  - Day 1-3: 15-20 msg/day
  - Day 4-7: 30-40 msg/day
  - Day 8+: 50-100 msg/day
- **Opt-Out keywords**: Immediate blacklist tagging on inbound reply matches (`\b(istemiyorum|iptal|sil|stop|unsubscribe)\b`).

## 2. Lead Discovery ("İşletme Ara")
- Multi-district scope: Expanding across district arrays sequentially with satellite-tuner dynamic streaming.
- Deterministic place_id: `gmaps_{sha256(url)[:16]}`.
- Telephoneless entries: Set `phone_e164 = None` and `is_whatsapp_eligible = False`.
- Ingestion pipeline: Uses `LeadIngestService` with deduplication and normalization.
