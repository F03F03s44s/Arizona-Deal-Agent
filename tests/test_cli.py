"""Command-line behaviour."""

from __future__ import annotations

import json

import pytest

from arizona_deal_agent.cli import main


def run(capsys, argv):
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_rank_prints_a_table(capsys, listings_csv):
    code, out, _ = run(capsys, ["rank", "-i", str(listings_csv)])

    assert code == 0
    assert "SCORE" in out
    assert "100 Good St" in out
    assert "Best value:" in out


def test_rank_defaults_to_the_bundled_sample(capsys):
    code, out, _ = run(capsys, ["rank", "--top", "3"])

    assert code == 0
    assert "sample" in out
    assert out.count("\n") > 4


def test_json_output_is_machine_readable(capsys, listings_csv):
    code, out, _ = run(capsys, ["rank", "-i", str(listings_csv), "--format", "json"])
    payload = json.loads(out)

    assert code == 0
    assert payload["counts"]["found"] == 3
    assert payload["best"]["id"] == "M-1"
    assert payload["request"]["assumptions"]["interest_rate"] == 0.065


def test_csv_output_has_one_row_per_deal(capsys, listings_csv):
    code, out, _ = run(capsys, ["rank", "-i", str(listings_csv), "--format", "csv"])
    lines = out.strip().splitlines()

    assert code == 0
    assert lines[0].startswith("rank,id,source")
    assert len(lines) == 4


def test_budget_filters_are_applied(capsys, listings_csv):
    code, out, _ = run(capsys, ["rank", "-i", str(listings_csv), "--max-price", "200000"])

    assert code == 0
    assert "100 Good St" in out
    assert "300 Bad Blvd" not in out


def test_include_over_budget_keeps_the_rows_visible(capsys, listings_csv):
    code, out, _ = run(
        capsys, ["rank", "-i", str(listings_csv), "--max-price", "200000", "--include-over-budget"]
    )

    assert code == 0
    assert "300 Bad Blvd" in out
    assert "over budget (shown)" in out


def test_city_filter(capsys, listings_csv):
    code, out, _ = run(capsys, ["rank", "-i", str(listings_csv), "--city", "Tucson"])

    assert code == 0
    assert "100 Good St" in out
    assert "200 Meh Ave" not in out


def test_no_matches_exits_nonzero(capsys, listings_csv):
    code, out, _ = run(capsys, ["rank", "-i", str(listings_csv), "--city", "Nowhere"])

    assert code == 1
    assert "No deals matched" in out


def test_explain_prints_a_full_breakdown(capsys, listings_csv):
    code, out, _ = run(capsys, ["explain", "-i", str(listings_csv), "--id", "M-1"])

    assert code == 0
    for section in ("MARKET", "PURCHASE", "MONTHLY", "ANNUAL", "RETURNS", "SCORES (0-100)", "WHY"):
        assert section in out
    assert "Breakeven price" in out


def test_explain_reports_an_unknown_id(capsys, listings_csv):
    code, _, err = run(capsys, ["explain", "-i", str(listings_csv), "--id", "NOPE"])

    assert code == 1
    assert "No deal with id" in err
    assert "M-1" in err


def test_weights_change_the_winner(capsys, listings_csv):
    _, discount_first, _ = run(
        capsys,
        ["rank", "-i", str(listings_csv), "--weight-discount", "1", "--weight-profit", "0",
         "--weight-afford", "0", "--format", "json"],
    )
    _, afford_first, _ = run(
        capsys,
        ["rank", "-i", str(listings_csv), "--weight-discount", "0", "--weight-profit", "0",
         "--weight-afford", "1", "--format", "json"],
    )

    a = json.loads(discount_first)["deals"][0]["scores"]
    b = json.loads(afford_first)["deals"][0]["scores"]
    assert a["composite"] == a["discount"]
    assert b["composite"] == b["affordability"]


def test_rate_accepts_either_percentage_form(capsys, listings_csv):
    _, whole, _ = run(capsys, ["rank", "-i", str(listings_csv), "--rate", "6.5", "--format", "json"])
    _, fraction, _ = run(capsys, ["rank", "-i", str(listings_csv), "--rate", "0.065", "--format", "json"])

    assert json.loads(whole)["deals"] == json.loads(fraction)["deals"]


def test_sources_command_lists_the_builtins(capsys):
    code, out, _ = run(capsys, ["sources"])

    assert code == 0
    assert "hud-reo" in out
    assert "sample" in out


def test_rank_does_not_reach_for_live_sources(capsys, monkeypatch):
    """'rank' must stay offline; only 'find' is allowed to hit the network."""
    from arizona_deal_agent.sources import hud_reo as hud_module

    def explode(*args, **kwargs):
        raise AssertionError("rank must not call a live source")

    monkeypatch.setattr(hud_module, "http_get_json", explode)
    code, _, _ = run(capsys, ["rank", "--top", "1"])
    assert code == 0


def test_find_uses_live_and_bundled_sources_by_default(capsys, monkeypatch, hud_payload):
    from arizona_deal_agent.sources import hud_reo as hud_module

    monkeypatch.setattr(hud_module, "http_get_json", lambda *a, **k: hud_payload)
    code, out, _ = run(capsys, ["find", "--format", "json"])
    payload = json.loads(out)

    assert code == 0
    assert {source["name"] for source in payload["sources"]} == {"hud-reo", "sample"}


def test_find_survives_a_dead_live_source(capsys, monkeypatch):
    from arizona_deal_agent.sources.base import SourceError
    from arizona_deal_agent.sources import hud_reo as hud_module

    def offline(*args, **kwargs):
        raise SourceError("could not reach egis.hud.gov")

    monkeypatch.setattr(hud_module, "http_get_json", offline)
    code, out, _ = run(capsys, ["find", "--format", "json"])
    payload = json.loads(out)

    assert code == 0
    assert payload["deals"]
    assert any("egis.hud.gov" in error for error in payload["errors"])


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
