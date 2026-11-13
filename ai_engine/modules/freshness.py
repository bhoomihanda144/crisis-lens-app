"""Freshness Analysis Module.

Calculates report age and categorizes freshness strictly according to
CrisisLens API Contract v1.0 Section 2:
- recent: age <= 60 min
- aging: 61–240 min
- stale: > 240 min
"""

from datetime import datetime, timezone
from typing import Optional
from dateutil import parser as date_parser

from ai_engine.schemas.enums import FreshnessStatus
from ai_engine.schemas.analysis import FreshnessInfo


class FreshnessAnalyzer:
    """Deterministic, contract-compliant freshness analyzer."""

    @staticmethod
    def calculate_freshness(
        reported_at_str: str,
        reference_time: Optional[datetime] = None,
    ) -> FreshnessInfo:
        """Computes age in minutes and maps to contract FreshnessStatus."""
        if not reference_time:
            reference_time = datetime.now(timezone.utc)
        elif reference_time.tzinfo is None:
            reference_time = reference_time.replace(tzinfo=timezone.utc)

        try:
            reported_at = date_parser.parse(reported_at_str)
            if reported_at.tzinfo is None:
                reported_at = reported_at.replace(tzinfo=timezone.utc)
            else:
                reported_at = reported_at.astimezone(timezone.utc)
        except Exception:
            reported_at = reference_time

        delta = reference_time - reported_at
        age_minutes = max(0, int(delta.total_seconds() // 60))

        if age_minutes <= 60:
            status = FreshnessStatus.RECENT
        elif age_minutes <= 240:
            status = FreshnessStatus.AGING
        else:
            status = FreshnessStatus.STALE

        # Format last_updated as ISO 8601 in UTC
        last_updated_iso = reported_at.strftime("%Y-%m-%dT%H:%M:%SZ")

        return FreshnessInfo(
            status=status,
            age_minutes=age_minutes,
            last_updated=last_updated_iso,
        )
