"""
Category Recommendation & Intelligence Engine.
Analyzes user offer, service value proposition, and business goals to discover
and rank candidate B2B target categories with explainable rationales.
"""
import re
import logging
from typing import List, Dict, Any, Optional, Set
from backend.app.schemas.smart_outreach import (
    DiscoveredCategory,
    CategoryFitLevel,
    CategorySource,
    BusinessGoal,
    CategoryRecommendationRequest,
    CategoryRecommendationResponse
)
from backend.app.services.taxonomy_registry import TaxonomyRegistry
from backend.app.data.turkey_locations import normalize_turkish

logger = logging.getLogger(__name__)


class CategoryRecommendationService:
    """
    Intelligent B2B Category Recommendation Engine:
    Maps user offer and intent to curated target categories with explainable B2B rationales.
    """

    # Domain Knowledge Patterns for rapid, explainable B2B matching
    OFFER_PATTERNS: List[Dict[str, Any]] = [
        {
            "keywords": ["vito", "vip transfer", "transfer", "soforlu arac", "havalimani transfer", "tasimacilik", "servis araci"],
            "categories": [
                {
                    "category_id": "hotels",
                    "display_name": "Oteller & Konaklama Tesisleri",
                    "rationale": "VIP transfer ihtiyacı çok yüksek; otel misafirleri ve havalimanı transferleri için doğrudan dış tedarikçi kullanılır.",
                    "fit_level": CategoryFitLevel.HIGH,
                    "search_keywords": ["otel", "butik otel", "resort otel", "konaklama"]
                },
                {
                    "category_id": "travel_agencies",
                    "display_name": "Turizm & Seyahat Acenteleri",
                    "rationale": "Tur, karşılama ve özel transfer operasyonlarında düzenli araç tedariği yaparlar.",
                    "fit_level": CategoryFitLevel.HIGH,
                    "search_keywords": ["turizm acentesi", "seyahat acentesi", "turizm"]
                },
                {
                    "category_id": "corporate_companies",
                    "display_name": "Kurumsal Şirketler & Holdingler",
                    "rationale": "Üst düzey yönetici, iş ortağı ve yabancı heyet transferleri için özel araç filosu tercih ederler.",
                    "fit_level": CategoryFitLevel.HIGH,
                    "search_keywords": ["holding", "şirket", "kurumsal", "plaza"]
                },
                {
                    "category_id": "private_hospitals",
                    "display_name": "Özel Hastaneler & Sağlık Turizmi",
                    "rationale": "Özellikle sağlık turizmi ve VIP hasta/yakını havalimanı transferlerinde yoğun araç ihtiyacı vardır.",
                    "fit_level": CategoryFitLevel.MEDIUM,
                    "search_keywords": ["özel hastane", "sağlık turizmi", "tıp merkezi"]
                },
                {
                    "category_id": "event_organizers",
                    "display_name": "Düğün & Etkinlik Organizasyonları",
                    "rationale": "Gelin/damat, protokol ve VIP misafir taşımacılığı için dönemsel transfer ihtiyacı duyarlar.",
                    "fit_level": CategoryFitLevel.MEDIUM,
                    "search_keywords": ["düğün organizasyon", "etkinlik organizasyon", "organizasyon"]
                }
            ],
            "custom_suggestions": ["Havalimanı Transfer Firmaları", "Konsolosluklar & Protokol", "Prodüksiyon Şirketleri"]
        },
        {
            "keywords": ["dental", "dis", "dis hekimi", "implant", "ortodonti", "sarf malzeme", "dis deposu"],
            "categories": [
                {
                    "category_id": "dental_clinics",
                    "display_name": "Diş Klinikleri & Muayenehaneler",
                    "rationale": "Sarf malzeme, implant ve klinik ekipmanı tedariğinde doğrudan ana karar verici hedef kitledir.",
                    "fit_level": CategoryFitLevel.HIGH,
                    "search_keywords": ["diş kliniği", "diş hekimi", "dentist"]
                },
                {
                    "category_id": "dental_centers",
                    "display_name": "Ağız ve Diş Sağlığı Merkezleri (ADSM)",
                    "rationale": "Yüksek hasta sirkülasyonu nedeniyle düzenli ve yüksek hacimli sarf malzeme siparişi verirler.",
                    "fit_level": CategoryFitLevel.HIGH,
                    "search_keywords": ["ağız ve diş sağlığı merkezi", "diş polikliniği", "dental center"]
                },
                {
                    "category_id": "orthodontic_clinics",
                    "display_name": "Ortodonti & Çene Cerrahisi Merkezleri",
                    "rationale": "Özel branş tedavileri için niş ve yüksek katma değerli dental malzeme alımı yaparlar.",
                    "fit_level": CategoryFitLevel.HIGH,
                    "search_keywords": ["ortodonti", "çene cerrahisi", "estetik diş"]
                },
                {
                    "category_id": "medical_centers",
                    "display_name": "Özel Poliklinik & Tıp Merkezleri",
                    "rationale": "Bünyelerinde diş ünitesi bulunduran tıp merkezleri için alternatif tedarik kanalıdır.",
                    "fit_level": CategoryFitLevel.MEDIUM,
                    "search_keywords": ["tıp merkezi", "özel poliklinik"]
                }
            ],
            "custom_suggestions": ["Diş Protez Laboratuvarları", "Özel Diş Hastaneleri"]
        },
        {
            "keywords": ["kurye", "paket servis", "filo", "motor kurye", "restoran yazilimi", "pos"],
            "categories": [
                {
                    "category_id": "restaurants",
                    "display_name": "Restoranlar & Lokantalar",
                    "rationale": "Paket servis operasyonlarında kurye maliyetlerini ve filo yönetimini optimize etmeye açıktırlar.",
                    "fit_level": CategoryFitLevel.HIGH,
                    "search_keywords": ["restoran", "lokanta", "kebapçı", "pizzacı"]
                },
                {
                    "category_id": "cafes_bistros",
                    "display_name": "Kafeler & Fast Food Noktaları",
                    "rationale": "Hızlı paket servis ve yoğun saat kurye desteği arayan işletmelerdir.",
                    "fit_level": CategoryFitLevel.HIGH,
                    "search_keywords": ["kafe", "fast food", "burger", "bistro"]
                },
                {
                    "category_id": "bakeries_pastries",
                    "display_name": "Pastane & Tatlıcılar",
                    "rationale": "Özel sipariş teslimatı ve paket dağıtımı yapan yüksek hacimli işletmelerdir.",
                    "fit_level": CategoryFitLevel.MEDIUM,
                    "search_keywords": ["pastane", "tatlıcı", "baklavacı"]
                },
                {
                    "category_id": "catering_companies",
                    "display_name": "Catering & Tabldot Yemek Şirketleri",
                    "rationale": "Kurumsal öğle yemeği ve düzenli sıcak yemek teslimat operasyonları yürütürler.",
                    "fit_level": CategoryFitLevel.HIGH,
                    "search_keywords": ["catering", "tabldot", "yemek şirketi"]
                }
            ],
            "custom_suggestions": ["Bulut Mutfaklar", "Şarküteri & Gurme Marketler"]
        },
        {
            "keywords": ["temizlik", "hijyen", "dezenfeksiyon", "endustriyel temizlik", "tesis yonetimi"],
            "categories": [
                {
                    "category_id": "hotels",
                    "display_name": "Oteller & Tatil Köyleri",
                    "rationale": "Günlük oda hijyeni ve periyodik derin temizlik için düzenli hizmet ve sarf alımı yaparlar.",
                    "fit_level": CategoryFitLevel.HIGH,
                    "search_keywords": ["otel", "tatil köyü", "butik otel"]
                },
                {
                    "category_id": "private_schools",
                    "display_name": "Özel Okullar, Kolejler & Kreşler",
                    "rationale": "Öğrenci sağlığı için düzenli periyodik temizlik ve kurumsal hijyen standartlarına önem verirler.",
                    "fit_level": CategoryFitLevel.HIGH,
                    "search_keywords": ["özel okul", "kolej", "kreş", "anaokulu"]
                },
                {
                    "category_id": "factories",
                    "display_name": "Fabrikalar & İmalathaneler",
                    "rationale": "Geniş zemin temizliği, endüstriyel hijyen ve periyodik bakım hizmeti ararlar.",
                    "fit_level": CategoryFitLevel.HIGH,
                    "search_keywords": ["fabrika", "imalathane", "üretim tesisi", "organize sanayi"]
                },
                {
                    "category_id": "office_plazas",
                    "display_name": "İş Merkezleri & Plazalar",
                    "rationale": "Ortak alan ve kurumsal ofis temizliği için periyodik sözleşmeli hizmet alırlar.",
                    "fit_level": CategoryFitLevel.MEDIUM,
                    "search_keywords": ["iş merkezi", "plaza", "ofis kompleksi"]
                }
            ],
            "custom_suggestions": ["Özel Hastaneler", "AVM Tesis Yönetimleri", "Site Yönetimleri"]
        },
        {
            "keywords": ["yazilim", "web tasarim", "dijital pazarlama", "sosyal medya", "seo", "e-ticaret"],
            "categories": [
                {
                    "category_id": "beauty_centers",
                    "display_name": "Güzellik Merkezleri & Estetik Klinikleri",
                    "rationale": "Müşteri kazanımı için dijital reklam, randevu yazılımı ve sosyal medya yönetimine yüksek bütçe ayırırlar.",
                    "fit_level": CategoryFitLevel.HIGH,
                    "search_keywords": ["güzellik merkezi", "estetik merkezi", "lazer epilasyon"]
                },
                {
                    "category_id": "e_commerce_retail",
                    "display_name": "Perakende & E-Ticaret İşletmeleri",
                    "rationale": "Satış artırıcı entegrasyonlar, web sitesi optimizasyonu ve reklam yönetimi ihtiyaçları süreklidir.",
                    "fit_level": CategoryFitLevel.HIGH,
                    "search_keywords": ["mağaza", "perakende", "butik", "ithalat ihracat"]
                },
                {
                    "category_id": "law_firms",
                    "display_name": "Hukuk & Danışmanlık Büroları",
                    "rationale": "Kurumsal web varlığı, KVKK uyumu ve profesyonel dijital kimlik çözümleri talep ederler.",
                    "fit_level": CategoryFitLevel.MEDIUM,
                    "search_keywords": ["avukat", "hukuk bürosu", "danışmanlık"]
                },
                {
                    "category_id": "furniture_showrooms",
                    "display_name": "Mobilya & Ev Dekorasyon Showroomları",
                    "rationale": "Online katalog, 3D görselleştirme ve bölgesel dijital reklam çözümlerine ihtiyaç duyarlar.",
                    "fit_level": CategoryFitLevel.MEDIUM,
                    "search_keywords": ["mobilya showroom", "mobilyacı", "ev dekorasyon"]
                }
            ],
            "custom_suggestions": ["Gayrimenkul Acenteleri", "Mimarlık Ofisleri", "Özel Kurslar"]
        }
    ]

    @classmethod
    def recommend_categories(cls, request: CategoryRecommendationRequest) -> CategoryRecommendationResponse:
        """
        Processes offer information and returns ordered, normalized candidate categories with rationales.
        """
        TaxonomyRegistry.initialize()
        offer_text = f"{request.offer_title} {request.offer_description or ''} {request.target_sector_hint or ''}"
        norm_offer = normalize_turkish(offer_text.lower())

        matched_categories: List[DiscoveredCategory] = []
        custom_suggestions: List[str] = []
        seen_category_ids: Set[str] = set()

        # 1. Match against curated B2B offer knowledge base
        for pattern in cls.OFFER_PATTERNS:
            pattern_hit = False
            for kw in pattern["keywords"]:
                norm_kw = normalize_turkish(kw)
                if norm_kw in norm_offer:
                    pattern_hit = True
                    break

            if pattern_hit:
                for cat in pattern["categories"]:
                    cat_id = cat["category_id"]
                    if cat_id not in seen_category_ids:
                        seen_category_ids.add(cat_id)
                        matched_categories.append(DiscoveredCategory(
                            category_id=cat_id,
                            display_name=cat["display_name"],
                            rationale=cat["rationale"],
                            fit_level=cat["fit_level"],
                            search_keywords=cat["search_keywords"],
                            source=CategorySource.DISCOVERED,
                            is_recommended=(cat["fit_level"] == CategoryFitLevel.HIGH),
                            estimated_volume="Yüksek" if cat["fit_level"] == CategoryFitLevel.HIGH else "Orta"
                        ))
                custom_suggestions.extend(pattern.get("custom_suggestions", []))

        # 2. If no pattern matches, perform semantic search across TaxonomyRegistry
        if not matched_categories:
            logger.info(f"[CATEGORY_RECOMMENDATION] No predefined pattern for '{request.offer_title}', querying TaxonomyRegistry.")
            tokens = [t for t in re.split(r"\s+", norm_offer) if len(t) > 2]
            for node in TaxonomyRegistry._registry.values():
                node_match_score = 0
                for token in tokens:
                    if token in normalize_turkish(node.display_name.lower()):
                        node_match_score += 3
                    for alias in node.aliases:
                        if token in normalize_turkish(alias.lower()):
                            node_match_score += 2
                    for concept in node.semantic_concepts:
                        if token in normalize_turkish(concept.lower()):
                            node_match_score += 1

                if node_match_score > 0 and node.id not in seen_category_ids:
                    seen_category_ids.add(node.id)
                    fit_level = CategoryFitLevel.HIGH if node_match_score >= 3 else CategoryFitLevel.MEDIUM
                    matched_categories.append(DiscoveredCategory(
                        category_id=node.id,
                        display_name=node.display_name,
                        rationale=f"{request.offer_title} teklifiniz ile '{node.display_name}' sektörel terminolojisi arasında semantik uyum tespit edildi.",
                        fit_level=fit_level,
                        search_keywords=node.aliases[:4] if node.aliases else [node.display_name],
                        source=CategorySource.DISCOVERED,
                        is_recommended=True,
                        estimated_volume="Orta"
                    ))

        # 3. Fallback generic recommendations if still empty
        if not matched_categories:
            generic_fallback = [
                DiscoveredCategory(
                    category_id="corporate_businesses",
                    display_name="KOBİ & Ticari İşletmeler",
                    rationale="Genel B2B hizmet ve ürün tedarik talebi olan bölgesel ticari işletmeler.",
                    fit_level=CategoryFitLevel.HIGH,
                    search_keywords=["işletme", "şirket", "ticaret"],
                    source=CategorySource.DISCOVERED,
                    is_recommended=True,
                ),
                DiscoveredCategory(
                    category_id="consulting_offices",
                    display_name="Kurumsal Ofis & Danışmanlık Firmaları",
                    rationale="Dış hizmet ve ürün tedarikine açık kurumsal ofisler.",
                    fit_level=CategoryFitLevel.MEDIUM,
                    search_keywords=["danışmanlık", "ofis", "hizmet"],
                    source=CategorySource.DISCOVERED,
                    is_recommended=True,
                )
            ]
            matched_categories.extend(generic_fallback)
            custom_suggestions = ["Bölgesel İmalatçılar", "Özel Sağlık Merkezleri"]

        # Sort: HIGH first, then MEDIUM, then LOW
        priority_order = {
            CategoryFitLevel.HIGH: 0,
            CategoryFitLevel.MEDIUM: 1,
            CategoryFitLevel.LOW: 2,
            CategoryFitLevel.ALTERNATIVE: 3
        }
        matched_categories.sort(key=lambda c: priority_order.get(c.fit_level, 99))

        return CategoryRecommendationResponse(
            offer_title=request.offer_title,
            business_goal=request.business_goal or BusinessGoal.DISCOVERY,
            discovered_categories=matched_categories,
            suggested_custom_categories=list(dict.fromkeys(custom_suggestions))[:5]
        )
