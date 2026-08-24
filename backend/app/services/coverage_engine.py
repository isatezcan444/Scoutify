"""
Coverage Engine V3 for Business Discovery Engine.
Tracks multi-provider discovery yield, saturation trends, provider overlap matrix,
and known entity recovery benchmarks.
"""
import logging
from typing import List, Dict, Any, Set, Optional
from backend.app.schemas.intelligence import (
    SearchPlan,
    QueryFamily,
    RoundMetrics,
    CoverageReport,
    CandidateEntity
)
from backend.app.data.turkey_locations import normalize_turkish

logger = logging.getLogger(__name__)


class CoverageEngine:
    """
    V3 Coverage Engine:
    - Provider Overlap & Unique Contribution Matrix
    - Saturation & Marginal Discovery Gain Analyzer
    - Known Entity Recovery Benchmark Tracker
    - Subdivision Coverage & Gap Detection
    """

    def __init__(self, search_plan: SearchPlan):
        self.search_plan = search_plan
        self.round_history: List[RoundMetrics] = []
        self.subdivisions_probed: Set[str] = set()
        self.provider_raw_counts: Dict[str, int] = {}
        self.provider_unique_entities: Dict[str, Set[str]] = {}  # provider -> set(entity_ids)

        self.raw_total = 0
        self.unique_total = 0
        self.category_matches = 0
        self.category_mismatches = 0
        self.location_rejected = 0
        self.qualified_total = 0

    def record_candidate_discovery(
        self,
        provider_name: str,
        entity_id: str,
        is_new: bool
    ) -> None:
        """Tracks provider attribution per candidate."""
        p_name = provider_name.lower()
        self.provider_raw_counts[p_name] = self.provider_raw_counts.get(p_name, 0) + 1

        if p_name not in self.provider_unique_entities:
            self.provider_unique_entities[p_name] = set()
        self.provider_unique_entities[p_name].add(entity_id)

    def record_round(
        self,
        round_number: int,
        query_family: QueryFamily,
        queries_executed: int,
        pages_visited: int,
        raw_candidates_found: int,
        new_candidates_added: int,
        duplicate_candidates: int,
        rejections_count: int,
        subdivisions_in_round: List[str]
    ) -> RoundMetrics:
        """Records metrics for a discovery round."""
        self.raw_total += raw_candidates_found
        self.unique_total += new_candidates_added
        for s in subdivisions_in_round:
            if s:
                self.subdivisions_probed.add(s)

        yield_rate = (new_candidates_added / max(raw_candidates_found, 1)) if raw_candidates_found > 0 else 0.0

        metrics = RoundMetrics(
            round_number=round_number,
            query_family=query_family,
            queries_executed=queries_executed,
            pages_visited=pages_visited,
            raw_candidates_found=raw_candidates_found,
            new_candidates_added=new_candidates_added,
            duplicate_candidates=duplicate_candidates,
            rejections_count=rejections_count,
            discovery_yield_rate=round(yield_rate, 3)
        )
        self.round_history.append(metrics)
        logger.info(
            f"[COVERAGE_V3] Round {round_number} ({query_family.value}): "
            f"Raw={raw_candidates_found}, New={new_candidates_added}, Yield={metrics.discovery_yield_rate:.1%}"
        )
        return metrics

    def compute_provider_overlap_matrix(self) -> Dict[str, Any]:
        """
        Computes NxN overlap matrix between providers and unique solo contributions.
        """
        providers = list(self.provider_unique_entities.keys())
        overlap_matrix: Dict[str, Dict[str, int]] = {p: {} for p in providers}
        unique_contributions: Dict[str, int] = {}

        for p1 in providers:
            set1 = self.provider_unique_entities[p1]
            # Solo unique contribution (entities only found by p1)
            other_entities: Set[str] = set()
            for p2 in providers:
                if p1 != p2:
                    other_entities.update(self.provider_unique_entities[p2])
            unique_contributions[p1] = len(set1 - other_entities)

            for p2 in providers:
                if p1 == p2:
                    overlap_matrix[p1][p2] = len(set1)
                else:
                    set2 = self.provider_unique_entities[p2]
                    overlap_matrix[p1][p2] = len(set1.intersection(set2))

        return {
            "providers": providers,
            "raw_counts": self.provider_raw_counts,
            "unique_counts": {p: len(ents) for p, ents in self.provider_unique_entities.items()},
            "solo_unique_contributions": unique_contributions,
            "overlap_matrix": overlap_matrix
        }

    def evaluate_known_entities(
        self,
        all_entities: List[CandidateEntity],
        known_benchmarks: List[str]
    ) -> Dict[str, Any]:
        """
        Evaluates Known Entity Recovery rate against a golden benchmark list.
        """
        if not known_benchmarks:
            return {"total": 0, "recovered": 0, "recall_rate": 1.0, "recovered_names": [], "missed_names": []}

        recovered: List[str] = []
        missed: List[str] = []

        all_names_norm = {normalize_turkish(e.primary_name): e for e in all_entities}
        for e in all_entities:
            for v in e.name_variations:
                all_names_norm[normalize_turkish(v)] = e

        for kb in known_benchmarks:
            norm_kb = normalize_turkish(kb)
            found = False
            for entity_norm_name in all_names_norm:
                if norm_kb in entity_norm_name or entity_norm_name in norm_kb:
                    recovered.append(kb)
                    found = True
                    break
            if not found:
                missed.append(kb)

        recall = (len(recovered) / len(known_benchmarks)) if known_benchmarks else 0.0
        return {
            "total": len(known_benchmarks),
            "recovered": len(recovered),
            "recall_rate": round(recall, 3),
            "recovered_names": recovered,
            "missed_names": missed
        }

    def should_terminate_early(
        self,
        current_round: int,
        target_limit: int = 0
    ) -> bool:
        """
        Adaptive saturation and early termination evaluation.
        """
        if target_limit > 0 and self.qualified_total >= target_limit:
            logger.info(f"[COVERAGE_V3] Target lead limit of {target_limit} reached.")
            return True

        if current_round >= 3 and len(self.round_history) >= 2:
            last_two_new = [r.new_candidates_added for r in self.round_history[-2:]]
            if sum(last_two_new) == 0:
                logger.info("[COVERAGE_V3] Discovery saturated (0 new candidates in last 2 rounds).")
                return True

        if current_round >= 4 and len(self.round_history) >= 3:
            recent_yields = [r.discovery_yield_rate for r in self.round_history[-2:]]
            avg_yield = sum(recent_yields) / len(recent_yields)
            if avg_yield < 0.02:
                logger.info(f"[COVERAGE_V3] Marginal gain below 2% ({avg_yield:.1%}). Terminating.")
                return True

        return False

    def build_report(self) -> CoverageReport:
        families_covered = list({r.query_family for r in self.round_history})
        total_queries = sum(r.queries_executed for r in self.round_history)

        diminishing = False
        if len(self.round_history) >= 3:
            last_yield = self.round_history[-1].discovery_yield_rate
            if last_yield < 0.05:
                diminishing = True

        return CoverageReport(
            total_rounds=len(self.round_history),
            total_queries=total_queries,
            query_families_covered=families_covered,
            subdivisions_covered=list(self.subdivisions_probed),
            subdivisions_total=len(self.subdivisions_probed),
            subdivision_coverage_pct=100.0 if self.subdivisions_probed else 0.0,
            raw_candidates_total=self.raw_total,
            unique_entities_total=self.unique_total,
            category_matches=self.category_matches,
            category_mismatches=self.category_mismatches,
            location_rejected=self.location_rejected,
            qualified_leads_total=self.qualified_total,
            diminishing_returns_reached=diminishing,
            round_history=self.round_history
        )
