"""
Discovery Budget & Resource Guard for Business Discovery Engine V3.
Enforces limits on total requests, pages, runtime, and API calls to prevent infinite loops and rate limiting.
"""
import time
import logging
from typing import Dict, Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DiscoveryBudget(BaseModel):
    max_requests: int = 150
    max_pages_per_slug: int = 10
    max_runtime_seconds: int = 120
    max_candidates: int = 1000

    requests_made: int = 0
    pages_visited: int = 0
    start_time: float = Field(default_factory=time.time)

    def record_request(self, pages: int = 1) -> None:
        self.requests_made += 1
        self.pages_visited += pages

    def is_exhausted(self, candidate_count: int = 0) -> bool:
        elapsed = time.time() - self.start_time
        if elapsed > self.max_runtime_seconds:
            logger.warning(f"[DISCOVERY_BUDGET] Runtime limit exceeded ({elapsed:.1f}s > {self.max_runtime_seconds}s)")
            return True
        if self.requests_made >= self.max_requests:
            logger.warning(f"[DISCOVERY_BUDGET] Request limit exceeded ({self.requests_made} >= {self.max_requests})")
            return True
        if candidate_count >= self.max_candidates:
            logger.info(f"[DISCOVERY_BUDGET] Candidate limit reached ({candidate_count} >= {self.max_candidates})")
            return True
        return False
