import json
import pytest
import urllib.parse
from unittest.mock import AsyncMock, patch, MagicMock
from backend.app.scrapers.google_maps_http_scraper import GoogleMapsHttpScraper


@pytest.fixture
def http_scraper():
    return GoogleMapsHttpScraper()


def test_build_search_url(http_scraper):
    url_p0 = http_scraper._build_search_url("İstanbul Ataşehir Diş", start=0)
    assert "tbm=map" in url_p0
    assert "!7i20" in url_p0
    assert "!8i" not in url_p0
    assert urllib.parse.quote("İstanbul Ataşehir Diş") in url_p0

    url_p1 = http_scraper._build_search_url("İstanbul Ataşehir Diş", start=20)
    assert "!8i20" in url_p1


def test_extract_phone_direct(http_scraper):
    pd = [None] * 180
    pd[178] = [None, None, None, "0216 456 56 33"]
    phone = http_scraper._extract_phone(pd)
    assert phone == "0216 456 56 33"


def test_extract_phone_mobile(http_scraper):
    pd = [None] * 180
    pd[178] = ["0542 789 28 85"]
    phone = http_scraper._extract_phone(pd)
    assert phone == "0542 789 28 85"


def test_extract_website_unwrap(http_scraper):
    pd = [None] * 10
    pd[7] = ["/url?q=https://www.dentatasehir.com/&opi=123"]
    web = http_scraper._extract_website(pd)
    assert web == "https://www.dentatasehir.com"


def test_extract_website_rejects_aggregators(http_scraper):
    pd = [None] * 10
    pd[7] = ["https://www.facebook.com/klinik"]
    web = http_scraper._extract_website(pd)
    assert web is None


def test_extract_category_clean(http_scraper):
    pd = [None] * 15
    pd[13] = ["Diş Kliniği\nEkstra Bilgi", "Diş Hekimi"]
    cat = http_scraper._extract_category(pd, "Diş")
    assert cat == "Diş Kliniği"


def test_parse_place_entry_complete(http_scraper):
    entry = [None] * 15
    pd = [None] * 180
    pd[10] = "0x14cac8a7:0xa626190b"
    pd[11] = "Özel Test Diş Kliniği"
    pd[13] = ["Diş Kliniği"]
    pd[18] = "Barbaros Mah. No: 10, Ataşehir, İstanbul"
    pd[4] = [None, None, None, None, None, None, None, 4.8, 120]
    pd[9] = [None, None, 40.9928, 29.1249]
    pd[7] = ["https://www.testdis.com"]
    pd[178] = ["0542 123 45 67"]
    entry[14] = pd

    res = http_scraper._parse_place_entry(
        entry=entry,
        keyword="Diş Klinikleri",
        city="İstanbul",
        district="Ataşehir"
    )
    assert res is not None
    assert res["name"] == "Özel Test Diş Kliniği"
    assert res["category"] == "Diş Kliniği"
    assert res["phone_e164"] == "+905421234567"
    assert res["is_mobile"] is True
    assert res["is_whatsapp_eligible"] is True
    assert res["website"] == "https://www.testdis.com"
    assert res["rating"] == 4.8
    assert res["reviews_count"] == 120
    assert res["latitude"] == 40.9928
    assert res["longitude"] == 29.1249
    assert res["place_id"].startswith("gmaps_")
    assert "Ataşehir" in res["address"]


@pytest.mark.asyncio
async def test_scrape_district_places_mock(http_scraper):
    # Mock payload with 2 places
    entry1 = [None] * 15
    pd1 = [None] * 180
    pd1[10] = "0x1:0x1"
    pd1[11] = "Klinik A"
    pd1[13] = ["Diş Kliniği"]
    pd1[18] = "Ataşehir, İstanbul"
    entry1[14] = pd1

    entry2 = [None] * 15
    pd2 = [None] * 180
    pd2[10] = "0x2:0x2"
    pd2[11] = "Klinik B"
    pd2[13] = ["Diş Hekimi"]
    pd2[18] = "Ataşehir, İstanbul"
    entry2[14] = pd2

    raw_payload = [[None, ["meta", entry1, entry2]]]
    mock_json_str = ")]}'\n" + json.dumps(raw_payload)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = mock_json_str

    inspected = []
    async def on_inspected(lead, idx, total):
        inspected.append(lead)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        results = await http_scraper.scrape_district_places(
            keyword="Diş",
            city="İstanbul",
            district="Ataşehir",
            max_results=2,
            on_place_inspected=on_inspected
        )

    assert len(results) == 2
    assert len(inspected) == 2
    assert results[0]["name"] == "Klinik A"
    assert results[1]["name"] == "Klinik B"


# ============================================================
# Address name-prefix strip (kartlarda "İşletme Adı, adres..." bug)
# ============================================================

def test_strip_leading_business_name_exact_prefix(http_scraper):
    from backend.app.scrapers.google_maps_playwright_scraper import strip_leading_business_name
    addr = "Mozaik Dent Ağız ve Diş Sağlığı Polikliniği, Atatürk, Meriç Cd. NO: 21/35, 34758 Ataşehir/İstanbul"
    assert strip_leading_business_name("Mozaik Dent Ağız ve Diş Sağlığı Polikliniği", addr) == \
        "Atatürk, Meriç Cd. NO: 21/35, 34758 Ataşehir/İstanbul"


def test_strip_leading_business_name_no_match_untouched():
    from backend.app.scrapers.google_maps_playwright_scraper import strip_leading_business_name
    addr = "Barbaros Mah. Halk Cd. No:1, Ataşehir"
    assert strip_leading_business_name("Başka Klinik", addr) == addr
    assert strip_leading_business_name(None, addr) == addr
    assert strip_leading_business_name("Klinik", None) is None


def test_strip_leading_business_name_never_empties():
    from backend.app.scrapers.google_maps_playwright_scraper import strip_leading_business_name
    assert strip_leading_business_name("Klinik X", "Klinik X") == "Klinik X"


def test_parse_place_entry_strips_name_from_address(http_scraper):
    entry = [None] * 15
    pd = [None] * 180
    pd[10] = "0x14cac8a7:0xa626190b"
    pd[11] = "Özel Test Diş Kliniği"
    pd[13] = ["Diş Kliniği"]
    pd[18] = "Özel Test Diş Kliniği, Barbaros Mah. No: 10, Ataşehir, İstanbul"
    pd[4] = [None] * 9
    pd[9] = [None, None, 40.9928, 29.1249]
    entry[14] = pd

    res = http_scraper._parse_place_entry(
        entry=entry, keyword="Diş Klinikleri", city="İstanbul", district="Ataşehir"
    )
    assert res is not None
    assert res["address"] == "Barbaros Mah. No: 10, Ataşehir, İstanbul"
    assert not res["address"].startswith("Özel Test Diş Kliniği")
