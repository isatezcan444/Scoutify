"""
Query Expander & Taxonomy Engine for B2B Lead Discovery.
Generates controlled, highly relevant Turkish and international term variations,
directory category slugs, and OSM query parameters without altering the geographic scope.
"""
import re
from typing import List, Dict, Set
from backend.app.data.turkey_locations import normalize_turkish


class QueryExpander:
    """
    Expands a high-level business category (e.g. 'Saç Ekim Merkezleri & Poliklinikler')
    into a comprehensive set of discovery terms, directory slugs, and OSM amenity tags.
    """

    # Category mappings to directory slugs and search terms
    CATEGORY_TAXONOMY: Dict[str, Dict[str, List[str]]] = {
        "sac_ekim": {
            "keywords": [
                "saç", "sac", "ekim", "ekimi", "transplant", "hair", "trikoloji"
            ],
            "directory_slugs": [
                "saç-ekimi",
                "saç-ekim-merkezi",
                "saç-ekimi-ve-tedavisi",
                "estetik-merkezleri",
                "poliklinikler",
                "tıp-merkezleri",
                "klinikler"
            ],
            "text_terms": [
                "saç ekim merkezi",
                "saç ekimi kliniği",
                "saç ekim",
                "saç ekimi ve tedavisi",
                "hair transplant clinic",
                "estetik ve saç ekimi",
                "poliklinik saç ekim",
                "saç tasarım merkezi"
            ],
            "osm_amenities": [
                "clinic", "hospital", "beauty", "hairdresser", "doctors", "healthcare"
            ]
        },
        "dis_klinigi": {
            "keywords": [
                "diş", "dis", "dent", "dental", "ortodonti", "periodontoloji", "ağız"
            ],
            "directory_slugs": [
                "diş-hekimleri",
                "diş-klinikleri",
                "ağız-ve-diş-sağlığı-merkezleri",
                "diş-poliklinikleri",
                "ortodonti-uzmanları",
                "diş-hastaneleri"
            ],
            "text_terms": [
                "diş kliniği",
                "ağız ve diş sağlığı",
                "diş hekimi",
                "dental klinik",
                "diş polikliniği",
                "dentist clinic",
                "ortodonti kliniği"
            ],
            "osm_amenities": [
                "dentist", "clinic", "hospital", "healthcare", "doctors"
            ]
        },
        "guzellik_estetik": {
            "keywords": [
                "güzellik", "guzellik", "estetik", "kuaför", "kuafor", "spa", "lazer", "epilasyon"
            ],
            "directory_slugs": [
                "güzellik-salonları",
                "estetik-merkezleri",
                "kuaförler",
                "cilt-bakımı",
                "lazer-epilasyon-merkezleri",
                "spa-merkezleri"
            ],
            "text_terms": [
                "güzellik salonu",
                "güzellik merkezi",
                "estetik merkezi",
                "cilt bakımı ve güzellik",
                "lazer epilasyon",
                "beauty salon",
                "kuaför ve güzellik salonu"
            ],
            "osm_amenities": [
                "beauty", "hairdresser", "spa", "cosmetics"
            ]
        },
        "hukuk_avukat": {
            "keywords": [
                "hukuk", "avukat", "baro", "danışmanlık", "arabuluculuk", "dava"
            ],
            "directory_slugs": [
                "avukatlar",
                "hukuk-büroları",
                "arabuluculuk-merkezleri",
                "hukuki-danışmanlık"
            ],
            "text_terms": [
                "hukuk bürosu",
                "avukatlık ofisi",
                "avukat",
                "hukuki danışmanlık",
                "law office",
                "arabuluculuk bürosu"
            ],
            "osm_amenities": [
                "lawyer", "office"
            ]
        },
        "yazilim_ajans": {
            "keywords": [
                "yazılım", "yazilim", "bilişim", "bilisim", "ajans", "medya", "web", "tasarım", "reklam"
            ],
            "directory_slugs": [
                "yazılım-firmaları",
                "reklam-ajansları",
                "web-tasarım",
                "bilişim-firmaları",
                "dijital-pazarlama-ajansları"
            ],
            "text_terms": [
                "yazılım şirketi",
                "dijital reklam ajansı",
                "web tasarım ajansı",
                "bilişim teknolojileri",
                "software company",
                "yazılım ajansı"
            ],
            "osm_amenities": [
                "company", "office", "coworking", "it"
            ]
        },
        "saglik_doktor": {
            "keywords": [
                "sağlık", "saglik", "doktor", "tabip", "klinik", "tıp", "tip", "hastane", "poliklinik"
            ],
            "directory_slugs": [
                "doktorlar",
                "klinikler",
                "tıp-merkezleri",
                "poliklinikler",
                "özel-hastaneler",
                "sağlık-kabini"
            ],
            "text_terms": [
                "özel tıp merkezi",
                "özel poliklinik",
                "sağlık merkezi",
                "özel klinik",
                "doktor muayenehanesi",
                "medical center"
            ],
            "osm_amenities": [
                "doctors", "clinic", "hospital", "pharmacy", "healthcare"
            ]
        },
        "muhasebe_mali": {
            "keywords": [
                "muhasebe", "mali", "müşavir", "musavir", "smmm", "ymm", "vergi", "denetim"
            ],
            "directory_slugs": [
                "mali-müşavirler",
                "muhasebe-büroları",
                "yeminli-mali-müşavirler",
                "denetim-firmaları"
            ],
            "text_terms": [
                "mali müşavirlik",
                "muhasebe bürosu",
                "serbest muhasebeci",
                "smmm ofisi",
                "accounting office"
            ],
            "osm_amenities": [
                "accountant", "office", "financial"
            ]
        }
    }

    @classmethod
    def identify_category(cls, keyword: str) -> str:
        """Identifies the closest taxonomy category based on input keyword."""
        norm_kw = normalize_turkish(keyword)
        for cat_key, cat_data in cls.CATEGORY_TAXONOMY.items():
            for kw in cat_data["keywords"]:
                if kw in norm_kw:
                    return cat_key
        return "general"

    @classmethod
    def expand_queries(cls, keyword: str, district: str, city: str) -> List[str]:
        """
        Generates comprehensive text search queries for web & search engine discovery.
        Always keeps district and city strictly bound.
        """
        queries: List[str] = []
        cat_key = cls.identify_category(keyword)

        # 1. Base variations with the user-provided keyword
        clean_kw = re.sub(r'[&,/-]', ' ', keyword).strip()
        queries.append(f"{clean_kw} {district} {city}".strip())
        queries.append(f"{district} {clean_kw}".strip())

        # Sub-terms if combined with '&' or 've'
        parts = re.split(r'\s*(?:&|ve|\+|\/|,)\s*', keyword)
        if len(parts) > 1:
            for part in parts:
                p = part.strip()
                if len(p) >= 3:
                    queries.append(f"{p} {district} {city}".strip())
                    queries.append(f"{district} {p}".strip())

        # 2. Taxonomy-driven synonym expansion
        if cat_key in cls.CATEGORY_TAXONOMY:
            for term in cls.CATEGORY_TAXONOMY[cat_key]["text_terms"]:
                queries.append(f"{term} {district} {city}".strip())
                queries.append(f"{district} {term}".strip())

        # Deduplicate preserving order
        unique_queries = []
        seen = set()
        for q in queries:
            norm = normalize_turkish(q)
            if norm not in seen:
                seen.add(norm)
                unique_queries.append(q)

        return unique_queries

    @classmethod
    def get_directory_slugs(cls, keyword: str) -> List[str]:
        """
        Returns relevant Turkish directory category URL slugs for directory scraping.
        """
        cat_key = cls.identify_category(keyword)
        if cat_key in cls.CATEGORY_TAXONOMY:
            return cls.CATEGORY_TAXONOMY[cat_key]["directory_slugs"]
        
        # Fallback to normalized keyword as slug
        norm = normalize_turkish(keyword)
        clean_slug = re.sub(r'[^a-z0-9]+', '-', norm).strip('-')
        return [clean_slug] if clean_slug else ["isletmeler"]

    @classmethod
    def get_osm_amenity_terms(cls, keyword: str) -> List[str]:
        """Returns OSM tag terms for OpenStreetMap Nominatim/Overpass queries."""
        cat_key = cls.identify_category(keyword)
        if cat_key in cls.CATEGORY_TAXONOMY:
            return cls.CATEGORY_TAXONOMY[cat_key]["osm_amenities"]
        return ["office", "commercial", "shop"]
