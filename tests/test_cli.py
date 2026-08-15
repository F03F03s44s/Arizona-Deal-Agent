"""CLI usage tests for `python -m app`."""

import json

import pytest

from app.cli import run


def test_default_run_prints_recommendation_and_table():
    output = run([])
    assert "Arizona Deal Agent" in output
    assert "Recommendation:" in output
    assert "Budget: $15,000" in output
    assert "Profit weight: 0.60" in output
    assert "Estate-sale tool collection (Tempe)" in output
    assert "Fixer-upper mobile home (Mesa)" in output


def test_json_flag_returns_rank_payload():
    payload = json.loads(run(["--json"]))
    assert payload["budget"] == 15000
    assert payload["recommendation"]["within_budget"] is True
    assert len(payload["ranked"]) >= 1


def test_tight_budget_excludes_expensive_recommendation():
    output = run(["--budget", "2000", "--profit-weight", "0.5"])
    assert "mobile home" not in output.split("Recommendation:", 1)[1].splitlines()[0].lower()
    assert "over" in output


def test_rejects_invalid_weight():
    with pytest.raises(SystemExit):
        run(["--profit-weight", "1.5"])


def test_rejects_non_positive_budget():
    with pytest.raises(SystemExit):
        run(["--budget", "0"])
