"""End-to-end exercises of the command line, run in-process via ``main()``."""

import json

import pytest

from arizona_deal_agent.cli import fraction, main


def run(capsys, *argv):
    code = main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


class TestFractionArgument:
    @pytest.mark.parametrize(
        "text,expected",
        [("0.2", 0.2), ("20", 0.2), ("20%", 0.2), ("6.5", 0.065), ("6.5%", 0.065), ("0", 0.0), ("1", 1.0)],
    )
    def test_percentages_and_fractions_both_work(self, text, expected):
        assert fraction(text) == pytest.approx(expected)

    def test_rejects_text(self):
        with pytest.raises(Exception):
            fraction("cheap")


class TestFind:
    def test_find_uses_bundled_sample_catalog(self, capsys):
        code, out, _ = run(capsys, "find", "--top", "3")
        assert code == 0
        assert "SCORE" in out
        assert "showing 3" in out
        assert "Best:" in out

    def test_find_ranks_best_value_first(self, capsys):
        _, out, _ = run(capsys, "find", "--format", "json")
        deals = json.loads(out)["deals"]
        scores = [deal["scores"]["composite"] for deal in deals]
        assert scores == sorted(scores, reverse=True)
        assert deals[0]["id"] == "AZ-003"

    def test_rank_also_defaults_to_sample_catalog(self, capsys):
        code, out, _ = run(capsys, "rank", "--top", "1", "--format", "json")
        assert code == 0
        assert json.loads(out)["deals"][0]["id"] == "AZ-003"


class TestRank:
    def test_prints_a_ranked_table(self, capsys, sample_csv):
        code, out, _ = run(capsys, "rank", "-i", str(sample_csv))
        assert code == 0
        assert "SCORE" in out and "CASH FLOW" in out
        assert out.count("AZ-") >= 13
        assert "Scored 25 listing(s)" in out

    def test_top_limits_the_rows(self, capsys, sample_csv):
        _, out, _ = run(capsys, "rank", "-i", str(sample_csv), "--top", "3")
        assert "showing 3" in out

    def test_top_must_be_positive(self, capsys, sample_csv):
        code, _, err = run(capsys, "rank", "-i", str(sample_csv), "--top", "0")
        assert code == 1
        assert "--top must be a positive number" in err

    def test_json_output_is_valid_and_ordered(self, capsys, sample_csv):
        _, out, _ = run(capsys, "rank", "-i", str(sample_csv), "--format", "json")
        payload = json.loads(out)
        assert payload["count"] == 25
        scores = [deal["scores"]["composite"] for deal in payload["deals"]]
        assert scores == sorted(scores, reverse=True)
        assert payload["deals"][0]["rank"] == 1
        assert "cap_rate" in payload["deals"][0]["metrics"]

    def test_csv_output_has_a_header_and_a_row_per_deal(self, capsys, sample_csv):
        _, out, _ = run(capsys, "rank", "-i", str(sample_csv), "--format", "csv")
        lines = out.strip().splitlines()
        assert lines[0].startswith("rank,id,address")
        assert len(lines) == 26

    def test_city_filter(self, capsys, sample_csv):
        _, out, _ = run(capsys, "rank", "-i", str(sample_csv), "--city", "Tucson", "--format", "json")
        cities = {deal["city"] for deal in json.loads(out)["deals"]}
        assert cities == {"Tucson"}

    def test_city_filter_is_case_insensitive_and_repeatable(self, capsys, sample_csv):
        _, out, _ = run(
            capsys, "rank", "-i", str(sample_csv), "--city", "tucson", "--city", "MESA", "--format", "json"
        )
        cities = {deal["city"] for deal in json.loads(out)["deals"]}
        assert cities == {"Tucson", "Mesa"}

    def test_min_cash_flow_filter(self, capsys, sample_csv):
        _, out, _ = run(capsys, "rank", "-i", str(sample_csv), "--min-cash-flow", "0", "--format", "json")
        deals = json.loads(out)["deals"]
        assert deals
        assert all(deal["metrics"]["monthly_cash_flow"] >= 0 for deal in deals)

    def test_min_cap_rate_filter_accepts_percentages(self, capsys, sample_csv):
        _, out, _ = run(capsys, "rank", "-i", str(sample_csv), "--min-cap-rate", "6", "--format", "json")
        deals = json.loads(out)["deals"]
        assert deals
        assert all(deal["metrics"]["cap_rate"] >= 0.06 for deal in deals)

    def test_budget_drops_deals_that_do_not_fit(self, capsys, sample_csv):
        _, out, _ = run(capsys, "rank", "-i", str(sample_csv), "--max-price", "300000", "--format", "json")
        deals = json.loads(out)["deals"]
        assert deals
        assert all(deal["list_price"] <= 300_000 for deal in deals)

    def test_over_budget_deals_can_be_kept_and_are_marked(self, capsys, sample_csv):
        _, out, _ = run(
            capsys,
            "rank",
            "-i",
            str(sample_csv),
            "--max-price",
            "300000",
            "--include-over-budget",
            "--format",
            "json",
        )
        deals = json.loads(out)["deals"]
        assert len(deals) == 25
        assert any(deal["fits_budget"] is False for deal in deals)

    def test_impossible_filters_report_no_matches(self, capsys, sample_csv):
        code, out, _ = run(capsys, "rank", "-i", str(sample_csv), "--min-cash-flow", "999999")
        assert code == 0
        assert "No listings matched your filters." in out

    def test_financing_assumptions_change_the_numbers(self, capsys, sample_csv):
        _, cheap, _ = run(capsys, "rank", "-i", str(sample_csv), "--rate", "3", "--format", "json")
        _, dear, _ = run(capsys, "rank", "-i", str(sample_csv), "--rate", "9", "--format", "json")
        cheap_flow = {d["id"]: d["metrics"]["monthly_cash_flow"] for d in json.loads(cheap)["deals"]}
        dear_flow = {d["id"]: d["metrics"]["monthly_cash_flow"] for d in json.loads(dear)["deals"]}
        assert all(cheap_flow[key] > dear_flow[key] for key in cheap_flow)

    def test_missing_file_exits_with_an_error(self, capsys, tmp_path):
        code, _, err = run(capsys, "rank", "-i", str(tmp_path / "nope.csv"))
        assert code == 1
        assert "not found" in err


class TestExplain:
    def test_prints_every_section(self, capsys, sample_csv):
        code, out, _ = run(capsys, "explain", "-i", str(sample_csv), "--id", "AZ-011")
        assert code == 0
        for section in ("PURCHASE", "MONTHLY", "ANNUAL", "RETURNS", "SCORES", "NOTES"):
            assert section in out
        assert "70%-rule max offer" in out

    def test_id_lookup_ignores_case(self, capsys, sample_csv):
        code, out, _ = run(capsys, "explain", "-i", str(sample_csv), "--id", "az-003")
        assert code == 0
        assert "AZ-003" in out

    def test_unknown_id_lists_what_is_available(self, capsys, sample_csv):
        code, _, err = run(capsys, "explain", "-i", str(sample_csv), "--id", "NOPE")
        assert code == 1
        assert "no listing with id 'NOPE'" in err
        assert "AZ-001" in err

    def test_budget_section_appears_only_with_a_budget(self, capsys, sample_csv):
        _, plain, _ = run(capsys, "explain", "-i", str(sample_csv), "--id", "AZ-003")
        _, budgeted, _ = run(
            capsys, "explain", "-i", str(sample_csv), "--id", "AZ-003", "--budget-cash", "50000"
        )
        assert "BUDGET" not in plain
        assert "Fits budget              no" in budgeted


class TestScore:
    def test_scores_a_deal_typed_by_hand(self, capsys):
        code, out, _ = run(capsys, "score", "--price", "240000", "--rent", "2100")
        assert code == 0
        assert "Cap rate" in out and "Composite" in out

    def test_arv_enables_the_flip_line(self, capsys):
        _, without, _ = run(capsys, "score", "--price", "240000", "--rent", "2100")
        _, with_arv, _ = run(capsys, "score", "--price", "240000", "--rent", "2100", "--arv", "330000")
        assert "70%-rule max offer" not in without
        assert "70%-rule max offer" in with_arv

    def test_dollar_signs_and_commas_are_accepted(self, capsys):
        code, out, _ = run(capsys, "score", "--price", "$240,000", "--rent", "$2,100")
        assert code == 0
        assert "$240,000" in out

    def test_beds_and_baths_line_is_omitted_when_unknown(self, capsys):
        _, out, _ = run(capsys, "score", "--price", "240000", "--rent", "2100")
        assert "0 bd / 0 ba" not in out


class TestTransmit:
    def test_formats_top_deal_as_shareable_text(self, capsys, sample_csv):
        code, out, _ = run(capsys, "transmit", "-i", str(sample_csv))
        assert code == 0
        assert "ARIZONA DEAL RECOMMENDATION" in out
        assert "Why this deal:" in out
        assert "— Arizona Deal Agent" in out

    def test_recipient_appears_in_header(self, capsys, sample_csv):
        _, out, _ = run(capsys, "transmit", "-i", str(sample_csv), "--to", "Kiet")
        assert out.startswith("To: Kiet\n")

    def test_json_format_includes_recipient_and_recommendation(self, capsys, sample_csv):
        _, out, _ = run(capsys, "transmit", "-i", str(sample_csv), "--format", "json", "--to", "team@example.com")
        payload = json.loads(out)
        assert payload["recipient"] == "team@example.com"
        assert payload["recommendation"]["id"] == "AZ-003"
        assert "scores" in payload["recommendation"]

    def test_budget_filters_apply_before_transmitting(self, capsys, sample_csv):
        _, out, _ = run(
            capsys,
            "transmit",
            "-i",
            str(sample_csv),
            "--max-price",
            "350000",
            "--format",
            "json",
        )
        payload = json.loads(out)
        assert payload["recommendation"]["list_price"] <= 350_000

    def test_no_matches_is_an_error(self, capsys, sample_csv):
        code, _, err = run(capsys, "transmit", "-i", str(sample_csv), "--min-cash-flow", "999999")
        assert code == 1
        assert "nothing to transmit" in err


class TestHowto:
    def test_prints_operator_guide(self, capsys):
        code, out, _ = run(capsys, "howto")
        assert code == 0
        assert "How to use Arizona Deal Agent" in out
        assert "arizona-deal-agent rank" in out
        assert "arizona-deal-agent transmit" in out
        assert ".venv\\Scripts\\activate.bat" in out
        for name in ("balanced", "profit", "affordability", "tight", "houses"):
            assert name in out

    def test_help_mentions_howto(self, capsys):
        with pytest.raises(SystemExit) as excinfo:
            main(["--help"])
        assert excinfo.value.code == 0
        help_text = capsys.readouterr().out
        assert "howto" in help_text
        assert "How to use" in help_text

    def test_run_balanced_recommends_fort_lowell(self, capsys, sample_csv):
        code, out, _ = run(capsys, "howto", "--run", "balanced", "-i", str(sample_csv))
        assert code == 0
        assert "How to use — balanced" in out
        assert "AZ-003" in out
        assert "3110 E Fort Lowell Rd" in out
        assert "Best:" in out

    def test_run_profit_recommends_twelfth_ave(self, capsys, sample_csv):
        code, out, _ = run(capsys, "howto", "--run", "profit", "-i", str(sample_csv))
        assert code == 0
        assert "AZ-012" in out
        assert "5402 S 12th Ave" in out
        assert out.index("AZ-012") < out.index("AZ-003")

    def test_run_tight_keeps_only_fort_lowell(self, capsys, sample_csv):
        code, out, _ = run(capsys, "howto", "--run", "tight", "-i", str(sample_csv))
        assert code == 0
        assert "AZ-003" in out
        assert "showing 1" in out
        assert "AZ-012" not in out

    def test_run_houses_recommends_fort_lowell(self, capsys, sample_csv):
        code, out, _ = run(capsys, "howto", "--run", "houses", "-i", str(sample_csv))
        assert code == 0
        assert "How to use — houses" in out
        assert "AZ-003" in out
        assert "3110 E Fort Lowell Rd" in out

    def test_unknown_scenario_is_an_error(self, capsys, sample_csv):
        code, _, err = run(capsys, "howto", "--run", "flip", "-i", str(sample_csv))
        assert code == 1
        assert "unknown scenario 'flip'" in err


class TestTopLevel:
    def test_parser_help_strings_are_valid(self, capsys):
        """Python 3.14 rejects a lone % in argparse help (e.g. 0.62% of price)."""
        from arizona_deal_agent.cli import build_parser

        parser = build_parser()
        parser.format_help()
        with pytest.raises(SystemExit) as excinfo:
            main(["score", "--help"])
        assert excinfo.value.code == 0
        help_text = capsys.readouterr().out
        assert "of price" in help_text

    def test_version(self, capsys):
        with pytest.raises(SystemExit) as excinfo:
            main(["--version"])
        assert excinfo.value.code == 0
        assert "arizona-deal-agent" in capsys.readouterr().out

    def test_a_command_is_required(self, capsys):
        with pytest.raises(SystemExit) as excinfo:
            main([])
        assert excinfo.value.code == 2
