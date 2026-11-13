"""Duplicate Detection Module.

Explainable and deterministic duplicate detection requiring meaningful textual similarity.
Strictly adheres to core rules:
- Same location alone NEVER establishes a duplicate.
- Time proximity alone NEVER establishes a duplicate.
- Generic shared crisis words ('water', 'flood', 'road', 'building') alone are NEVER sufficient.
- Meaningful textual similarity on informative content is a mandatory prerequisite.
- Explicit forwarded_from relationships establish strong duplicate linkage.
"""

import math
import re
from typing import List, Set, Tuple
from dateutil import parser as date_parser

from ai_engine.schemas.internal import ReportInput
from ai_engine.schemas.analysis import DuplicateMatch, DuplicateInfo

# Generic crisis words that frequently appear in emergency reports
# but alone do NOT indicate identical incident identity.
GENERIC_CRISIS_WORDS: Set[str] = {
    "water", "flood", "flooding", "flooded",
    "building", "buildings", "structure", "structural", "wall", "walls",
    "road", "roads", "street", "streets", "area", "lane", "block", "corner",
    "near", "about", "incident", "emergency", "situation", "reported", "reporting",
    "urgent", "alert", "help", "please", "damage", "people", "call", "called",
    "hazard", "risk", "event", "update", "update:", "zone",
}

# Common English stopwords
STOPWORDS: Set[str] = {
    "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of",
    "with", "is", "are", "was", "were", "it", "its", "by", "from", "as",
    "into", "over", "after", "this", "that", "there", "has", "have", "had",
    "be", "been", "being", "some", "also", "very", "much", "our", "all",
    "can", "could", "will", "would", "should", "not", "only", "just",
}


def _extract_tokens(text: str) -> Set[str]:
    """Extracts cleaned normalized alphanumeric tokens of length > 2."""
    clean_text = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    return {w for w in clean_text.split() if len(w) > 2}


def _haversine_distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculates great-circle distance between two geographic points in meters."""
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


class DuplicateDetector:
    """Deterministic, explainable duplicate detector with strict guardrails."""

    @staticmethod
    def detect_duplicates(
        report: ReportInput,
        context_reports: List[ReportInput],
        duplicate_threshold: float = 0.55,
    ) -> DuplicateInfo:
        """Compares target report against context reports to identify duplicates and reasons.

        Guarantees that location and time only strengthen matches that possess
        genuine textual and semantic similarity.
        """
        matches: List[DuplicateMatch] = []
        tokens_target = _extract_tokens(report.text)
        loc_tokens_target = _extract_tokens(report.location_label) if report.location_label else set()

        try:
            target_time = date_parser.parse(report.reported_at)
        except Exception:
            target_time = None

        for other in context_reports:
            if other.id == report.id:
                continue

            tokens_other = _extract_tokens(other.text)
            loc_tokens_other = _extract_tokens(other.location_label) if other.location_label else set()
            combined_loc_tokens = loc_tokens_target.union(loc_tokens_other)

            reasons: List[str] = []

            # 1. Check explicit forwarded relationship
            is_forwarded_match = (
                (report.forwarded_from is not None and report.forwarded_from == other.id) or
                (other.forwarded_from is not None and other.forwarded_from == report.id)
            )

            # 2. Check location proximity
            same_location = False
            if report.location_label and other.location_label:
                if report.location_label.strip().lower() == other.location_label.strip().lower():
                    same_location = True

            if not same_location and report.lat is not None and report.lng is not None and other.lat is not None and other.lng is not None:
                dist = _haversine_distance_m(report.lat, report.lng, other.lat, other.lng)
                if dist <= 500:
                    same_location = True

            # 3. Check temporal proximity
            time_diff_min = None
            if target_time and other.reported_at:
                try:
                    other_time = date_parser.parse(other.reported_at)
                    time_diff_min = abs(int((target_time - other_time).total_seconds() // 60))
                except Exception:
                    pass

            if is_forwarded_match:
                # Explicit forwarding is direct proof of relationship
                similarity = 0.95
                reasons.append("Direct forwarded marker or reference")
                if same_location:
                    reasons.append("Same location")
                if time_diff_min is not None and time_diff_min <= 10:
                    reasons.append("Within 10 minutes")
                elif time_diff_min is not None and time_diff_min <= 30:
                    reasons.append("Within 30 minutes")

                matches.append(
                    DuplicateMatch(
                        report_id=other.id,
                        similarity=similarity,
                        reasons=reasons,
                    )
                )
                continue

            # 4. Token Overlap & Content Analysis
            content_target = tokens_target - STOPWORDS
            content_other = tokens_other - STOPWORDS

            informative_target = content_target - GENERIC_CRISIS_WORDS - combined_loc_tokens
            informative_other = content_other - GENERIC_CRISIS_WORDS - combined_loc_tokens

            shared_content = content_target.intersection(content_other)
            shared_informative = informative_target.intersection(informative_other)

            union_content = content_target.union(content_other)
            union_informative = informative_target.union(informative_other)

            content_jaccard = len(shared_content) / len(union_content) if union_content else 0.0
            informative_jaccard = len(shared_informative) / len(union_informative) if union_informative else 0.0

            # GUARDRAIL 1: Generic shared words alone must NEVER produce duplicates.
            # There must be at least one shared informative, distinctive token.
            if len(shared_informative) == 0:
                has_meaningful_similarity = False
            else:
                # GUARDRAIL 2: Must exhibit genuine textual similarity.
                # Either strong content Jaccard (>= 0.35) with at least 1 informative term,
                # or solid informative Jaccard (>= 0.25) with at least 2 informative terms,
                # or near-identical text overall (>= 0.70).
                has_meaningful_similarity = (
                    (content_jaccard >= 0.35 and len(shared_informative) >= 1) or
                    (informative_jaccard >= 0.25 and len(shared_informative) >= 2) or
                    (content_jaccard >= 0.70)
                )

            # GUARDRAILS 3 & 4: If meaningful textual similarity is absent,
            # location and time bonuses are STRICTLY WITHHELD.
            if not has_meaningful_similarity:
                # Unrelated reports (even if at same location & time) are rejected
                continue

            # Compute similarity based on text, strengthened by location and time
            base_similarity = 0.50 * content_jaccard + 0.30 * informative_jaccard
            loc_boost = 0.20 if same_location else 0.0

            time_boost = 0.0
            if time_diff_min is not None:
                if time_diff_min <= 10:
                    time_boost = 0.10
                elif time_diff_min <= 30:
                    time_boost = 0.05

            computed_sim = round(min(1.0, base_similarity + loc_boost + time_boost), 2)

            if computed_sim >= duplicate_threshold:
                if same_location:
                    reasons.append("Same location")
                if content_jaccard >= 0.30 or informative_jaccard >= 0.20:
                    reasons.append("Similar wording")
                if content_jaccard >= 0.85:
                    reasons.append("Near-identical text")
                if time_diff_min is not None and time_diff_min <= 10:
                    reasons.append("Within 10 minutes")
                elif time_diff_min is not None and time_diff_min <= 30:
                    reasons.append("Within 30 minutes")
                if not reasons:
                    reasons.append("Overlapping disaster context")

                matches.append(
                    DuplicateMatch(
                        report_id=other.id,
                        similarity=computed_sim,
                        reasons=reasons,
                    )
                )

        matches.sort(key=lambda m: m.similarity, reverse=True)
        return DuplicateInfo(
            is_duplicate=len(matches) > 0,
            matches=matches,
        )
