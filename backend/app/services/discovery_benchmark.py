"""
Ground Truth Benchmark Datasets & Known Entity Recovery Engine for Business Discovery Engine V3.
Provides golden positive and negative ground-truth entities across sectors to measure real recall and precision.
"""
from typing import Dict, List, Any
from pydantic import BaseModel


class BenchmarkTarget(BaseModel):
    category_id: str
    city: str
    district: str
    known_positives: List[str]
    known_negatives: List[str]


GOLDEN_BENCHMARKS: Dict[str, BenchmarkTarget] = {
    "dental_atasehir": BenchmarkTarget(
        category_id="dental",
        city="İstanbul",
        district="Ataşehir",
        known_positives=[
            "7dent", "Dentbien", "Dentopia", "ProDenta", "Smileart",
            "Rotadent", "İçerenköy Diş", "G.İ.S. Ağız ve Diş", "Özel Esatpaşa Ağız ve Diş", "Tekdent", "Pi Dent"
        ],
        known_negatives=[
            "Atakent Pet Shop", "Adalet Hukuk Bürosu", "Boğaziçi Kebap",
            "Wes Dış Ticaret", "Merry Dolci Pasta", "Asus Aydınlatma", "Little Caesars Pizza"
        ]
    ),
    "furniture_umraniye": BenchmarkTarget(
        category_id="furniture",
        city="İstanbul",
        district="Ümraniye",
        known_positives=[
            "Hafele Mobilya", "Mirage Modoko", "Piya Ahşap", "Sözen Mobilya",
            "Özşafak Mobilya", "Dekor Ofis Mobilyaları", "Asido Koltuk", "DK Koltuk Tasarim"
        ],
        known_negatives=[
            "Atakent Pet Shop", "Merry Dolci Tasarım Pasta", "Tatlıcı", "Veteriner", "Diş Kliniği", "Burcu Demiralp"
        ]
    ),
    "pet_kadikoy": BenchmarkTarget(
        category_id="pet_services",
        city="İstanbul",
        district="Kadıköy",
        known_positives=[
            "Moda Petshop", "Empati Petshop", "Erenköy Petshop", "Doğasan Akvaryum"
        ],
        known_negatives=[
            "Kadıköy Mobilya Showroom", "Diş Hekimi Muayenehanesi", "Pastane", "Hukuk Bürosu"
        ]
    ),
    "solar_kadikoy": BenchmarkTarget(
        category_id="dynamic_gunes_paneli_ve_yenilenebilir_en",
        city="İstanbul",
        district="Kadıköy",
        known_positives=[
            "Zeta Enerji", "Transmer Enerji", "Solis Continuum", "Bek Teknik Enerji", "Orge Enerji", "Daf Enerji"
        ],
        known_negatives=[
            "Pet Shop", "Pastane", "Diş Kliniği", "Mobilya Mağazası"
        ]
    )
}


def get_benchmark_for_target(canonical_category: str, district: str) -> List[str]:
    """Retrieves list of known positive entities for benchmarking."""
    key = f"{canonical_category}_{district.lower()}"
    bm = GOLDEN_BENCHMARKS.get(key)
    if bm:
        return bm.known_positives
    # Fallback to category prefix lookup
    for k, v in GOLDEN_BENCHMARKS.items():
        if canonical_category in k and district.lower() in k:
            return v.known_positives
    return []
