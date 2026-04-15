"""Tests for core/anomaly.py"""
from core.anomaly import AnomalyDetector


def test_no_anomaly_normal():
    d = AnomalyDetector()
    result = d.record("hello world")
    assert not result.detected


def test_burst_detection():
    d = AnomalyDetector(burst_window=100.0, burst_limit=5)
    for _ in range(6):
        result = d.record("event")
    assert result.detected
    assert result.pattern == "burst"


def test_loop_detection():
    d = AnomalyDetector()
    for _ in range(4):
        result = d.record("exactly the same content")
    assert result.detected
    assert result.pattern == "loop"
