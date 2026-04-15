"""Tests for core/policy.py"""
from core.policy import PolicyEngine


def test_policy_allows_benign():
    p = PolicyEngine()
    result = p.check("print('hello world')")
    assert result.allowed


def test_policy_denies_rm_rf():
    p = PolicyEngine()
    result = p.check("rm -rf /")
    assert not result.allowed
    assert "deny-list" in result.reason


def test_policy_denies_over_budget():
    p = PolicyEngine(max_cost_usd=0.01)
    p.record_usage(100, 0.02)
    result = p.check("anything")
    assert not result.allowed
    assert "cost ceiling" in result.reason
