"""Source Independence and Corroboration Analysis Module.

Strictly enforces CrisisLens API Contract v1.0 and intelligence integrity rules:
1. If forwarded_from is present, independence must be "forwarded".
2. If explicit forwarding language is detected, independence must be "forwarded".
3. Do not automatically classify citizen, news, official, responder, or sensor reports
   as independent solely because of their source_type.
4. If provenance is insufficient, use independence = "unknown".
5. Forwarded reports must NEVER increase independent corroboration counts.
6. Only count corroboration when there is defensible evidence that the reports have independent origins.
7. Set original_report_id only when an explicit forwarding reference or reliable provenance identifies the original.
8. Never assume the most similar report is the original. If unestablished, return null (None).
"""

import re
from typing import List, Optional
from ai_engine.schemas.enums import (
    Independence,
    CorroborationStatus,
    RelationshipType,
)
from ai_engine.schemas.internal import ReportInput
from ai_engine.schemas.analysis import (
    DuplicateInfo,
    RelatedReport,
    SourceVerification,
)

FORWARD_PATTERNS = [
    r"^fwd[:\s-]",
    r"\bfwd\b",
    r"\bforwarded\b",
    r"\bplease share\b",
    r"\bshare to help\b",
    r"\bcirculating on\b",
    r"\bforwarded message\b",
]


class SourceIndependenceAnalyzer:
    """Analyzes report independence, original report linkage, and corroboration."""

    @staticmethod
    def is_forwarded_text(text: str) -> bool:
        """Detects whether text contains explicit forwarding markers or language."""
        lower = text.lower().strip()
        for pattern in FORWARD_PATTERNS:
            if re.search(pattern, lower):
                return True
        return False

    @staticmethod
    def extract_forwarded_reference_id(text: str) -> Optional[str]:
        """Extracts an explicitly referenced report ID from forwarding text if present."""
        match = re.search(r"\b(?:from|ref|parent|original)[:\s]+(rpt_\w+)\b", text, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    @classmethod
    def has_defensible_independent_provenance(cls, report: ReportInput) -> bool:
        """Checks if a report provides defensible evidence of independent origin.

        Rule: Do not assume independence based solely on source_type.
        Requires explicit verifiable provenance metadata or authenticated credentials.
        """
        # If forwarded, origin is by definition not independent
        if bool(report.forwarded_from) or cls.is_forwarded_text(report.text):
            return False

        # Check for explicit provenance credential or established independent flag
        if report.provenance:
            prov = report.provenance.strip().lower()
            if prov in ["independent", "verified", "authenticated", "firsthand"]:
                return True

        return False

    @classmethod
    def analyze_source(
        cls,
        report: ReportInput,
        duplicate_info: DuplicateInfo,
        context_reports: List[ReportInput],
        has_conflicts: bool = False,
    ) -> SourceVerification:
        """Determines source independence, original report ID, and corroboration status."""
        is_forwarded = bool(report.forwarded_from) or cls.is_forwarded_text(report.text)

        # 1. Determine Independence (Rules 1-4)
        if is_forwarded:
            independence = Independence.FORWARDED
        elif cls.has_defensible_independent_provenance(report):
            independence = Independence.INDEPENDENT
        else:
            # Without verifiable provenance, do NOT invent independence. Use UNKNOWN.
            independence = Independence.UNKNOWN

        # 2. Determine Original Report ID (Rules 7-8)
        # Set original_report_id ONLY when an explicit forwarding reference or provenance identifies it.
        # Never assume the most similar report is the original.
        original_id: Optional[str] = None
        if report.forwarded_from:
            original_id = report.forwarded_from
        elif is_forwarded:
            ref_id = cls.extract_forwarded_reference_id(report.text)
            if ref_id:
                original_id = ref_id
            else:
                original_id = None
        else:
            # Non-forwarded reports do NOT adopt another similar report as their "original"
            original_id = None

        # 3. Build Related List and Evaluate Corroboration
        context_by_id = {r.id: r for r in context_reports}
        related: List[RelatedReport] = []
        defensible_independent_matches = 0

        for m in duplicate_info.matches:
            other = context_by_id.get(m.report_id)
            other_is_forwarded = False
            other_has_independent_provenance = False

            if other:
                other_is_forwarded = bool(other.forwarded_from) or cls.is_forwarded_text(other.text)
                other_has_independent_provenance = cls.has_defensible_independent_provenance(other)

            if is_forwarded or other_is_forwarded:
                rel = RelationshipType.FORWARDED
            elif m.similarity >= 0.8:
                rel = RelationshipType.DUPLICATE
            else:
                rel = RelationshipType.CORROBORATING

            related.append(RelatedReport(report_id=m.report_id, relation=rel))

            # Rules 5 & 6:
            # - Forwarded reports must NEVER increase independent corroboration counts.
            # - Only count corroboration when there is defensible evidence that the reports have independent origins.
            if (not is_forwarded and
                not other_is_forwarded and
                independence == Independence.INDEPENDENT and
                other_has_independent_provenance and
                m.similarity >= 0.50):
                defensible_independent_matches += 1

        # 4. Determine Corroboration Status
        if has_conflicts:
            corroboration = CorroborationStatus.DISPUTED
        elif is_forwarded:
            corroboration = CorroborationStatus.SINGLE_SOURCE
        elif defensible_independent_matches > 0:
            corroboration = CorroborationStatus.CORROBORATED
        else:
            corroboration = CorroborationStatus.SINGLE_SOURCE

        return SourceVerification(
            independence=independence,
            original_report_id=original_id,
            related=related,
            corroboration_status=corroboration,
        )
