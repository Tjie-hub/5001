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
