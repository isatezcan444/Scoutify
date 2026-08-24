"""
Entity Resolution, Person vs Business Detection, and Source Trust Model.
Enforces the fundamental principle: PERSON != BUSINESS, DOCTOR != CLINIC, DENTIST != DENTAL CLINIC.
Balances HIGH PRECISION with HIGH RECALL:
- Real commercial clinics (even those named after doctors, e.g. 'Dr. Ahmet Yılmaz Diş Kliniği' or 'Özkan Öztürk Muayenehanesi') are recognized as CLINIC / BUSINESS.
- Pure individual names without commercial clinic/business markers (e.g. 'Burcu Demiralp', 'Diş Hekimi Burcu Demiralp') are classified as PERSON / UNVERIFIED.
- Provides explainable verification trace and calibrated confidence scoring.
"""
import enum
import re
from typing import Dict, Any, List, Optional, Tuple
from backend.app.data.turkey_locations import normalize_turkish


class EntityType(str, enum.Enum):
    BUSINESS = "BUSINESS"
    CLINIC = "CLINIC"
    COMPANY = "COMPANY"
    PROFESSIONAL = "PROFESSIONAL"
    PERSON = "PERSON"
    DIRECTORY_PROFILE = "DIRECTORY_PROFILE"
    UNKNOWN = "UNKNOWN"


class VerificationStatus(str, enum.Enum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    REJECTED = "REJECTED"
    CANDIDATE = "CANDIDATE"


class ConfidenceLevel(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class SourceTrustTier(str, enum.Enum):
    TIER_1_STRONG = "TIER_1_STRONG"           # Google Maps / Official Website / Corporate Domain
    TIER_2_SUPPORTING = "TIER_2_SUPPORTING"   # Verified Business Directories / Industry Registries / OSM
    TIER_3_WEAK = "TIER_3_WEAK"               # Scraped Yellow Pages / Aggregator Profiles / Person Listings


class EntityResolver:
    """
    Production-Grade Entity Resolver:
    1. Distinguishes commercial business entities (Clinics, Companies, Studios) from private individuals.
    2. Recognizes clinics named after doctors ('Dr. Ahmet Yılmaz Diş Kliniği' -> CLINIC).
    3. Detects pure person/doctor profiles without commercial indicators ('Burcu Demiralp' -> PERSON).
    4. Evaluates source trust and independent verification evidence (Physical address, Phone, Category).
    5. Computes explainable confidence score (0-100) with detailed validation trace.
    6. Prohibits synthetic AI business name generation from personal names.
    """

    # Person / Professional Titles (both Turkish diacritics and ASCII normalized forms)
    PERSON_TITLE_REGEX = re.compile(
        r'\b(?:dr|dt|uzm|prof|doc|doç|op\.?\s*dr|uzm\.?\s*dr|uzm\.?\s*dt|dis\s*hekimi|diş\s*hekimi|dis\s*tabibi|diş\s*tabibi|doktor|avukat|av|mimar|muh|müh|psikolog|diyetisyen|fizyoterapist|optisyen|eczaci|eczacı)\b',
        re.IGNORECASE
    )

    # Explicit Clinic / Medical Practice Keywords
    CLINIC_KEYWORDS = [
        "klinik", "klinigi", "kliniği", "poliklinik", "poliklinigi", "polikliniği",
        "tip merkezi", "tıp merkezi", "dental", "dent", "muayenehane", "muayenehanesi",
        "agiz ve dis", "ağız ve diş", "dis sagligi", "diş sağlığı", "saglik merkezi",
        "sağlık merkezi", "hastane", "hastanesi", "estetik merkezi", "implantoloji",
        "ortodonti", "laboratuvar", "laboratuvari", "laboratuvarı"
    ]

    # Corporate Company Suffixes / Keywords
    CORPORATE_KEYWORDS = [
        "ltd", "sti", "şti", "a.s", "a.ş", "anonim", "sirket", "şirket",
        "sanayi", "ticaret", "tic", "grup", "group", "holding"
    ]

    # Commercial Business & Corporate Suffixes / Keywords
    BUSINESS_KEYWORDS = [
        "merkez", "merkezi", "hastane", "hastanesi", "tip", "tıp",
        "saglik", "sağlık", "estetik", "ofisi", "eczane",
        "danismanlik", "danışmanlık", "ajans", "studio", "stüdyo",
        "akademi", "enstitu", "enstitü", "hizmetleri", "servis", "ticaret"
    ]

    @classmethod
    def get_source_tier(cls, source_name: str, has_official_website: bool = False) -> SourceTrustTier:
        """Determines the trust tier of the discovery / verification source."""
        s = (source_name or "").upper()
        if "GOOGLE" in s or "MAPS" in s or has_official_website:
            return SourceTrustTier.TIER_1_STRONG
        elif "DIRECTORY" in s or "BULURUM" in s or "OPENSTREETMAP" in s or "OSM" in s:
            return SourceTrustTier.TIER_2_SUPPORTING
        return SourceTrustTier.TIER_3_WEAK

    @classmethod
    def detect_entity_type(
        cls,
        name: str,
        category: str = "",
        address: str = "",
        website: Optional[str] = None
    ) -> Tuple[EntityType, List[str]]:
        """
        Analyzes name and context to detect if an entity is a CLINIC, COMPANY, BUSINESS, or PERSON.
        Returns (EntityType, List of detection reasons).
        """
        reasons: List[str] = []
        if not name or len(name.strip()) < 2:
            return EntityType.UNKNOWN, ["İsim çok kısa veya boş"]

        clean_name = name.strip()
        norm_name = normalize_turkish(clean_name)
        words = norm_name.split()

        # 1. Check for explicit Clinic / Healthcare Practice keywords
        # Even if it contains a doctor title (e.g. 'Dr. Ahmet Yılmaz Diş Kliniği' or 'Özkan Öztürk Muayenehanesi'),
        # the presence of clinic/practice markers establishes it as a commercial healthcare entity.
        is_clinic = any(k in norm_name for k in cls.CLINIC_KEYWORDS)
        if is_clinic:
            reasons.append("Klinik/Poliklinik/Muayenehane ticari sağlık kuruluşu belirteci mevcut")
            return EntityType.CLINIC, reasons

        # 2. Check for Corporate legal entity markers (Ltd., A.Ş., Tic. Şti.)
        is_corporate = any(k in norm_name for k in cls.CORPORATE_KEYWORDS)
        if is_corporate:
            reasons.append("Kurumsal şirket unvanı (Ltd/A.Ş./Tic. Şti.) mevcut")
            return EntityType.COMPANY, reasons

        # 3. Check for general commercial business keywords
        is_business = any(k in norm_name for k in cls.BUSINESS_KEYWORDS)
        if is_business:
            reasons.append("Ticari işletme belirteci mevcut")
            return EntityType.BUSINESS, reasons

        # 4. Check for explicit Person/Doctor title prefixes without business markers
        # Example: 'Diş Hekimi Burcu Demiralp', 'Dr. Mehmet Kaya', 'Dt. Ali Can'
        if cls.PERSON_TITLE_REGEX.search(norm_name):
            reasons.append(f"Şahıs/Unvan profili (Ticari unvan veya klinik eki yok): {cls.PERSON_TITLE_REGEX.findall(norm_name)}")
            return EntityType.PERSON, reasons

        # 5. Person Name Pattern Analysis (e.g. 'Burcu Demiralp', 'Kemal Aytuğlu')
        # 2 or 3 alphabetical words, no commercial keywords
        if 2 <= len(words) <= 3:
            all_name_tokens = all(w.isalpha() for w in words)
            if all_name_tokens:
                reasons.append("Kişi adı-soyadı kalıbı (Ticari unvan veya klinik eki yok)")
                return EntityType.PERSON, reasons

        if len(words) == 1:
            reasons.append("Tek kelimelik tanımsız profil")
            return EntityType.DIRECTORY_PROFILE, reasons

        reasons.append("Genel işletme değerlendirmesi")
        return EntityType.BUSINESS, reasons

    @classmethod
    def resolve_entity(
        cls,
        raw_name: str,
        raw_address: str,
        phone_e164: Optional[str],
        website: Optional[str],
        source: str,
        target_category: str,
        is_mobile: bool = False
    ) -> Dict[str, Any]:
        """
        Executes full entity resolution and validation:
        - Detects Entity Type (CLINIC, COMPANY, BUSINESS, PERSON, etc.)
        - Validates business existence
        - Calibrates confidence score for high recall of real businesses while rejecting private individuals
        - Produces explainable verification trace
        """
        has_website = bool(website and len(website.strip()) > 5)
        source_tier = cls.get_source_tier(source, has_official_website=has_website)
        entity_type, type_reasons = cls.detect_entity_type(raw_name, target_category, raw_address, website)

        score = 0
        trace: Dict[str, Any] = {
            "entity_type": entity_type.value,
            "entity_type_reasons": type_reasons,
            "source_tier": source_tier.value,
            "business_existence_check": "FAIL",
            "category_alignment_check": "FAIL",
            "contact_validation_check": "FAIL",
            "location_consistency_check": "FAIL",
            "positive_signals": [],
            "risk_factors": []
        }

        # 1. Entity Type Business Weight
        if entity_type == EntityType.PERSON:
            trace["risk_factors"].append("Kayıt şahıs/doktor profili (PERSON != BUSINESS). Ticari işletme doğrulanmadı.")
            trace["business_existence_check"] = "REJECT_PERSON"
        elif entity_type in (EntityType.CLINIC, EntityType.COMPANY):
            score += 40
            trace["positive_signals"].append(f"Doğrulanmış ticari işletme tipi: {entity_type.value}")
            trace["business_existence_check"] = "PASS"
        elif entity_type == EntityType.BUSINESS:
            score += 35
            trace["positive_signals"].append("Doğrulanmış ticari işletme tipi: BUSINESS")
            trace["business_existence_check"] = "PASS"

        # 2. Source Trust Score
        if source_tier == SourceTrustTier.TIER_1_STRONG:
            score += 25
            trace["positive_signals"].append("Güçlü kaynak (Tier 1: Google Maps / Resmi Web Sitesi)")
        elif source_tier == SourceTrustTier.TIER_2_SUPPORTING:
            score += 20
            trace["positive_signals"].append("Doğrulanmış B2B dizin / OSM kaynağı (Tier 2)")
        else:
            trace["risk_factors"].append("Zayıf/tekil dizin kaydı (Tier 3)")

        # 3. Contact & Phone Validation
        if phone_e164:
            score += 20
            trace["contact_validation_check"] = "PASS"
            trace["positive_signals"].append(f"Formatlanmış iletişim hattı: {phone_e164}")
            if is_mobile:
                score += 5
                trace["positive_signals"].append("WhatsApp uyumlu mobil GSM hattı")
        else:
            trace["risk_factors"].append("Telefon numarası eksik")

        # 4. Physical Address Validation
        if raw_address and len(raw_address.strip()) > 8:
            score += 15
            trace["location_consistency_check"] = "PASS"
            trace["positive_signals"].append(f"Fiziksel adres mevcut: {raw_address[:45]}")
        else:
            trace["risk_factors"].append("Fiziksel açık adres yetersiz")

        # 5. Official Website Validation
        if has_website:
            score += 10
            trace["positive_signals"].append(f"Aktif web sitesi mevcut: {website}")
        else:
            trace["risk_factors"].append("Web sitesi bulunamadı (Opsiyonel kanıt)")

        # 6. Category Alignment Gate
        norm_target = normalize_turkish(target_category)
        is_clinic_target = any(k in norm_target for k in ["klinik", "dis", "diş", "sac", "saç", "poliklinik"])
        
        if is_clinic_target and entity_type == EntityType.PERSON:
            trace["category_alignment_check"] = "REJECT_PERSON_NOT_CLINIC"
            score = min(score, 35)  # Cap score for person records
        else:
            trace["category_alignment_check"] = "PASS"

        # Determine Final Status & Confidence Level
        if entity_type == EntityType.PERSON or score < 50:
            verification_status = VerificationStatus.UNVERIFIED
            confidence_level = ConfidenceLevel.LOW
            is_verified = False
        elif score >= 70:
            verification_status = VerificationStatus.VERIFIED
            confidence_level = ConfidenceLevel.HIGH
            is_verified = True
        else:
            verification_status = VerificationStatus.VERIFIED
            confidence_level = ConfidenceLevel.MEDIUM
            is_verified = True

        trace["confidence_score"] = score
        trace["confidence_level"] = confidence_level.value
        trace["verification_status"] = verification_status.value

        return {
            "entity_type": entity_type.value,
            "verification_status": verification_status.value,
            "confidence_level": confidence_level.value,
            "confidence_score": score,
            "is_verified": is_verified,
            "discovered_from": source,
            "verified_by": "Official Website / Google Maps" if has_website else source,
            "verification_trace": trace
        }
