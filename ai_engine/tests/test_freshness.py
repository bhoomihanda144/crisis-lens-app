"""Tests for Freshness Analysis module."""

from datetime import datetime, timezone, timedelta
from ai_engine.schemas.enums import FreshnessStatus
from ai_engine.modules.freshness import FreshnessAnalyzer


def test_freshness_recent():
    ref_time = datetime(2026, 11, 12, 14, 0, 0, tzinfo=timezone.utc)
    # 25 minutes ago
    rep_time = (ref_time - timedelta(minutes=25)).strftime("%Y-%m-%dT%H:%M:%SZ")

    info = FreshnessAnalyzer.calculate_freshness(rep_time, reference_time=ref_time)
    assert info.status == FreshnessStatus.RECENT
    assert info.age_minutes == 25
    assert info.last_updated == rep_time


def test_freshness_boundary_60_min():
    ref_time = datetime(2026, 11, 12, 14, 0, 0, tzinfo=timezone.utc)
    # Exactly 60 minutes ago -> recent
    rep_time = (ref_time - timedelta(minutes=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
    info = FreshnessAnalyzer.calculate_freshness(rep_time, reference_time=ref_time)
    assert info.status == FreshnessStatus.RECENT
    assert info.age_minutes == 60


def test_freshness_aging():
    ref_time = datetime(2026, 11, 12, 14, 0, 0, tzinfo=timezone.utc)
    # 95 minutes ago -> aging (61 to 240)
    rep_time = (ref_time - timedelta(minutes=95)).strftime("%Y-%m-%dT%H:%M:%SZ")
    info = FreshnessAnalyzer.calculate_freshness(rep_time, reference_time=ref_time)
    assert info.status == FreshnessStatus.AGING
    assert info.age_minutes == 95


def test_freshness_boundary_240_min():
    ref_time = datetime(2026, 11, 12, 14, 0, 0, tzinfo=timezone.utc)
    # Exactly 240 minutes ago -> aging
    rep_time = (ref_time - timedelta(minutes=240)).strftime("%Y-%m-%dT%H:%M:%SZ")
    info = FreshnessAnalyzer.calculate_freshness(rep_time, reference_time=ref_time)
    assert info.status == FreshnessStatus.AGING
    assert info.age_minutes == 240


def test_freshness_stale():
    ref_time = datetime(2026, 11, 12, 14, 0, 0, tzinfo=timezone.utc)
    # 310 minutes ago -> stale (> 240)
    rep_time = (ref_time - timedelta(minutes=310)).strftime("%Y-%m-%dT%H:%M:%SZ")
    info = FreshnessAnalyzer.calculate_freshness(rep_time, reference_time=ref_time)
    assert info.status == FreshnessStatus.STALE
    assert info.age_minutes == 310
