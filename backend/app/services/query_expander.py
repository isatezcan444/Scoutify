"""
Query Expander & Taxonomy Engine for B2B Lead Discovery.
Generates controlled, highly relevant Turkish and international term variations,
directory category slugs, and OSM query parameters without altering the geographic scope.
"""
import re
import logging
from typing import List, Dict, Set
from backend.app.data.turkey_locations import normalize_turkish

logger = logging.getLogger(__name__)

# Administrative suffixes riding along location names ('İstanbul İli', 'Ataşehir İlçesi').
_LOCATION_SUFFIX_TOKENS = ("il", "ili", "ilce", "ilcesi")

# Separators preserved while rebuilding sanitized keywords.
_KEYWORD_SEPARATORS = r"([\s&+/,:;|-]+)"


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

    @staticmethod
    def _strip_admin_suffix(norm_token: str) -> str:
        """Reduces 'atasehir ilcesi' to 'atasehir' for location-token matching."""
        parts = norm_token.split()
        if len(parts) >= 2 and parts[-1] in _LOCATION_SUFFIX_TOKENS:
            return " ".join(parts[:-1])
        return norm_token

    @classmethod
    def strip_location_tokens(cls, keyword: str, city: str, districts: List[str]) -> str:
        """
        Removes city/district names accidentally typed inside the sector keyword,
        PRESERVING the original connectors between surviving terms so downstream
        variant-splitting ('&', '+' ...) keeps working.

        Users sometimes paste a full search string such as
        'Diş Klinikleri & Ağız Sağlığı Merkezleri + istanbul + ataşehir' into the
        sector field. Left in place, the connector-splitter would turn 'istanbul'
        and 'ataşehir' into independent search TERMS, producing geo-garbage queries.
        Location binding is re-added deterministically by the caller ({city} {district}).
        """
        if not keyword or not keyword.strip():
            return ""

        blocked = {normalize_turkish(city)} if city else set()
        blocked.update(normalize_turkish(d) for d in districts if d)
        blocked.discard("")

        def is_location_token(token: str) -> bool:
            norm = normalize_turkish(token)
            if not norm:
                return False
            if norm in _LOCATION_SUFFIX_TOKENS:
                return True  # orphaned 'İli' / 'İlçesi' left behind by a removed name
            return cls._strip_admin_suffix(norm) in blocked

        pieces = re.split(_KEYWORD_SEPARATORS, keyword)
        token_sep_pairs = list(zip(pieces[0::2], pieces[1::2]))

        kept_pairs: List[tuple] = []
        skipped: List[str] = []
        for token, separator in token_sep_pairs:
            if not token:
                continue
            if is_location_token(token):
                skipped.append(token)
                continue
            kept_pairs.append((token, separator))

        if not skipped:
            return keyword.strip()  # Untouched passthrough — zero semantic drift.

        rebuilt = "".join(token + separator for token, separator in kept_pairs).strip(" \t&+/,:;|-")
        logger.info(f"[QUERY_EXPANDER] Location tokens stripped from keyword: {skipped} -> '{rebuilt}'")
        return rebuilt

    @classmethod
    def build_search_terms(cls, keyword: str, max_terms: int = 3) -> List[str]:
        """
        Builds a bounded, relevance-ordered list of geo-free search term variants
        for map search engines (Google Maps etc.).

        Order of precedence:
        1. The raw keyword as entered by the user.
        2. Segments split on connectors ('&', 've', '+', '/', ',') — combined labels
           such as 'Diş Klinikleri & Ağız Sağlığı Merkezleri' otherwise narrow
           recall when sent to the engine verbatim.
        3. Taxonomy synonym terms for the identified category.

        The result is deduplicated (diacritics-insensitive) and capped at max_terms.
        Geographic binding ({city} {district}) is the caller's responsibility.
        """
        if not keyword or not keyword.strip():
            return []

        variants: List[str] = [keyword.strip()]

        # 2. Connector-split segments of the user label
        parts = re.split(r'\s*(?:&|ve|\+|\/|,)\s*', keyword)
        variants.extend(p.strip() for p in parts if len(p.strip()) >= 3)

        # 3. Taxonomy-driven synonyms
        cat_key = cls.identify_category(keyword)
        if cat_key in cls.CATEGORY_TAXONOMY:
            variants.extend(cls.CATEGORY_TAXONOMY[cat_key]["text_terms"])

        unique: List[str] = []
        seen: Set[str] = set()
        for v in variants:
            norm = normalize_turkish(v)
            if norm and norm not in seen:
                seen.add(norm)
                unique.append(v)
                if len(unique) >= max_terms:
                    break
        return unique

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
