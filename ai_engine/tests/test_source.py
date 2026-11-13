"""Tests for Source Independence and Corroboration module."""

from ai_engine.schemas.enums import Independence, CorroborationStatus
from ai_engine.schemas.internal import ReportInput
from ai_engine.schemas.analysis import DuplicateInfo, DuplicateMatch
from ai_engine.modules.source import SourceIndependenceAnalyzer


def test_forwarded_text_markers():
    assert SourceIndependenceAnalyzer.is_forwarded_text("FWD: Emergency flood alert") is True
    assert SourceIndependenceAnalyzer.is_forwarded_text("Please share to help families") is True
    assert SourceIndependenceAnalyzer.is_forwarded_text("Forwarded message from group") is True
    assert SourceIndependenceAnalyzer.is_forwarded_text("Water level is rising at bridge") is False


def test_citizen_report_insufficient_provenance_is_unknown():
    """B.1: Citizen report with insufficient provenance should have independence = unknown."""
    rep = ReportInput(
        id="rpt_cit",
        text="Water entering ground floor houses on Lake Road.",
        source_type="citizen",
        source_name="Citizen reporter A",
        location_label="Lake Road, Bellandur",
        reported_at="2026-11-11T14:00:00Z",
    )
    dup_info = DuplicateInfo(is_duplicate=False, matches=[])
    ver = SourceIndependenceAnalyzer.analyze_source(rep, dup_info, [])
    assert ver.independence == Independence.UNKNOWN
    assert ver.original_report_id is None


def test_news_report_insufficient_provenance_is_unknown():
    """B.2: News report with insufficient provenance should have independence = unknown."""
    rep = ReportInput(
        id="rpt_news",
        text="Breaking: Flooding reported in southern suburbs.",
        source_type="news",
        source_name="City News Wire",
        location_label="Lake Road, Bellandur",
        reported_at="2026-11-11T14:05:00Z",
    )
    dup_info = DuplicateInfo(is_duplicate=False, matches=[])
    ver = SourceIndependenceAnalyzer.analyze_source(rep, dup_info, [])
    assert ver.independence == Independence.UNKNOWN
    assert ver.original_report_id is None


def test_official_report_insufficient_provenance_not_automatically_independent():
    """B.3: Official report with insufficient provenance should not automatically be considered independent."""
    rep = ReportInput(
        id="rpt_off",
        text="Ward officer report: 1.2 m water depth.",
        source_type="official",
        source_name="Ward officer",
        location_label="Lake Road, Bellandur",
        reported_at="2026-11-11T14:10:00Z",
    )
    dup_info = DuplicateInfo(is_duplicate=False, matches=[])
    ver = SourceIndependenceAnalyzer.analyze_source(rep, dup_info, [])
    assert ver.independence == Independence.UNKNOWN
    assert ver.original_report_id is None


def test_forwarded_report_does_not_count_as_corroboration():
    """B.4: Forwarded reports must NEVER increase independent corroboration counts."""
    fwd_report = ReportInput(
        id="rpt_003",
        text="FWD: Water entering ground floor houses on Lake Road. Please share!",
        source_type="social_media",
        location_label="Lake Road, Bellandur",
        forwarded_from="rpt_001",
        reported_at="2026-11-11T14:15:00Z",
    )
    prior_report = ReportInput(
        id="rpt_001",
        text="Water entering ground floor houses on Lake Road.",
        source_type="citizen",
        location_label="Lake Road, Bellandur",
        reported_at="2026-11-11T14:00:00Z",
        provenance="independent",
    )

    dup_info = DuplicateInfo(
        is_duplicate=True,
        matches=[DuplicateMatch(report_id="rpt_001", similarity=0.95, reasons=["Direct forwarded reference"])],
    )

    ver = SourceIndependenceAnalyzer.analyze_source(
        report=fwd_report,
        duplicate_info=dup_info,
        context_reports=[prior_report],
    )

    assert ver.independence == Independence.FORWARDED
    assert ver.original_report_id == "rpt_001"
    # Forwarded report never corroborates
    assert ver.corroboration_status == CorroborationStatus.SINGLE_SOURCE


def test_two_reports_with_defensible_independent_origins_corroborate():
    """B.5: Two reports with defensibly independent origins may be corroborated."""
    target = ReportInput(
        id="rpt_002",
        text="Water entering ground floor houses on Lake Road, families moving upstairs.",
        source_type="citizen",
        source_name="Field Witness B",
        location_label="Lake Road, Bellandur",
        reported_at="2026-11-11T14:13:00Z",
        provenance="independent",
    )
    prior = ReportInput(
        id="rpt_001",
        text="Water entering ground floor houses on Lake Road, people moving upstairs.",
        source_type="citizen",
        source_name="Field Witness A",
        location_label="Lake Road, Bellandur",
        reported_at="2026-11-11T14:00:00Z",
        provenance="independent",
    )

    dup_info = DuplicateInfo(
        is_duplicate=True,
        matches=[DuplicateMatch(report_id="rpt_001", similarity=0.85, reasons=["Same location", "Similar wording"])],
    )

    ver = SourceIndependenceAnalyzer.analyze_source(
        report=target,
        duplicate_info=dup_info,
        context_reports=[prior],
    )

    assert ver.independence == Independence.INDEPENDENT
    assert ver.corroboration_status == CorroborationStatus.CORROBORATED
    # Neither report is forwarded, so original_report_id must remain null
    assert ver.original_report_id is None


def test_similar_non_forwarded_reports_do_not_produce_original_id():
    """C.1 & C.3: Similar non-forwarded reports must not automatically produce original_report_id (must be None/null)."""
    target = ReportInput(
        id="rpt_002",
        text="Lake Road is flooding, water entering ground floor houses.",
        source_type="citizen",
        location_label="Lake Road, Bellandur",
        reported_at="2026-11-11T14:13:00Z",
    )
    prior = ReportInput(
        id="rpt_001",
        text="Water entering ground floor houses on Lake Road.",
        source_type="citizen",
        location_label="Lake Road, Bellandur",
        reported_at="2026-11-11T14:00:00Z",
    )

    dup_info = DuplicateInfo(
        is_duplicate=True,
        matches=[DuplicateMatch(report_id="rpt_001", similarity=0.91, reasons=["Same location", "Similar wording"])],
    )

    ver = SourceIndependenceAnalyzer.analyze_source(
        report=target,
        duplicate_info=dup_info,
        context_reports=[prior],
    )

    # Must NOT assume rpt_001 is the original just because it is similar
    assert ver.original_report_id is None


def test_explicit_forwarded_from_identifies_original_id():
    """C.2: Explicit forwarded_from reference must correctly identify the original report."""
    target = ReportInput(
        id="rpt_003",
        text="FWD: Water entering ground floor houses on Lake Road.",
        source_type="social_media",
        location_label="Lake Road, Bellandur",
        forwarded_from="rpt_001",
        reported_at="2026-11-11T14:15:00Z",
    )
    prior = ReportInput(
        id="rpt_001",
        text="Water entering ground floor houses on Lake Road.",
        source_type="citizen",
        location_label="Lake Road, Bellandur",
        reported_at="2026-11-11T14:00:00Z",
    )

    dup_info = DuplicateInfo(
        is_duplicate=True,
        matches=[DuplicateMatch(report_id="rpt_001", similarity=0.95, reasons=["Direct forwarded reference"])],
    )

    ver = SourceIndependenceAnalyzer.analyze_source(
        report=target,
        duplicate_info=dup_info,
        context_reports=[prior],
    )

    assert ver.original_report_id == "rpt_001"
    assert ver.independence == Independence.FORWARDED
