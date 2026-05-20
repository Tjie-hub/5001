import json
import sqlite3
import pytest
from engine.agent_firm.analytics import cohort_summary


def _make_db(tmp_path):
    db = tmp_path / "t.db"
    conn = sqlite3.connect(db)
    conn.executescript("""
        CREATE TABLE agent_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_time TEXT NOT NULL,
            ticker TEXT NOT NULL,
            strategy TEXT NOT NULL,
            quant_score REAL,
            decision TEXT NOT NULL,
            confidence REAL,
            size_hint REAL,
            rationale TEXT,
            tokens_in INTEGER,
            tokens_out INTEGER,
            cost_usd REAL,
            duration_s REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE agent_traces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_id INTEGER REFERENCES agent_decisions(id),
            role TEXT NOT NULL,
            prompt_version TEXT,
            output TEXT,
            tools_called TEXT,
            tokens_in INTEGER,
            tokens_out INTEGER,
            duration_s REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE paper_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            strategy TEXT,
            entry_date TEXT,
            entry_price REAL,
            lots INTEGER,
            tp_price REAL,
            sl_price REAL,
            exit_date TEXT,
            exit_price REAL,
            exit_reason TEXT,
            pnl_rp REAL,
            pnl_pct REAL,
            status TEXT DEFAULT 'OPEN'
        );
    """)
    conn.commit()
    conn.close()
    return str(db)


def _seed_cohort_data(db_path):
    conn = sqlite3.connect(db_path)
    # 3 approved decisions → positive trades
    for i, (ticker, pnl) in enumerate([("BBRI", 3.2), ("TLKM", 2.1), ("ASII", 1.5)]):
        conn.execute(
            "INSERT INTO agent_decisions (scan_time, ticker, strategy, decision) VALUES (?,?,?,?)",
            (f"2026-05-{10+i:02d}T10:00:00", ticker, "vol_weighted", "approve"),
        )
        conn.execute(
            "INSERT INTO paper_trades (ticker, entry_date, pnl_pct, status) VALUES (?,?,?,?)",
            (ticker, f"2026-05-{10+i:02d}", pnl, "CLOSED"),
        )
    # 2 veto decisions → negative trades
    for i, (ticker, pnl) in enumerate([("BMRI", -1.8), ("UNVR", -2.3)]):
        conn.execute(
            "INSERT INTO agent_decisions (scan_time, ticker, strategy, decision) VALUES (?,?,?,?)",
            (f"2026-05-{13+i:02d}T10:00:00", ticker, "vol_weighted", "veto"),
        )
        conn.execute(
            "INSERT INTO paper_trades (ticker, entry_date, pnl_pct, status) VALUES (?,?,?,?)",
            (ticker, f"2026-05-{13+i:02d}", pnl, "CLOSED"),
        )
    conn.commit()
    conn.close()


def test_cohort_summary_approve_beats_baseline(tmp_path):
    db = _make_db(tmp_path)
    _seed_cohort_data(db)
    result = cohort_summary(db)
    assert result["approve"]["n"] == 3
    assert result["veto"]["n"] == 2
    assert result["baseline"]["n"] == 5  # all 5 closed trades
    assert result["approve"]["avg_return_pct"] > result["baseline"]["avg_return_pct"]
    assert result["veto"]["avg_return_pct"] < 0


def test_cohort_summary_empty_db(tmp_path):
    db = _make_db(tmp_path)
    result = cohort_summary(db)
    assert result["approve"]["n"] == 0
    assert result["veto"]["n"] == 0
    assert result["baseline"]["n"] == 0


def test_cohort_summary_identical_returns_no_crash(tmp_path):
    db = _make_db(tmp_path)
    conn = sqlite3.connect(db)
    # Seed an approve decision with 3 trades all having identical pnl
    for i, ticker in enumerate(["BBRI", "TLKM", "ASII"]):
        conn.execute(
            "INSERT INTO agent_decisions (scan_time, ticker, strategy, decision) VALUES (?,?,?,?)",
            (f"2026-05-{10+i:02d}T10:00:00", ticker, "vol_weighted", "approve"),
        )
        conn.execute(
            "INSERT INTO paper_trades (ticker, entry_date, pnl_pct, status) VALUES (?,?,?,?)",
            (ticker, f"2026-05-{10+i:02d}", 5.0, "CLOSED"),
        )
    conn.commit()
    conn.close()
    result = cohort_summary(db)
    assert result["approve"]["n"] == 3
    assert result["approve"]["sharpe"] == 0.0  # stdev = 0, sharpe = 0 not crash


from engine.agent_firm.analytics import agent_agreement


def _seed_agreement_data(db_path):
    conn = sqlite3.connect(db_path)
    # 1 approve decision with 6 traces (4 analysts + bull + bear)
    cur = conn.execute(
        "INSERT INTO agent_decisions (scan_time, ticker, strategy, decision) VALUES (?,?,?,?)",
        ("2026-05-20T10:00:00", "BBRI", "vol_weighted", "approve"),
    )
    did = cur.lastrowid
    traces = [
        ("technical", json.dumps({"verdict": "BULLISH", "conviction": 0.7})),
        ("flow",      json.dumps({"flow_verdict": "ACCUMULATING"})),
        ("regime",    json.dumps({"regime_call": "TRENDING"})),
        ("news",      json.dumps({"sentiment": "BULLISH"})),
        ("bull",      json.dumps({"bull_case": "Strong flow."})),
        ("bear",      json.dumps({"bear_case": "Rate risk."})),
    ]
    for role, output in traces:
        conn.execute(
            "INSERT INTO agent_traces (decision_id, role, output) VALUES (?,?,?)",
            (did, role, output),
        )
    conn.commit()
    conn.close()


def test_agent_agreement_counts_roles(tmp_path):
    db = _make_db(tmp_path)
    _seed_agreement_data(db)
    result = agent_agreement(db)
    roles = [r["role"] for r in result]
    assert set(roles) == {"technical", "flow", "regime", "news", "bull", "bear"}
    # All analyst traces are bullish-aligned with approve decision
    for r in result:
        assert r["decisions"] == 1
    # bear is aligned with veto, not approve → agreement_pct 0.0
    bear_row = next(r for r in result if r["role"] == "bear")
    assert bear_row["agreement_pct"] == 0.0
    # bull, technical, flow, regime, news all aligned with approve → 100%
    for role in ["bull", "technical", "flow", "regime", "news"]:
        row = next(r for r in result if r["role"] == role)
        assert row["agreement_pct"] == 100.0


def test_agent_agreement_empty(tmp_path):
    db = _make_db(tmp_path)
    result = agent_agreement(db)
    assert result == []


from engine.agent_firm.analytics import decision_log


def _seed_log_data(db_path):
    conn = sqlite3.connect(db_path)
    # 3 approve decisions with matching closed paper trades
    for i, ticker in enumerate(["BBRI", "TLKM", "ASII"]):
        conn.execute(
            "INSERT INTO agent_decisions (scan_time, ticker, strategy, decision, confidence, size_hint, rationale) "
            "VALUES (?,?,?,?,?,?,?)",
            (f"2026-05-{10+i:02d}T10:00:00", ticker, "vol_weighted", "approve",
             0.75, 1.0, "Risk: aligned.\nBull/Bear: bull case."),
        )
        conn.execute(
            "INSERT INTO paper_trades (ticker, entry_date, pnl_pct, status) VALUES (?,?,?,?)",
            (ticker, f"2026-05-{10+i:02d}", 2.5, "CLOSED"),
        )
    # 1 veto decision with NO matching paper trade
    conn.execute(
        "INSERT INTO agent_decisions (scan_time, ticker, strategy, decision, confidence, size_hint, rationale) "
        "VALUES (?,?,?,?,?,?,?)",
        ("2026-05-15T10:00:00", "BMRI", "vol_weighted", "veto", 0.6, 0.0, "Risk: distributing."),
    )
    conn.commit()
    conn.close()


def test_decision_log_returns_rows(tmp_path):
    db = _make_db(tmp_path)
    _seed_log_data(db)
    result = decision_log(db)
    assert len(result) == 4
    assert all("ticker" in r for r in result)
    assert all("decision" in r for r in result)


def test_decision_log_no_paper_trade_outcome_is_none(tmp_path):
    db = _make_db(tmp_path)
    _seed_log_data(db)
    result = decision_log(db)
    veto_row = next(r for r in result if r["decision"] == "veto")
    assert veto_row["outcome"] is None
    assert veto_row["pnl_pct"] is None


def test_decision_log_empty_db(tmp_path):
    db = _make_db(tmp_path)
    result = decision_log(db)
    assert result == []
