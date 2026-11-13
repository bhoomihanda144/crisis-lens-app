"""Tests for Duplicate Detection module with strict false-positive prevention."""

from ai_engine.schemas.internal import ReportInput
from ai_engine.modules.duplicate import DuplicateDetector


def test_same_location_different_emergency_not_duplicate():
    """A.1: Same location but completely different emergency descriptions must NOT be duplicates."""
    flood_report = ReportInput(
        id="rpt_flood",
        text="Severe basement flooding and rising water entering homes on Lake Road.",
        source_type="citizen",
        location_label="Lake Road, Bellandur",
        lat=12.9304,
        lng=77.6784,
        reported_at="2026-11-11T14:15:00Z",
    )
    fire_report = ReportInput(
        id="rpt_fire",
        text="Sparking power line and an electrical transformer fire on Lake Road.",
        source_type="citizen",
        location_label="Lake Road, Bellandur",
        lat=12.9304,
        lng=77.6784,
        reported_at="2026-11-11T14:15:00Z",
    )

    result = DuplicateDetector.detect_duplicates(flood_report, [fire_report])
    assert result.is_duplicate is False
    assert len(result.matches) == 0


def test_same_location_and_time_unrelated_text_not_duplicate():
    """A.2: Same location and time but unrelated report text must NOT be duplicates."""
    medical_report = ReportInput(
        id="rpt_med",
        text="Elderly patient having severe cardiac arrest needing urgent ambulance dispatch.",
        source_type="citizen",
        location_label="4th Block, Koramangala",
        lat=12.9352,
        lng=77.6245,
        reported_at="2026-11-11T14:20:00Z",
    )
    traffic_report = ReportInput(
        id="rpt_traffic",
        text="Fallen tree branch blocking bicycle lane, traffic moving slowly.",
        source_type="citizen",
        location_label="4th Block, Koramangala",
        lat=12.9352,
        lng=77.6245,
        reported_at="2026-11-11T14:20:00Z",
    )

    result = DuplicateDetector.detect_duplicates(medical_report, [traffic_report])
    assert result.is_duplicate is False
    assert len(result.matches) == 0


def test_generic_shared_words_alone_not_duplicate():
    """A.3: Generic shared words such as 'water', 'building', 'road', or 'flood' alone must NOT produce duplicates."""
    generic_a = ReportInput(
        id="rpt_gen_a",
        text="Water flood on road near building emergency situation.",
        source_type="citizen",
        location_label="Lake Road, Bellandur",
        reported_at="2026-11-11T14:00:00Z",
    )
    generic_b = ReportInput(
        id="rpt_gen_b",
        text="Building near road reported flood water incident.",
        source_type="citizen",
        location_label="Lake Road, Bellandur",
        reported_at="2026-11-11T14:02:00Z",
    )

    result = DuplicateDetector.detect_duplicates(generic_a, [generic_b])
    # Must NOT produce duplicate matches despite identical generic words and location
    assert result.is_duplicate is False
    assert len(result.matches) == 0


def test_strongly_similar_reports_detected_as_duplicates():
    """A.4: Strongly similar reports with close locations and times should be detected as likely duplicates."""
    target = ReportInput(
        id="rpt_002",
        text="Water entering ground floor houses on Lake Road, families moving upstairs.",
        source_type="citizen",
        source_name="Citizen reporter B",
        location_label="Lake Road, Bellandur",
        lat=12.9304,
        lng=77.6784,
        reported_at="2026-11-11T14:13:00Z",
    )
    prior = ReportInput(
        id="rpt_001",
        text="Water entering ground floor houses on Lake Road, people moving upstairs.",
        source_type="citizen",
        source_name="Citizen reporter A",
        location_label="Lake Road, Bellandur",
        lat=12.9304,
        lng=77.6784,
        reported_at="2026-11-11T14:05:00Z",
    )

    result = DuplicateDetector.detect_duplicates(target, [prior])
    assert result.is_duplicate is True
    assert len(result.matches) == 1
    match = result.matches[0]
    assert match.report_id == "rpt_001"
    assert match.similarity >= 0.70
    assert "Same location" in match.reasons
    assert "Similar wording" in match.reasons
    assert "Within 10 minutes" in match.reasons


def test_explicit_forwarded_from_relationship():
    """A.5: Explicit forwarded_from relationships must be detected correctly."""
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

    result = DuplicateDetector.detect_duplicates(target, [prior])
    assert result.is_duplicate is True
    assert len(result.matches) == 1
    assert result.matches[0].report_id == "rpt_001"
    assert "Direct forwarded marker or reference" in result.matches[0].reasons
    assert result.matches[0].similarity >= 0.95


def test_duplicate_detection_unrelated_locations():
    """Different locations and unrelated text must not be duplicates."""
    target = ReportInput(
        id="rpt_whitefield",
        text="Sparking transformer near bus stop on Main Road Whitefield.",
        source_type="citizen",
        location_label="Main Road, Whitefield",
        lat=12.9698,
        lng=77.75,
        reported_at="2026-11-11T14:13:00Z",
    )
    prior = ReportInput(
        id="rpt_bellandur",
        text="Water entering ground floor houses on Lake Road Bellandur.",
        source_type="citizen",
        location_label="Lake Road, Bellandur",
        lat=12.9304,
        lng=77.6784,
        reported_at="2026-11-11T14:05:00Z",
    )

    result = DuplicateDetector.detect_duplicates(target, [prior])
    assert result.is_duplicate is False
    assert len(result.matches) == 0
