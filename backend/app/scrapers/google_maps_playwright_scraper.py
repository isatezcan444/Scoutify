"""
High-Recall Google Maps Playwright Discovery Scraper with Real-Time Place Streaming.
Directly queries Google Maps places feed for target city, district, and business category.
Interacts with each place card to extract exact full street/neighborhood address,
direct landline (02xx) & mobile GSM phone numbers, official website, rating, reviews, and place coordinates.
Streams each discovered place in real-time with satellite-tuner style progress updates.
"""
import re
import asyncio
import hashlib
import logging
from typing import List, Dict, Any, Optional, Set, Callable
from urllib.parse import quote, unquote, urlparse
from playwright.async_api import async_playwright, Browser, Page

from backend.app.services.phone_service import PhoneService
from backend.app.data.turkey_locations import normalize_turkish

logger = logging.getLogger(__name__)


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
        seen_maps_urls: Set[str] = set()
        
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
                    "--disable-dev-shm-usage"
                ]
            )
            context = await browser.new_context(
                locale="tr-TR",
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            page = await context.new_page()
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

            try:
                await page.goto(maps_url, wait_until="domcontentloaded", timeout=25000)
                await page.wait_for_timeout(1800)

                # Dismiss Google Consent dialog if present
                try:
                    accept_btn = page.locator('button:has-text("Tümünü kabul et"), button:has-text("Kabul et"), button:has-text("Accept all")')
                    if await accept_btn.count() > 0:
                        await accept_btn.first.click()
                        await page.wait_for_timeout(600)
                except Exception:
                    pass

                # Wait for Google Maps page initial render
                await page.wait_for_timeout(2500)

                # Check if it's a single direct place result (rare case for exact match brand)
                feed_count = await page.locator('a.hfpxzc').count()
                single_title = page.locator('h1.DUwDvf, div.fontHeadlineLarge')
                if feed_count == 0 and await single_title.count() > 0:
                    raw_name = (await single_title.first.inner_text()).strip()
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
                                if (row.includes('Mah') || row.includes('Cd') || row.includes('Sok') || row.includes('No:') || row.includes('347') || row.includes('34')) {
                                    res.address = row;
                                }
                            }
                        }
                        return res;
                    }""")

                    full_address = clean_extracted_address(details.get("address")) or f"{district}, {city}"
                    raw_phone = details.get("phone")
                    phone_data = PhoneService.normalize_to_e164(raw_phone) if raw_phone else None
                    clean_web = clean_extracted_website(details.get("website"))
                    lat, lon = extract_coords_from_url(page.url)

                    lead_data = {
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
                    results.append(lead_data)
                    if on_place_inspected:
                        await on_place_inspected(lead_data, 1, 1)

                    await browser.close()
                    return results

                # Progressive in-view card inspection loop:
                # Discovers and inspects each place card in the viewport before Google Maps virtual DOM unmounts it.
                scroll_attempts = 0
                max_scroll_attempts = 15 if (max_results == 0 or max_results > 50) else max(5, (max_results // 5) + 2)
                stagnant_scrolls = 0
                seen_hrefs: Set[str] = set()

                if on_progress_status:
                    await on_progress_status(f"📡 {city} > {district} işletme kanalları taranıyor...", 15)

                while scroll_attempts < max_scroll_attempts:
                    current_cards = await page.locator('a.hfpxzc').all()
                    if len(current_cards) == 0 and scroll_attempts == 0:
                        await page.wait_for_timeout(1500)
                        current_cards = await page.locator('a.hfpxzc').all()

                    logger.info(f"[GMAPS_PLAYWRIGHT] [Scroll {scroll_attempts+1}] Found {len(current_cards)} cards in DOM")
                    new_cards_inspected_this_scroll = 0

                    for card in current_cards:
                        try:
                            href = await card.get_attribute("href")
                            raw_name = await card.get_attribute("aria-label")

                            if not href or not raw_name:
                                continue
                            if href in seen_hrefs or raw_name in seen_names:
                                continue

                            seen_hrefs.add(href)
                            seen_names.add(raw_name)
                            new_cards_inspected_this_scroll += 1

                            # Inspect the visible card
                            try:
                                await card.scroll_into_view_if_needed(timeout=1000)
                                await card.click(timeout=1500)
                                try:
                                    await page.wait_for_selector('button[data-item-id="address"], div.Io6YTe, button[data-item-id*="phone"]', timeout=1500)
                                except Exception:
                                    await page.wait_for_timeout(450)
                            except Exception as click_err:
                                logger.debug(f"[GMAPS_PLAYWRIGHT] Card click fallback for '{raw_name}': {click_err}")

                            # Extract detailed attributes from the active place details pane
                            details = await page.evaluate("""() => {
                                const res = {
                                    address: null,
                                    phone: null,
                                    website: null,
                                    rating: null,
                                    reviewsCount: 0,
                                    category: null,
                                    is_sponsored: false
                                };

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
                                    res.phone = phoneBtn.getAttribute('aria-label') || phoneBtn.innerText.trim() || phoneBtn.href;
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
                                        if (row.includes('Mah') || row.includes('Cd') || row.includes('Sok') || row.includes('No:') || row.includes('347') || row.includes('34') || row.includes('/')) {
                                            res.address = row;
                                        }
                                    }
                                }

                                return res;
                            }""")

                            # Clean full address
                            full_address = clean_extracted_address(details.get("address")) or f"{district}, {city}"

                            # Clean & normalize phone
                            raw_phone = details.get("phone")
                            phone_data = PhoneService.normalize_to_e164(raw_phone) if raw_phone else None

                            # Clean website
                            clean_web = clean_extracted_website(details.get("website"))

                            # Coordinates
                            lat, lon = extract_coords_from_url(href)

                            lead_dict = {
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
                                "google_maps_url": href,
                                "place_id": f"gmaps_{hashlib.sha256(href.encode()).hexdigest()[:16]}",
                                "source": "GOOGLE_MAPS",
                                "is_verified": True if (phone_data or clean_web or details.get("rating")) else False,
                                "display_name": f"{raw_name}, {full_address}"
                            }

                            results.append(lead_dict)
                            logger.info(f"[GMAPS_PLAYWRIGHT] Extracted #{len(results)}: '{raw_name}' ({phone_data['e164'] if phone_data else 'No phone'})")

                            # Real-time satellite-tuner style callback
                            if on_place_inspected:
                                await on_place_inspected(lead_dict, len(results), max_results or 100)

                            if max_results > 0 and len(results) >= max_results:
                                break
                        except Exception as item_err:
                            logger.warning(f"[GMAPS_PLAYWRIGHT] Error processing card item '{raw_name}': {item_err}", exc_info=True)

                    if max_results > 0 and len(results) >= max_results:
                        break

                    # Check for explicit end-of-results markers
                    end_marker = page.locator('span:has-text("Tüm sonuçlara ulaştınız"), span:has-text("Sonuçların sonuna geldiniz"), span:has-text("reached the end"), div.HlvSq')
                    if await end_marker.count() > 0:
                        logger.info(f"[GMAPS_PLAYWRIGHT] Reached end of results marker for {city} > {district}.")
                        break

                    if new_cards_inspected_this_scroll == 0:
                        stagnant_scrolls += 1
                        if stagnant_scrolls >= 3:
                            break
                    else:
                        stagnant_scrolls = 0

                    # Feed scroll with last card focus, mouse wheel and PageDown
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
                    
                    await page.wait_for_timeout(1000)
                    scroll_attempts += 1

            except Exception as e:
                logger.error(f"[GMAPS_PLAYWRIGHT] Error searching '{query}': {e}", exc_info=True)
            finally:
                await browser.close()

        logger.info(f"[GMAPS_PLAYWRIGHT] District '{district}' finished. Extracted {len(results)} places with full details.")
        return results

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
