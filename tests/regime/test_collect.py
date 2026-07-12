from research.regime.collect import tag_trade, corpus_fingerprint


class _StubConn:
    pass


def test_tag_trade_adds_regime_and_both_tiers(monkeypatch):
    import research.regime.collect as col
    # Stub the three enrichers so tag_trade is unit-testable without a DB/df.
    monkeypatch.setattr(col, "_regime_at", lambda df, t, d: "BULL")
    monkeypatch.setattr(col, "vol_tier", lambda df, d, window, median_lookback: "HIGH_VOL")
    monkeypatch.setattr(col, "liq_tier", lambda adv_value, high_multiple: "LOW_LIQ")
    monkeypatch.setattr(col, "get_adv_value_30d", lambda conn, ticker, date: 6e9)

    from research.regime.config import load_config
    cfg = load_config()
    base = {"ticker": "AALI", "entry_date": "2024-03-01",
            "raw_entry": 100.0, "raw_exit": 102.0}
    out = tag_trade(_StubConn(), base, full_df=None, config=cfg)
    assert out["regime"] == "BULL"
    assert out["vol_tier"] == "HIGH_VOL"
    assert out["liq_tier"] == "LOW_LIQ"


def test_corpus_fingerprint_is_stable_and_order_independent():
    a = [{"ticker": "A", "entry_date": "2024-01-01"},
         {"ticker": "B", "entry_date": "2024-02-01"}]
    b = list(reversed(a))
    assert corpus_fingerprint(a) == corpus_fingerprint(b)


class _AsOfConn:
    def execute(self, *a):
        class _Cur:
            def fetchone(self_inner):
                return ("2026-07-10",)
        return _Cur()


def test_collect_defaults_to_liquid_universe_not_all_tickers(monkeypatch):
    """Regression: the canonical NR7 corpus is the 187 liquidity-filtered tickers
    (Phase B/C baseline), NOT the full ~958-ticker ohlcv universe. Using the wrong
    universe silently inflates the trade set and corrupts the regime cells."""
    import research.regime.collect as col
    from research.regime.config import load_config

    calls = {}

    def fake_liquid(conn, as_of):
        calls["as_of"] = as_of
        return []                      # empty universe -> short-circuits the loop

    monkeypatch.setattr(col, "liquid_universe", fake_liquid)
    out = col.collect_tagged_trades(_AsOfConn(), "nr7_breakout", load_config())
    assert out == []
    assert calls["as_of"] == "2026-07-10"   # liquidity filter applied as-of latest bar
