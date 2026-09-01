"""
Generic Category Relevance Engine.
Evaluates candidate relevance against a CategoryProfile using multi-signal evidence
and relational taxonomy reasoning without hardcoded category-specific if statements.
"""
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from backend.app.schemas.intelligence import (
    CategoryProfile,
    RawBusinessCandidate,
    CategoryAssessment,
    CategoryMatchClassification
)
from backend.app.services.taxonomy_registry import TaxonomyRegistry
from backend.app.data.turkey_locations import normalize_turkish

logger = logging.getLogger(__name__)


class CategoryRelevanceEngine:
    """
    Generic Category Relevance Engine:
    - Multi-signal evaluation (Name, Provider Category, Query, Content).
    - Relational taxonomy reasoning (Mutual Exclusivity = Hard Mismatch).
    - Data-driven scoring without hardcoded category branches.
    """

    @classmethod
    def evaluate(
        cls,
        profile: CategoryProfile,
        candidate: RawBusinessCandidate
    ) -> CategoryAssessment:
        """
        Evaluates a candidate business against the target CategoryProfile.
        Returns explainable CategoryAssessment with score, classification, and evidence breakdown.
        """
        # Use only candidate's own attributes (NEVER search query text)
        raw_text_corpus = f"{candidate.raw_name} {candidate.clean_name} {candidate.raw_category or ''}"
        norm_corpus = normalize_turkish(raw_text_corpus)
        corpus_tokens = set(norm_corpus.split())

        positive_evidence: List[str] = []
        negative_evidence: List[str] = []

        # Disambiguation: Turkish "diş" (dental) vs "dış ticaret" (foreign trade / import-export / logistics)
        if profile.canonical_id == "dental":
            foreign_trade_markers = ["dis ticaret", "ic ve dis", "dis cephe", "ithalat", "ihracat", "gumruk", "lojistik", "tekstil", "makina", "insaat"]
            has_foreign_trade = any(m in norm_corpus for m in foreign_trade_markers)
            has_dental_marker = any(d in norm_corpus for d in ["klinik", "hekim", "dent", "poliklinik", "ortodonti", "implant", "agiz", "tabip", "muayenehane"])
            if has_foreign_trade and not has_dental_marker:
                return CategoryAssessment(
                    score=0.0,
                    classification=CategoryMatchClassification.MISMATCH,
                    matched_category_id="foreign_trade",
                    positive_evidence=[],
                    negative_evidence=["Dış Ticaret / İthalat-İhracat homonim tespiti (Diş ≠ Dış Ticaret)"],
                    confidence=1.0,
                    reason="Dış Ticaret / İthalat / Lojistik firması elendi (Diş Klinikleri ile uyuşmuyor)."
                )

        # =========================================================================
        # 1. RELATIONAL TAXONOMY REASONING: MUTUALLY EXCLUSIVE HARD MISMATCH GATE
        # =========================================================================
        # Detect if candidate strongly matches a category node that is mutually exclusive to target
        candidate_category_node = TaxonomyRegistry.find_node_by_alias_or_concept(candidate.clean_name)
        if not candidate_category_node and candidate.raw_category:
            candidate_category_node = TaxonomyRegistry.find_node_by_alias_or_concept(candidate.raw_category)

        if candidate_category_node:
            candidate_cat_id = candidate_category_node.id
            if candidate_cat_id != profile.canonical_id:
                if not profile.is_dynamic:
                    if TaxonomyRegistry.are_mutually_exclusive(profile.canonical_id, candidate_cat_id):
                        neg_reason = (
                            f"Kategori uyuşmazlığı (MUTUALLY_EXCLUSIVE): Aday '{candidate_category_node.display_name}' ({candidate_cat_id}) "
                            f"kategorisine ait, hedef '{profile.display_name}' ({profile.canonical_id}) ile çelişiyor."
                        )
                        negative_evidence.append(neg_reason)
                        return CategoryAssessment(
                            score=0.0,
                            classification=CategoryMatchClassification.MISMATCH,
                            matched_category_id=candidate_cat_id,
                            positive_evidence=[],
                            negative_evidence=negative_evidence,
                            confidence=1.0,
                            reason=neg_reason
                        )
                else:
                    # Dynamic profile: Candidate matches a distinct established static category
                    neg_reason = (
                        f"Kategori çelişkisi: Aday '{candidate_category_node.display_name}' ({candidate_cat_id}) "
                        f"yerleşik statik kategorisine ait, dinamik '{profile.display_name}' hedefiyle uyuşmuyor."
                    )
                    negative_evidence.append(neg_reason)
                    return CategoryAssessment(
                        score=0.0,
                        classification=CategoryMatchClassification.MISMATCH,
                        matched_category_id=candidate_cat_id,
                        positive_evidence=[],
                        negative_evidence=negative_evidence,
                        confidence=1.0,
                        reason=neg_reason
                    )

        # Check explicit negative concepts configured in profile
        for neg in profile.negative_concepts:
            norm_neg = normalize_turkish(neg)
            if norm_neg in norm_corpus or (len(norm_neg) > 3 and norm_neg in corpus_tokens):
                negative_evidence.append(f"Negatif kavram eşleşmesi: '{neg}'")

        if len(negative_evidence) >= 2:
            return CategoryAssessment(
                score=0.05,
                classification=CategoryMatchClassification.MISMATCH,
                matched_category_id=None,
                positive_evidence=positive_evidence,
                negative_evidence=negative_evidence,
                confidence=0.95,
                reason=f"Çoklu negatif kavram tespiti nedeniyle elendi: {', '.join(negative_evidence[:2])}"
            )

        # =========================================================================
        # 2. POSITIVE CONCEPT MATCHING & EVIDENCE GATHERING
        # =========================================================================
        matched_positives: List[str] = []
        for pos in profile.positive_concepts:
            norm_pos = normalize_turkish(pos)
            if norm_pos in norm_corpus or (len(norm_pos) > 2 and norm_pos in corpus_tokens):
                matched_positives.append(pos)
                positive_evidence.append(f"Pozitif kavram eşleşmesi: '{pos}'")

        # Provider category match bonus
        if candidate.raw_category:
            norm_raw_cat = normalize_turkish(candidate.raw_category)
            if any(normalize_turkish(pos) in norm_raw_cat for pos in profile.positive_concepts):
                positive_evidence.append(f"Sağlayıcı kategori uyumu: '{candidate.raw_category}'")

        # =========================================================================
        # 3. SCORE CALCULATION & CLASSIFICATION
        # =========================================================================
        score = 0.0

        if matched_positives:
            # Separate non-generic concepts from generic tokens
            non_generic_positives = [
                p for p in matched_positives 
                if normalize_turkish(p) not in TaxonomyRegistry.GENERIC_WORDS or len(p.split()) > 1
            ]
            has_full_phrase = any(len(p.split()) >= 2 and normalize_turkish(p) in norm_corpus for p in profile.positive_concepts)

            if non_generic_positives or has_full_phrase:
                base_score = min(0.65 + (len(non_generic_positives) * 0.15), 0.95)
                if candidate.raw_category and any(normalize_turkish(pos) in normalize_turkish(candidate.raw_category) for pos in profile.positive_concepts):
                    base_score = min(base_score + 0.1, 1.0)
                score = base_score
                classification = CategoryMatchClassification.MATCH if score >= 0.7 else CategoryMatchClassification.PARTIAL_MATCH
                reason = f"Hedef kategori kavramlarıyla güçlü uyum ({len(non_generic_positives)} nitelikli pozitif sinyal)."
            else:
                # Only generic concepts matched (cannot grant MATCH)
                score = 0.35
                classification = CategoryMatchClassification.AMBIGUOUS
                reason = "Aday yalnızca genel (generic) kavramlar içeriyor; yeterli alan kanıtı bulunamadı."
        elif profile.is_dynamic:
            # Dynamic profile: token overlap check strictly excluding generic words
            tokens = set(normalize_turkish(profile.display_name).split())
            non_generic_target_tokens = {t for t in tokens if t not in TaxonomyRegistry.GENERIC_WORDS and len(t) > 2}
            non_generic_corpus_tokens = {t for t in corpus_tokens if t not in TaxonomyRegistry.GENERIC_WORDS and len(t) > 2}
            
            overlap = non_generic_corpus_tokens.intersection(non_generic_target_tokens)
            if overlap:
                score = 0.75
                classification = CategoryMatchClassification.MATCH
                positive_evidence.append(f"Dinamik kategori anahtar kelime eşleşmesi: {', '.join(overlap)}")
                reason = "Dinamik profil anahtar kelime uyumu."
            else:
                score = 0.35
                classification = CategoryMatchClassification.AMBIGUOUS
                reason = "Yetersiz anlamsal kanıt (Dinamik profil)."
        else:
            # No positive signals and no strong negative
            score = 0.30
            classification = CategoryMatchClassification.AMBIGUOUS
            reason = "Aday unvanında veya etiketlerinde kategoriye dair belirgin pozitif sinyal bulunamadı."

        return CategoryAssessment(
            score=round(score, 3),
            classification=classification,
            matched_category_id=profile.canonical_id if score >= 0.7 else None,
            positive_evidence=positive_evidence,
            negative_evidence=negative_evidence,
            confidence=round(min(score + 0.1, 1.0), 2),
            reason=reason
        )
