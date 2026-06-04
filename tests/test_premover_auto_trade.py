"""Tests for premover auto-execution toggle (G6)."""
import sqlite3
import pytest
import pandas as pd


@pytest.fixture()
def pt_db(tmp_path, monkeypatch):
    """Isolated paper_trade DB with schema initialized."""
    import paper_trade as pt
    db = str(tmp_path / "pt.db")
    monkeypatch.setattr(pt, "DB_PATH", db)
    pt.init_paper_table()
    return db


def test_default_premover_mode_is_off(pt_db):
    """Default mode is 'off' when config key is absent."""
    from paper_trade import get_premover_mode
    assert get_premover_mode() == "off"


def test_set_and_get_premover_mode(pt_db):
    """set_premover_mode persists and get_premover_mode retrieves it."""
    from paper_trade import get_premover_mode, set_premover_mode
    set_premover_mode("shadow")
    assert get_premover_mode() == "shadow"
    set_premover_mode("enforce")
    assert get_premover_mode() == "enforce"
    set_premover_mode("off")
    assert get_premover_mode() == "off"


def test_set_premover_mode_invalid_raises(pt_db):
    """set_premover_mode raises ValueError for unknown mode."""
    from paper_trade import set_premover_mode
    with pytest.raises(ValueError):
        set_premover_mode("invalid_mode")


def test_get_config_survives_string_values(pt_db):
    """get_config() must not crash when paper_config has non-numeric values."""
    from paper_trade import get_config, set_premover_mode
    set_premover_mode("shadow")
    cfg = get_config()              # must not raise
    assert "capital" in cfg
    assert cfg["capital"] == 50_000_000.0


def test_evaluate_premover_trade_passes_all_gates(pt_db):
    """Clean state: no open trades, no DD block, BULL regime → would_trade=True."""
    from paper_trade import evaluate_premover_trade
    conn = sqlite3.connect(pt_db)
    conn.execute("""CREATE TABLE IF NOT EXISTS backtest_cache (
        ticker TEXT, computed_date TEXT, best_strategy TEXT, best_return REAL,
        win_rate REAL, sharpe REAL, total_trades INTEGER, profitable INTEGER,
        regime TEXT, updated_at TEXT, PRIMARY KEY (ticker, computed_date))""")
    conn.execute("INSERT INTO backtest_cache VALUES ('BRPT','2026-06-05','Crash Recovery',22.0,100.0,2.0,1,1,'BULL','2026-06-05')")
    conn.commit()
    conn.close()
    result = evaluate_premover_trade("BRPT", 55, "REVERSAL_BREAKOUT")
    assert result["would_trade"] is True
    assert result["skip_reason"] is None


def test_evaluate_blocks_on_dd_circuit_breaker(pt_db):
    """entries_blocked=1 in paper_config → would_trade=False."""
    from paper_trade import evaluate_premover_trade
    conn = sqlite3.connect(pt_db)
    conn.execute("INSERT OR REPLACE INTO paper_config VALUES ('entries_blocked','1')")
    conn.commit()
    conn.close()
    result = evaluate_premover_trade("BRPT", 55, "REVERSAL_BREAKOUT")
    assert result["would_trade"] is False
    assert result["skip_reason"] == "dd_circuit_breaker"


def test_evaluate_blocks_on_bear_regime(pt_db):
    """backtest_cache has regime=BEAR → would_trade=False."""
    from paper_trade import evaluate_premover_trade
    conn = sqlite3.connect(pt_db)
    conn.execute("""CREATE TABLE IF NOT EXISTS backtest_cache (
        ticker TEXT, computed_date TEXT, best_strategy TEXT, best_return REAL,
        win_rate REAL, sharpe REAL, total_trades INTEGER, profitable INTEGER,
        regime TEXT, updated_at TEXT, PRIMARY KEY (ticker, computed_date))""")
    conn.execute("INSERT INTO backtest_cache VALUES ('BEAR_TICKER','2026-06-05','momentum',5.0,60.0,1.0,1,1,'BEAR','2026-06-05')")
    conn.commit()
    conn.close()
    result = evaluate_premover_trade("BEAR_TICKER", 52, "REVERSAL_BREAKOUT")
    assert result["would_trade"] is False
    assert result["skip_reason"] is not None
    assert "regime" in result["skip_reason"]


def test_api_premover_mode_get_and_post(pt_db, monkeypatch):
    """GET returns 'off'; POST sets mode; invalid mode returns 400."""
    import paper_trade as pt
    monkeypatch.setattr(pt, "DB_PATH", pt_db)
    from app import app
    app.config['TESTING'] = True
    client = app.test_client()

    resp = client.get('/api/paper/premover_mode')
    assert resp.status_code == 200
    assert resp.get_json()['mode'] == 'off'

    resp = client.post('/api/paper/premover_mode',
                       json={'mode': 'shadow'},
                       content_type='application/json')
    assert resp.status_code == 200
    assert resp.get_json()['mode'] == 'shadow'

    resp = client.get('/api/paper/premover_mode')
    assert resp.get_json()['mode'] == 'shadow'

    resp = client.post('/api/paper/premover_mode',
                       json={'mode': 'unknown'},
                       content_type='application/json')
    assert resp.status_code == 400
