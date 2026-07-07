"""research CLI dispatch (M3): each command maps to its moved job."""
import research.cli as cli


def test_cli_dispatches_each_job(monkeypatch):
    calls = []
    import research.jobs as rj
    monkeypatch.setattr(rj, "refresh_wf_scores", lambda: calls.append("wf"))
    monkeypatch.setattr(rj, "_refresh_backtest_cache", lambda: calls.append("cache"))
    monkeypatch.setattr(rj, "run_backtest_roller", lambda: calls.append("roll"))
    assert cli.main(["wf-refresh"]) == 0
    assert cli.main(["backtest-cache"]) == 0
    assert cli.main(["roller"]) == 0
    assert calls == ["wf", "cache", "roll"]
