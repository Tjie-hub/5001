"""Phase C CLI (spec §3): `evaluate --strategy ...`. Glue tested with injected
fakes so no corpus is needed."""
from types import SimpleNamespace

from research.gatekeeper import cli


def test_cli_evaluate_threads_strategy_and_universe(tmp_path):
    calls = {}

    def fake_build(conn, strat, uni, cfg):
        calls["strat"] = strat
        calls["uni"] = uni
        return "CANDIDATE"

    def fake_run(candidate, config, db_path=None, report_path=None):
        calls["cand"] = candidate
        calls["report"] = report_path
        return SimpleNamespace(final_state="WATCHLIST", failing_stage=None, run_id="r1")

    args = cli.build_parser().parse_args(
        ["evaluate", "--strategy", "NR7 Breakout", "--db", str(tmp_path / "x.db"),
         "--universe", "AAA,BBB", "--report", str(tmp_path / "r.md")])
    d = cli.evaluate(args, build_candidate_fn=fake_build, run_gate_fn=fake_run)

    assert calls["strat"] == "NR7 Breakout"
    assert calls["uni"] == ["AAA", "BBB"]
    assert calls["cand"] == "CANDIDATE"
    assert d.final_state == "WATCHLIST"
