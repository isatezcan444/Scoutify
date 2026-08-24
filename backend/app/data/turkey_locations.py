"""
Turkish 81 Cities & Official Districts Mapping for Deep Regional Crawling.
Provides canonical location data and Turkish diacritics normalization.
"""
import re
from typing import List, Optional

# Turkish diacritics mapping for normalization (comparison only, display values preserved)
_TR_NORMALIZE_MAP = str.maketrans(
    "çğıöşüÇĞİÖŞÜ",
    "cgiosuCGIOSU"
)


def normalize_turkish(text: str) -> str:
    """
    Normalizes Turkish text for diacritics-insensitive comparison.
    Preserves original display value — use only for matching.
    Example: 'Ataşehir' -> 'atasehir'
    """
    if not text:
        return ""
    return text.translate(_TR_NORMALIZE_MAP).lower().strip()


TURKEY_LOCATIONS = [
    {
        "name": "İstanbul",
        "districts": [
            "Kadıköy", "Beşiktaş", "Ümraniye", "Şişli", "Bakırköy", "Fatih", "Üsküdar",
            "Ataşehir", "Avcılar", "Bağcılar", "Bahçelievler", "Başakşehir", "Bayrampaşa",
            "Beykoz", "Beylikdüzü", "Beyoğlu", "Büyükçekmece", "Çatalca", "Çekmeköy", "Esenler",
            "Esenyurt", "Eyüpsultan", "Gaziosmanpaşa", "Güngören", "Kağıthane", "Kartal",
            "Küçükçekmece", "Maltepe", "Pendik", "Sancaktepe", "Sarıyer", "Silivri",
            "Sultanbeyli", "Sultangazi", "Şile", "Tuzla", "Zeytinburnu", "Adalar", "Arnavutköy"
        ]
    },
    {
        "name": "Ankara",
        "districts": [
            "Çankaya", "Keçiören", "Yenimahalle", "Mamak", "Etimesgut", "Sincan", "Altındağ",
            "Pursaklar", "Gölbaşı", "Polatlı", "Çubuk", "Kahramankazan", "Beypazarı", "Elmadağ",
            "Akyurt", "Nallıhan", "Haymana", "Kızılcahamam", "Bala", "Kalecik", "Ayaş",
            "Güdül", "Çamlıdere", "Evren", "Şereflikoçhisar"
        ]
    },
    {
        "name": "İzmir",
        "districts": [
            "Konak", "Karşıyaka", "Bornova", "Buca", "Çiğli", "Gaziemir", "Bayraklı",
            "Karabağlar", "Balçova", "Narlıdere", "Güzelbahçe", "Torbalı", "Menemen",
            "Kemalpaşa", "Aliağa", "Menderes", "Urla", "Çeşme", "Seferihisar", "Bergama",
            "Ödemiş", "Tire", "Dikili", "Foça", "Selçuk", "Bayındır", "Kınık", "Kiraz", "Beydağ", "Karaburun"
        ]
    },
    {
        "name": "Bursa",
        "districts": [
            "Osmangazi", "Nilüfer", "Yıldırım", "İnegöl", "Gemlik", "Mustafakemalpaşa", "Mudanya",
            "Gürsu", "Karacabey", "Orhangazi", "Kestel", "Yenişehir", "İznik", "Orhaneli", "Keles", "Büyükorhan", "Harmancık"
        ]
    },
    {
        "name": "Antalya",
        "districts": [
            "Muratpaşa", "Kepez", "Konyaaltı", "Alanya", "Manavgat", "Serik", "Döşemealtı",
            "Aksu", "Kumluca", "Kaş", "Korkuteli", "Gazipaşa", "Finike", "Kemer", "Elmalı", "Demre", "Akseki", "Gündoğmuş", "İbradı"
        ]
    },
    {
        "name": "Adana",
        "districts": [
            "Seyhan", "Yüreğir", "Çukurova", "Sarıçam", "Ceyhan", "Kozan", "İmamoğlu",
            "Karataş", "Pozantı", "Karaisalı", "Yumurtalık", "Tufanbeyli", "Feke", "Aladağ", "Saimbeyli"
        ]
    },
    {
        "name": "Konya",
        "districts": [
            "Selçuklu", "Meram", "Karatay", "Ereğli", "Akşehir", "Beyşehir", "Çumra", "Seydişehir",
            "Ilgın", "Cihanbeyli", "Kulu", "Karapınar", "Kadınhanı", "Sarayönü", "Bozkır", "Yunak"
        ]
    },
    {
        "name": "Gaziantep",
        "districts": [
            "Şahinbey", "Şehitkamil", "Nizip", "İslahiye", "Nurdağı", "Araban", "Oğuzeli", "Yavuzeli", "Karkamış"
        ]
    },
    {
        "name": "Kocaeli",
        "districts": [
            "İzmit", "Gebze", "Darıca", "Gölcük", "Körfez", "Derince", "Çayırova",
            "Kartepe", "Başiskele", "Karamürsel", "Kandıra", "Dilovası"
        ]
    },
    {
        "name": "Mersin",
        "districts": [
            "Toroslar", "Akdeniz", "Yenişehir", "Mezitli", "Tarsus", "Erdemli", "Silifke", "Anamur", "Mut", "Bozyazı", "Aydıncık", "Gülnar", "Çamlıyayla"
        ]
    }
]


def get_districts_for_city(city_name: str) -> List[str]:
    """Returns official districts for given city. Returns empty list if city not found."""
    norm_city = normalize_turkish(city_name)
    for c in TURKEY_LOCATIONS:
        if normalize_turkish(c["name"]) == norm_city:
            return list(c["districts"])
    return []


def is_valid_district(city_name: str, district_name: str) -> bool:
    """Checks if a district belongs to the given city using normalized comparison."""
    districts = get_districts_for_city(city_name)
    norm_district = normalize_turkish(district_name)
    return any(normalize_turkish(d) == norm_district for d in districts)


def find_matching_district(city_name: str, text: str) -> Optional[str]:
    """
    Searches for any known district name within a text string (e.g., an address).
    Returns the canonical (display) district name if found, None otherwise.
    """
    if not text:
        return None
    norm_text = normalize_turkish(text)
    districts = get_districts_for_city(city_name)
    for d in districts:
        if normalize_turkish(d) in norm_text:
            return d
    return None
