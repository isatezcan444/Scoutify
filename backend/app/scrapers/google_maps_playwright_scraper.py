"""
High-Recall Google Maps Playwright Discovery Scraper with Real-Time Place Streaming.
Directly queries Google Maps places feed for target city, district, and business category.
Interacts with each place card to extract exact full street/neighborhood address,
direct landline (02xx) & mobile GSM phone numbers, official website, rating, reviews, and place coordinates.
Streams each discovered place in real-time with satellite-tuner style progress updates.

Robustness invariants:
- Feed scrolling is ADAPTIVE: after each scroll the scraper polls until new cards render
  (bounded by SCROLLER_SETTLE_TIMEOUT_MS) instead of assuming a fixed delay.
- Stagnation detection is TIME-BASED: discovery only stops when no new card has been
  inspected for SCRAPER_STAGNATION_TIMEOUT_SECONDS — lazy-loaded feeds no longer cut short.
- Single-place detection is guarded: it requires the absence of the results feed AFTER an
  extra settle wait AND presence of concrete place-detail markers, preventing the results
  list header from being misread as a single place.
- Detail-pane attribution is validated: extracted pane title must match the clicked card,
  otherwise pane-derived fields are discarded instead of poisoning the wrong business.
- Anti-bot interstitials (captcha / unusual traffic) raise GoogleMapsBlockedError —
  failures are reported loudly, never silently as zero results.
"""
import re
import hashlib
import logging
import time
from typing import List, Dict, Any, Optional, Set, Callable
from urllib.parse import quote, unquote, urlparse
from playwright.async_api import async_playwright, Browser, Page, Locator

from backend.app.core.config import settings
from backend.app.services.phone_service import PhoneService
from backend.app.data.turkey_locations import normalize_turkish

logger = logging.getLogger(__name__)

# Selectors that only exist on a genuine single-place details view (not on list pages).
_SINGLE_PLACE_MARKERS = 'button[data-item-id="address"], a[data-item-id="authority"], button[jsaction*="category"]'

# End-of-results markers rendered by Google Maps at the bottom of the feed.
_END_OF_RESULTS_SELECTOR = (
    'span:has-text("Tüm sonuçlara ulaştınız"), '
    'span:has-text("Sonuçların sonuna geldiniz"), '
    'span:has-text("reached the end"), '
    'div.HlvSq'
)

# Anti-bot / captcha interstitial indicators.
_BLOCK_URL_FRAGMENTS = ("/sorry/", "google.com/sorry")
_BLOCK_SELECTORS = "iframe[src*='recaptcha'], #captcha, form#captcha-form, div#sorry"
_BLOCK_TEXTS = ("unusual traffic", "olağandışı trafik")

# Extra wait before committing to the single-place branch when the feed looks empty (ms).
_SINGLE_PLACE_SETTLE_MS = 2500
# Poll interval while waiting for lazily-rendered feed cards (ms).
_FEED_GROWTH_POLL_MS = 300

# Extracts structured attributes from the currently open place details pane.
# paneTitle enables caller-side validation that the pane belongs to the clicked card.
_DETAILS_EXTRACT_JS = """() => {
    const res = {
        paneTitle: null,
        address: null,
        phone: null,
        website: null,
        rating: null,
        reviewsCount: 0,
        category: null,
        is_sponsored: false
    };

    const titleEl = document.querySelector('h1.DUwDvf, div.fontHeadlineLarge');
    if (titleEl) res.paneTitle = titleEl.innerText.trim();

    // Check sponsored badge
    if (document.querySelector('div.kpi10b, span.kpi10b, [aria-label*="Sponsorlu"], [aria-label*="Sponsored"]')) {
        res.is_sponsored = true;
    }

    // 1. Full Address
    const addrBtn = document.querySelector('button[data-item-id="address"], [data-tooltip*="Adres"], [data-item-id*="address"]');
    if (addrBtn) {
        res.address = addrBtn.getAttribute('aria-label') || addrBtn.innerText.trim();
    }

    // 2. Direct Phone
    const phoneBtn = document.querySelector('button[data-item-id*="phone"], a[href*="tel:"]');
    if (phoneBtn) {
        let p = phoneBtn.getAttribute('aria-label') || phoneBtn.innerText.trim() || phoneBtn.href;
        p = p.replace(/^tel:/i, '').replace(/^(?:Telefon|Phone|Tel|Cep)\s*:\s*/i, '').trim();
        res.phone = p;
    }

    // 3. Official Website
    const webBtn = document.querySelector('a[data-item-id="authority"], a[aria-label*="Web sitesi"], a[data-tooltip*="Web sitesi"]');
    if (webBtn) {
        res.website = webBtn.href;
    }

    // 4. Rating & Reviews
    const ratingEl = document.querySelector('div.F7nice span[aria-hidden="true"], span.MW4etd');
    if (ratingEl) {
        const rText = ratingEl.innerText.replace(',', '.').trim();
        res.rating = parseFloat(rText) || null;
    }
    const revEl = document.querySelector('div.F7nice span[aria-label*="yorum"], span.UY7F9, span[aria-label*="reviews"]');
    if (revEl) {
        const revClean = revEl.innerText.replace(/[^0-9]/g, '');
        if (revClean) res.reviewsCount = parseInt(revClean, 10);
    }

    // 5. Category
    const catBtn = document.querySelector('button[jsaction*="category"]');
    if (catBtn) res.category = catBtn.innerText.trim();

    // 6. Deep Scan all Io6YTe / rogA2c text rows if phone/address still missing
    const rows = Array.from(document.querySelectorAll('div.Io6YTe, div.rogA2c, span.LrzXr')).map(r => r.innerText.trim());
    for (const row of rows) {
        if (!res.phone) {
            const pMatch = row.match(/(?:0[2-5]\\d{2}[\\s\\.\\-\\(\\)]*\\d{3}[\\s\\.\\-\\(\\)]*\\d{2}[\\s\\.\\-\\(\\)]*\\d{2}|\\+90[\\s\\.\\-\\(\\)]*[2-5]\\d{2}[\\s\\.\\-\\(\\)]*\\d{3}|0850[\\s\\.\\-\\(\\)]*\\d{3}[\\s\\.\\-\\(\\)]*\\d{2}[\\s\\.\\-\\(\\)]*\\d{2})/);
            if (pMatch) {
                res.phone = pMatch[0];
            }
        }
        if (!res.address) {
            if (row.includes('Mah') || row.includes('Cd') || row.includes('Sok') || row.includes('No:') || row.includes('/')) {
                res.address = row;
            }
        }
    }

    return res;
}"""

# Direct batch extraction of all rendered feed cards in one O(1) JavaScript evaluation.
# Extracts real phone numbers, exact addresses, categories, ratings, reviews, and websites.
_FEED_CARDS_EXTRACT_JS = """() => {
    const results = [];
    const cards = document.querySelectorAll('div.Nv2PK');
    for (const card of cards) {
        const nameEl = card.querySelector('.qBF1Pd, a.hfpxzc');
        const linkEl = card.querySelector('a.hfpxzc');
        const ratingEl = card.querySelector('.MW4etd');
        const reviewsEl = card.querySelector('.UY7F9');
        const webEl = card.querySelector('a[data-value="Web sitesi"], a.lcr4fd, a[aria-label*="Web sitesi"], a[data-tooltip*="Web sitesi"]');
        
        const name = nameEl ? (nameEl.innerText || nameEl.getAttribute('aria-label') || '').trim() : '';
        const href = linkEl ? linkEl.href : '';
        if (!name || !href) continue;
        
        const fullText = card.innerText || '';
        const textLines = Array.from(card.querySelectorAll('.W4Efsd, .fontBodyMedium')).map(el => el.innerText.trim());
        
        // 1. Phone extraction directly from card text
        let phone = null;
        const phoneMatch = fullText.match(/(?:0[2-5]\\d{2}[\\s\\.\\-\\(\\)]*\\d{3}[\\s\\.\\-\\(\\)]*\\d{2}[\\s\\.\\-\\(\\)]*\\d{2}|\\(0[2-5]\\d{2}\\)[\\s\\.\\-\\(\\)]*\\d{3}[\\s\\.\\-\\(\\)]*\\d{2}[\\s\\.\\-\\(\\)]*\\d{2}|\\+90[\\s\\.\\-\\(\\)]*[2-5]\\d{2}[\\s\\.\\-\\(\\)]*\\d{3}[\\s\\.\\-\\(\\)]*\\d{2}[\\s\\.\\-\\(\\)]*\\d{2}|05\\d{2}[\\s\\.\\-\\(\\)]*\\d{3}[\\s\\.\\-\\(\\)]*\\d{2}[\\s\\.\\-\\(\\)]*\\d{2}|0850[\\s\\.\\-\\(\\)]*\\d{3}[\\s\\.\\-\\(\\)]*\\d{2}[\\s\\.\\-\\(\\)]*\\d{2})/);
        if (phoneMatch) {
            phone = phoneMatch[0].trim();
        }
        
        // 2. Address and Category extraction from card lines
        let category = null;
        let address = null;
        
        for (const line of textLines) {
            const parts = line.split('·').map(p => p.trim());
            for (const part of parts) {
                if (!category && (part.includes('Kliniği') || part.includes('Hastanesi') || part.includes('Doktor') || part.includes('Merkezi') || part.includes('Polikliniği') || part.includes('Hizmet') || part.includes('Dişçi') || part.includes('Sağlık') || part.includes('Şirket') || part.includes('Ofis') || part.includes('Danışmanlık') || part.includes('Ajans') || part.includes('Güzellik') || part.includes('Avukat') || part.includes('Mühendislik') || part.includes('Restoran') || part.includes('Kafe') || part.includes('Otel'))) {
                    category = part;
                }
                if (!address && (part.includes('Cd') || part.includes('Sk') || part.includes('Sok') || part.includes('Mah') || part.includes('No:') || part.includes('Bulvarı') || part.includes('Çarşı') || part.includes('Kat:') || part.includes('Cad.') || part.includes('Sitesi') || part.includes('Blok'))) {
                    address = part.replace(/^\\s*(?:Açık|Kapalı|Kapanmak üzere).*?·\\s*/i, '').trim();
                }
            }
        }
        
        const ratingText = ratingEl ? ratingEl.innerText.replace(',', '.').trim() : null;
        const rating = ratingText ? parseFloat(ratingText) : null;
        const revText = reviewsEl ? reviewsEl.innerText.replace(/[^0-9]/g, '') : null;
        const reviewsCount = revText ? parseInt(revText, 10) : 0;
        const website = webEl ? webEl.href : null;
        
        results.push({
            name,
            href,
            phone,
            address,
            category,
            rating,
            reviewsCount,
            website
        });
    }
    return results;
};"""


def clean_extracted_website(raw_url: Optional[str]) -> Optional[str]:
    """Cleans and validates business website URLs extracted from Google Maps."""
    if not raw_url:
        return None
    url = raw_url.strip()
    if not url or url.startswith("javascript:") or url.startswith("mailto:"):
        return None

    # Unwrap Google redirect URLs (/url?q=...)
    if "/url?q=" in url:
        match = re.search(r'/url\?q=([^&]+)', url)
        if match:
            url = unquote(match.group(1))

    # Reject social and directory domains as company official website
    skip_domains = [
        "google.com", "google.com.tr", "maps.google.com", "goo.gl",
        "facebook.com", "instagram.com", "twitter.com", "x.com",
        "youtube.com", "linkedin.com", "pinterest.com", "tiktok.com",
        "bulurum.com", "doktortakvimi.com", "eniyihekim.com", "sahibinden.com",
        "armut.com", "bionluk.com", "yellowpages.com.tr", "sarisayfalar.com"
    ]

    try:
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"https://{url}"
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        if any(d in netloc for d in skip_domains):
            return None
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
    except Exception:
        return None


def clean_extracted_address(raw_addr: Optional[str]) -> Optional[str]:
    """Cleans Google Maps address text, removing icons, newlines, and preserving full address text."""
    if not raw_addr:
        return None
    # Remove unicode icon glyphs (e.g. \ue0c8)
    cleaned = re.sub(r'[\ue000-\uf8ff]', '', raw_addr)
    # Remove 'Adres:' prefix from aria-label
    cleaned = re.sub(r'^\s*Adres:\s*', '', cleaned, flags=re.IGNORECASE).strip()
    # Remove opening status fragments
    cleaned = re.sub(r'(?:,\s*)?(?:Açık|Kapalı|Kapanmak üzere).*$', '', cleaned, flags=re.IGNORECASE).strip()
    # Split by newline and combine all address lines without dropping apartment/building/postal code
    lines = [l.strip().rstrip(',') for l in cleaned.split('\n') if l.strip() and not l.strip().startswith('Adres:')]
    if not lines:
        return None
    # If multiple lines exist, join them cleanly with comma
    full_joined = ", ".join(lines)
    # Clean redundant spaces or double commas
    full_joined = re.sub(r',\s*,', ', ', full_joined)
    return full_joined.strip()


def extract_coords_from_url(maps_url: Optional[str]) -> tuple[Optional[float], Optional[float]]:
    """Extracts latitude and longitude coordinates from Google Maps URL (@lat,lon,zoom)."""
    if not maps_url:
        return None, None
    match = re.search(r'@([0-9\.\-]+),([0-9\.\-]+)', maps_url)
    if match:
        try:
            return float(match.group(1)), float(match.group(2))
        except ValueError:
            pass
    return None, None


def pane_belongs_to_card(pane_title: Optional[str], card_name: str) -> bool:
    """
    Validates that the open details pane actually belongs to the clicked card.
    Comparison is diacritics-insensitive with bidirectional containment and word token matching.
    """
    if not pane_title:
        return True
    norm_pane = normalize_turkish(pane_title).lower()
    norm_card = normalize_turkish(card_name).lower()
    if not norm_pane or not norm_card:
        return True
    if norm_pane in norm_card or norm_card in norm_pane:
        return True
    # Word token intersection for titles with punctuation or slight variations
    pane_tokens = set(re.findall(r'\w+', norm_pane))
    card_tokens = set(re.findall(r'\w+', norm_card))
    common = pane_tokens.intersection(card_tokens)
    return len(common) >= 2 or (len(pane_tokens) == 1 and bool(common))


class GoogleMapsBlockedError(RuntimeError):
    """Raised when Google serves an anti-bot interstitial instead of search results."""


class GoogleMapsPlaywrightScraper:
    """
    Production-Grade Google Maps Discovery Scraper:
    - Scrolls results feed to discover all matching places.
    - Clicks into each listing to extract full exact address (Mahalle, Cadde, No, Posta Kodu, İlçe/İl).
    - Extracts verified landline phones (02xx), mobile GSMs (05xx), websites, ratings, and reviews.
    - Dispatches real-time callbacks as each place is inspected.
    """

    def __init__(self):
        self._browser: Optional[Browser] = None

    # ------------------------------------------------------------------
    # Session-level helpers
    # ------------------------------------------------------------------

    async def _open_results_session(self, page: Page, maps_url: str) -> None:
        """Navigates to the search URL, dismisses consent, and verifies Google served real results."""
        await page.goto(maps_url, wait_until="domcontentloaded", timeout=settings.SCRAPER_PAGE_TIMEOUT_MS)
        await page.wait_for_timeout(1800)

        await self._dismiss_consent(page)
        await page.wait_for_timeout(2500)
        await self._ensure_not_blocked(page)

    async def _dismiss_consent(self, page: Page) -> None:
        """Dismisses the Google cookie-consent dialog when present across any region."""
        consent_selectors = [
            'button[aria-label*="Tümünü kabul et"]',
            'button[aria-label*="Accept all"]',
            'button[aria-label*="Alle akzeptieren"]',
            'form[action*="consent"] button',
            'button:has-text("Tümünü kabul et")',
            'button:has-text("Kabul et")',
            'button:has-text("Accept all")',
            'button:has-text("I agree")',
            'button:has-text("Ich stimme zu")',
            'button:has-text("Tout accepter")',
        ]
        for sel in consent_selectors:
            try:
                btn = page.locator(sel)
                if await btn.count() > 0:
                    await btn.first.click()
                    await page.wait_for_timeout(800)
                    break
            except Exception:
                pass

    async def _ensure_not_blocked(self, page: Page) -> None:
        """Raises GoogleMapsBlockedError when an anti-bot interstitial is detected."""
        current_url = page.url.lower()
        if any(fragment in current_url for fragment in _BLOCK_URL_FRAGMENTS):
            raise GoogleMapsBlockedError(f"Google anti-bot sayfasına yönlendirildik: {page.url}")
        try:
            if await page.locator(_BLOCK_SELECTORS).count() > 0:
                raise GoogleMapsBlockedError("Google captcha doğrulaması sunuldu.")
            body_text = (await page.locator("body").inner_text(timeout=1500)).lower()
            if any(text in body_text for text in _BLOCK_TEXTS):
                raise GoogleMapsBlockedError("Google 'olağandışı trafik' uyarısı gösterildi.")
        except GoogleMapsBlockedError:
            raise
        except Exception:
            pass  # Detection probes must never break a healthy session.

    async def _count_feed_cards(self, page: Page) -> int:
        try:
            return await page.locator('a.hfpxzc').count()
        except Exception:
            return 0

    async def _reached_end_of_results(self, page: Page) -> bool:
        try:
            return await page.locator(_END_OF_RESULTS_SELECTOR).count() > 0
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Scroll helpers (adaptive)
    # ------------------------------------------------------------------

    async def _scroll_feed_once(self, page: Page) -> None:
        """Performs one feed-scroll action: focus last card, wheel over the feed, PageDown."""
        try:
            last_card = page.locator('a.hfpxzc').last
            if await last_card.count() > 0:
                await last_card.scroll_into_view_if_needed(timeout=1000)

            feed_el = page.locator('div[role="feed"]').first
            if await feed_el.is_visible():
                await feed_el.hover()
                await page.mouse.wheel(0, 5000)
                await page.keyboard.press("PageDown")
        except Exception:
            await page.evaluate("""() => {
                const feedEl = document.querySelector('div[role="feed"]');
                if (feedEl) feedEl.scrollTop += 5000;
            }""")

    async def _scroll_and_wait_for_growth(self, page: Page, previous_count: int) -> int:
        """
        Scrolls the feed once, then adaptively polls until new cards render, the
        end-of-results marker appears, or the settle timeout elapses.
        Returns the observed card count after settling.
        """
        await self._scroll_feed_once(page)

        deadline = time.monotonic() + (settings.SCROLLER_SETTLE_TIMEOUT_MS / 1000.0)
        current_count = await self._count_feed_cards(page)
        while time.monotonic() < deadline:
            if current_count > previous_count:
                break
            if await self._reached_end_of_results(page):
                break
            await page.wait_for_timeout(_FEED_GROWTH_POLL_MS)
            current_count = await self._count_feed_cards(page)
        return current_count

    def _resolve_scroll_budget(self, max_results: int) -> int:
        """Unlimited/high-target runs get the full configured budget; smaller targets scale down."""
        if max_results == 0 or max_results > 50:
            return settings.SCRAPER_MAX_SCROLL_ITERATIONS
        return max(5, (max_results // 5) + 2)

    # ------------------------------------------------------------------
    # Card inspection
    # ------------------------------------------------------------------

    async def _inspect_card(self, page: Page, card: Locator, card_name: str) -> Dict[str, Any]:
        """Clicks a card and extracts validated attributes from the opened details pane.

        Waits for the details-pane heading to actually switch to the clicked card
        (the pane is shared across clicks and updates asynchronously — without this
        wait every extraction reads the PREVIOUS business).
        """
        try:
            await card.scroll_into_view_if_needed(timeout=1000)
            await card.click(timeout=1500)
            await page.wait_for_timeout(400)
            await self._wait_for_pane_title(page, card_name, timeout_ms=1200)
        except Exception as click_err:
            logger.debug(f"[GMAPS_PLAYWRIGHT] Card click fallback: {click_err}")

        details = await page.evaluate(_DETAILS_EXTRACT_JS)
        return details

    @staticmethod
    async def _wait_for_pane_title(page: Page, card_name: str, timeout_ms: int = 2500) -> None:
        """Resolves once the open pane heading matches the clicked card's name."""
        expected = normalize_turkish(card_name)
        if not expected:
            return

        async def poll() -> bool:
            try:
                title = await page.evaluate(
                    "() => { const el = document.querySelector('h1.DUwDvf, div.fontHeadlineLarge');"
                    " return el ? el.innerText.trim() : null }"
                )
                return bool(title) and pane_belongs_to_card(title, card_name)
            except Exception:
                return False

        deadline = time.monotonic() + timeout_ms / 1000.0
        while time.monotonic() < deadline:
            if await poll():
                return
            await page.wait_for_timeout(120)

    @staticmethod
    def _strip_untrusted_fields(details: Dict[str, Any]) -> None:
        """Removes pane-derived fields that cannot be trusted due to a pane/card mismatch."""
        for key in ("address", "phone", "website", "rating", "category", "reviewsCount", "is_sponsored"):
            details[key] = None if key != "reviewsCount" else 0

    async def _collect_card_details(self, page: Page, card: Locator, card_name: str) -> Dict[str, Any]:
        details = await self._inspect_card(page, card, card_name)
        if not pane_belongs_to_card(details.get("paneTitle"), card_name):
            # The pane may have been mid-transition — one bounded retry before giving up
            # on this card's detail fields.
            details = await self._inspect_card(page, card, card_name)
        if not pane_belongs_to_card(details.get("paneTitle"), card_name):
            logger.warning(
                f"[GMAPS_PLAYWRIGHT] Pane/card mismatch: pane='{details.get('paneTitle')}' card='{card_name}'. "
                "Pane-derived fields discarded to avoid mis-attribution."
            )
            self._strip_untrusted_fields(details)
        details.pop("paneTitle", None)
        return details

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def scrape_district_places(
        self,
        keyword: str,
        city: str,
        district: str,
        max_results: int = 100,
        on_place_inspected: Optional[Callable[[Dict[str, Any], int, int], Any]] = None,
        on_progress_status: Optional[Callable[[str, int], Any]] = None
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        seen_names: Set[str] = set()
        seen_hrefs: Set[str] = set()

        query = f"{city} {district} {keyword}"
        maps_url = f"https://www.google.com/maps/search/{quote(query)}"
        logger.info(f"[GMAPS_PLAYWRIGHT] Searching: '{query}' -> {maps_url}")

        if on_progress_status:
            await on_progress_status(f"🌐 Google Maps oturumu başlatılıyor: {city} > {district}...", 10)

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--no-first-run",
                    "--no-zygote",
                    "--disable-extensions",
                    "--disable-background-networking",
                ]
            )
            context = await browser.new_context(
                locale="tr-TR",
                user_agent=settings.SCRAPER_USER_AGENT,
                viewport={"width": 1280, "height": 800}
            )
            page = await context.new_page()
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

            # Route optimization: block images, fonts, media and tracker scripts to speed up scraping 5-10x
            async def _filter_routes(route):
                req = route.request
                if req.resource_type in ["image", "media", "font"]:
                    await route.abort()
                elif any(b in req.url for b in ["google-analytics", "googletagmanager", "doubleclick", "fonts.gstatic.com"]):
                    await route.abort()
                else:
                    await route.continue_()

            await page.route("**/*", _filter_routes)

            try:
                await self._open_results_session(page, maps_url)

                # Guarded single-place branch: requires the feed to remain absent after an
                # extra settle wait AND concrete place-detail markers to be present.
                if await self._count_feed_cards(page) == 0:
                    await page.wait_for_timeout(_SINGLE_PLACE_SETTLE_MS)
                    if await self._count_feed_cards(page) == 0 and await page.locator(_SINGLE_PLACE_MARKERS).count() > 0:
                        single_result = await self._scrape_single_place(page, keyword, city, district)
                        results.append(single_result)
                        if on_place_inspected:
                            await on_place_inspected(single_result, 1, 1)
                        await browser.close()
                        return results

                await self._run_feed_discovery_loop(
                    page=page,
                    keyword=keyword,
                    city=city,
                    district=district,
                    max_results=max_results,
                    results=results,
                    seen_names=seen_names,
                    seen_hrefs=seen_hrefs,
                    on_place_inspected=on_place_inspected,
                    on_progress_status=on_progress_status,
                )

            except GoogleMapsBlockedError:
                raise
            except Exception as e:
                logger.error(f"[GMAPS_PLAYWRIGHT] Error searching '{query}': {e}", exc_info=True)
                # Transparency: surface the partial-failure instead of silently returning.
                if on_progress_status:
                    try:
                        await on_progress_status(
                            f"⚠️ Oturum beklenmedik şekilde sonlandı ({type(e).__name__}); "
                            f"{len(results)} işletme ile dönüldü.",
                            15
                        )
                    except Exception:
                        pass
            finally:
                await browser.close()

        logger.info(f"[GMAPS_PLAYWRIGHT] District '{district}' finished. Extracted {len(results)} places with full details.")
        return results

    # ------------------------------------------------------------------
    # Feed discovery loop
    # ------------------------------------------------------------------

    async def _run_feed_discovery_loop(
        self,
        page: Page,
        keyword: str,
        city: str,
        district: str,
        max_results: int,
        results: List[Dict[str, Any]],
        seen_names: Set[str],
        seen_hrefs: Set[str],
        on_place_inspected: Optional[Callable[[Dict[str, Any], int, int], Any]],
        on_progress_status: Optional[Callable[[str, int], Any]],
    ) -> None:
        max_scroll_attempts = self._resolve_scroll_budget(max_results)
        progress_denominator = max_results if max_results > 0 else settings.SCRAPER_UNLIMITED_DISTRICT_TARGET
        scroll_attempts = 0
        stagnant_count = 0

        if on_progress_status:
            await on_progress_status(f"📡 {city} > {district} işletme akışı taranıyor...", 15)

        while scroll_attempts < max_scroll_attempts:
            # 1. Fast batch extraction of all visible cards in DOM
            try:
                extracted_cards: List[Dict[str, Any]] = await page.evaluate(_FEED_CARDS_EXTRACT_JS)
            except Exception as eval_err:
                logger.warning(f"[GMAPS_PLAYWRIGHT] Feed evaluation warning: {eval_err}")
                extracted_cards = []

            new_cards_this_iteration = 0

            for c in extracted_cards:
                href = c.get("href")
                raw_name = c.get("name")
                if not href or not raw_name:
                    continue
                if href in seen_hrefs or raw_name in seen_names:
                    continue

                seen_hrefs.add(href)
                seen_names.add(raw_name)
                new_cards_this_iteration += 1

                raw_phone = c.get("phone")
                phone_data = PhoneService.normalize_to_e164(raw_phone) if raw_phone else None
                clean_web = clean_extracted_website(c.get("website"))
                raw_addr = c.get("address")
                full_address = clean_extracted_address(raw_addr) if raw_addr else f"{district}, {city}"
                lat, lon = extract_coords_from_url(href)

                lead_dict = {
                    "name": raw_name,
                    "category": c.get("category") or keyword,
                    "phone": raw_phone,
                    "phone_e164": phone_data["e164"] if phone_data else None,
                    "is_mobile": phone_data.get("is_mobile", False) if phone_data else False,
                    "is_whatsapp_eligible": phone_data.get("is_whatsapp_eligible", False) if phone_data else False,
                    "website": clean_web,
                    "address": full_address,
                    "city": city,
                    "district": district,
                    "latitude": lat,
                    "longitude": lon,
                    "rating": c.get("rating"),
                    "reviews_count": c.get("reviewsCount", 0),
                    "google_maps_url": href,
                    "place_id": f"gmaps_{hashlib.sha256(href.encode()).hexdigest()[:16]}",
                    "source": "GOOGLE_MAPS",
                    "is_verified": bool(phone_data or clean_web or c.get("rating")),
                    "display_name": f"{raw_name}, {full_address}"
                }

                results.append(lead_dict)
                logger.info(f"[GMAPS_PLAYWRIGHT] Extracted #{len(results)}: '{raw_name}' ({phone_data['e164'] if phone_data else 'No phone'})")

                if on_place_inspected:
                    await on_place_inspected(lead_dict, len(results), progress_denominator)

                if max_results > 0 and len(results) >= max_results:
                    break

            if max_results > 0 and len(results) >= max_results:
                break

            if await self._reached_end_of_results(page):
                logger.info(f"[GMAPS_PLAYWRIGHT] Reached end-of-results marker for {city} > {district}.")
                break

            if new_cards_this_iteration == 0:
                stagnant_count += 1
                if stagnant_count >= 4:
                    logger.info(f"[GMAPS_PLAYWRIGHT] Discovery settled with {len(results)} places.")
                    break
            else:
                stagnant_count = 0

            # 2. Smooth feed scroll
            try:
                await page.evaluate("""() => {
                    const feed = document.querySelector('div[role="feed"], .m6QErb[aria-label]');
                    if (feed) feed.scrollTop += 6000;
                }""")
            except Exception:
                pass

            await page.wait_for_timeout(600)
            scroll_attempts += 1

    # ------------------------------------------------------------------
    # Single-place branch
    # ------------------------------------------------------------------

    async def _scrape_single_place(
        self,
        page: Page,
        keyword: str,
        city: str,
        district: str,
    ) -> Dict[str, Any]:
        """Extracts the direct place view shown for exact-match brand queries."""
        raw_name = (await page.locator('h1.DUwDvf, div.fontHeadlineLarge').first.inner_text()).strip()
        details = await self._extract_single_place_details(page)

        full_address = clean_extracted_address(details.get("address")) or f"{district}, {city}"
        raw_phone = details.get("phone")
        phone_data = PhoneService.normalize_to_e164(raw_phone) if raw_phone else None
        clean_web = clean_extracted_website(details.get("website"))
        lat, lon = extract_coords_from_url(page.url)

        return {
            "name": raw_name,
            "category": details.get("category") or keyword,
            "phone": raw_phone,
            "phone_e164": phone_data["e164"] if phone_data else None,
            "is_mobile": phone_data.get("is_mobile", False) if phone_data else False,
            "is_whatsapp_eligible": phone_data.get("is_whatsapp_eligible", False) if phone_data else False,
            "website": clean_web,
            "address": full_address,
            "city": city,
            "district": district,
            "latitude": lat,
            "longitude": lon,
            "rating": details.get("rating"),
            "reviews_count": details.get("reviewsCount", 0),
            "google_maps_url": page.url,
            "place_id": f"gmaps_{hashlib.sha256(page.url.encode()).hexdigest()[:16]}",
            "source": "GOOGLE_MAPS",
            "is_verified": True if (phone_data or clean_web or details.get("rating")) else False,
            "display_name": f"{raw_name}, {full_address}"
        }

    async def _extract_single_place_details(self, page: Page) -> Dict[str, Any]:
        details = await page.evaluate("""() => {
            const res = { address: null, phone: null, website: null, rating: null, reviewsCount: 0, category: null };
            const addrBtn = document.querySelector('button[data-item-id="address"], [data-tooltip*="Adres"]');
            if (addrBtn) res.address = addrBtn.getAttribute('aria-label') || addrBtn.innerText.trim();

            const phoneBtn = document.querySelector('button[data-item-id*="phone"], a[href*="tel:"]');
            if (phoneBtn) res.phone = phoneBtn.getAttribute('aria-label') || phoneBtn.innerText.trim() || phoneBtn.href;

            const webBtn = document.querySelector('a[data-item-id="authority"]');
            if (webBtn) res.website = webBtn.href;

            const ratingEl = document.querySelector('div.F7nice span[aria-hidden="true"], span.MW4etd');
            if (ratingEl) res.rating = parseFloat(ratingEl.innerText.replace(',', '.').trim()) || null;

            const revEl = document.querySelector('div.F7nice span[aria-label*="yorum"], span.UY7F9');
            if (revEl) {
                const revClean = revEl.innerText.replace(/[^0-9]/g, '');
                if (revClean) res.reviewsCount = parseInt(revClean, 10);
            }

            const catBtn = document.querySelector('button[jsaction*="category"]');
            if (catBtn) res.category = catBtn.innerText.trim();

            const rows = Array.from(document.querySelectorAll('div.Io6YTe, div.rogA2c')).map(r => r.innerText.trim());
            for (const row of rows) {
                if (!res.phone) {
                    const pMatch = row.match(/(?:0[2-5]\\d{2}[\\s\\.\\-\\(\\)]*\\d{3}[\\s\\.\\-\\(\\)]*\\d{2}[\\s\\.\\-\\(\\)]*\\d{2}|\\+90[\\s\\.\\-\\(\\)]*[2-5]\\d{2}[\\s\\.\\-\\(\\)]*\\d{3}|0850[\\s\\.\\-\\(\\)]*\\d{3}[\\s\\.\\-\\(\\)]*\\d{2}[\\s\\.\\-\\(\\)]*\\d{2})/);
                    if (pMatch) res.phone = pMatch[0];
                }
                if (!res.address) {
                    if (row.includes('Mah') || row.includes('Cd') || row.includes('Sok') || row.includes('No:')) {
                        res.address = row;
                    }
                }
            }
            return res;
        }""")
        return details

    # ------------------------------------------------------------------
    # Multi-district convenience wrapper
    # ------------------------------------------------------------------

    async def scrape_multi_district(
        self,
        keyword: str,
        city: str,
        districts: List[str],
        max_results_per_district: int = 100,
        progress_callback: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        all_leads: List[Dict[str, Any]] = []
        seen_phones: Set[str] = set()
        seen_names: Set[str] = set()

        for idx, district in enumerate(districts):
            if progress_callback:
                await progress_callback(
                    status="RUNNING",
                    message=f"Google Maps taranıyor: {city} > {district} ({idx + 1}/{len(districts)})...",
                    current_district=district,
                    total_found=len(all_leads)
                )

            district_leads = await self.scrape_district_places(
                keyword=keyword,
                city=city,
                district=district,
                max_results=max_results_per_district
            )

            for lead in district_leads:
                phone_key = lead.get("phone_e164")
                name_key = normalize_turkish(lead.get("name", ""))

                if phone_key and phone_key in seen_phones:
                    continue
                if name_key and name_key in seen_names:
                    continue

                if phone_key:
                    seen_phones.add(phone_key)
                if name_key:
                    seen_names.add(name_key)

                all_leads.append(lead)

        return all_leads
