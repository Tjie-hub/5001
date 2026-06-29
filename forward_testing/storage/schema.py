"""Versioned DDL for forward-testing tables (single source of truth).

Phase 1 (foundation): strategy_version, signal, signal_state, transition_log,
run, run_log. Later phases (positions, trades, marks, adjustments, performance,
scoreboard, benchmark, improvement_log) extend init_ft_tables() with their own
schema constants appended here.
"""

FT_PHASE1_SCHEMA = """
CREATE TABLE IF NOT EXISTS ft_strategy_version (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy         TEXT NOT NULL,
    version          TEXT NOT NULL,
    config_json      TEXT,
    config_hash      TEXT NOT NULL,
    entry_rules_ref  TEXT,
    exit_policy_ref  TEXT,
    created_at       TEXT DEFAULT (datetime('now','localtime')),
    UNIQUE(strategy, version)
);
CREATE INDEX IF NOT EXISTS idx_ft_sv_hash ON ft_strategy_version(config_hash);

CREATE TABLE IF NOT EXISTS ft_signal (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_date         TEXT NOT NULL,
    ticker              TEXT NOT NULL,
    strategy            TEXT NOT NULL,
    strategy_version_id INTEGER REFERENCES ft_strategy_version(id),
    track               TEXT NOT NULL CHECK(track IN ('SHADOW','PORTFOLIO')),
    direction           TEXT NOT NULL DEFAULT 'LONG',
    entry_price_intent  REAL,
    atr14               REAL,
    conviction          REAL,
    source_table        TEXT,
    source_id           INTEGER,
    config_hash         TEXT,
    created_at          TEXT DEFAULT (datetime('now','localtime')),
    UNIQUE(signal_date, ticker, strategy, track)
);
CREATE INDEX IF NOT EXISTS idx_ft_signal_strategy_date ON ft_signal(strategy, signal_date);
CREATE INDEX IF NOT EXISTS idx_ft_signal_track_date ON ft_signal(track, signal_date);

CREATE TABLE IF NOT EXISTS ft_signal_state (
    signal_id   INTEGER PRIMARY KEY REFERENCES ft_signal(id),
    state       TEXT NOT NULL,
    since       TEXT,
    updated_at  TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS ft_transition_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id   INTEGER NOT NULL REFERENCES ft_signal(id),
    from_state  TEXT,
    to_state    TEXT NOT NULL,
    at          TEXT DEFAULT (datetime('now','localtime')),
    actor       TEXT,
    reason      TEXT,
    run_date    TEXT,
    violation   TEXT
);
CREATE INDEX IF NOT EXISTS idx_ft_trans_signal ON ft_transition_log(signal_id);
CREATE INDEX IF NOT EXISTS idx_ft_trans_run ON ft_transition_log(run_date);

CREATE TABLE IF NOT EXISTS ft_run (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date    TEXT NOT NULL,
    kind        TEXT NOT NULL,
    started_at  TEXT,
    finished_at TEXT,
    status      TEXT NOT NULL,
    pid         INTEGER
);
CREATE INDEX IF NOT EXISTS idx_ft_run_date ON ft_run(run_date);

CREATE TABLE IF NOT EXISTS ft_run_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      INTEGER REFERENCES ft_run(id),
    phase       TEXT,
    started_at  TEXT,
    finished_at TEXT,
    rows_in     INTEGER,
    rows_out    INTEGER,
    status      TEXT,
    error       TEXT
);
"""

FT_PHASE2_SCHEMA = """
CREATE TABLE IF NOT EXISTS ft_shadow_position (
    signal_id      INTEGER PRIMARY KEY REFERENCES ft_signal(id),
    ticker         TEXT NOT NULL,
    strategy       TEXT NOT NULL,
    direction      TEXT NOT NULL,
    entry_date     TEXT NOT NULL,
    entry_price    REAL NOT NULL,
    atr14          REAL NOT NULL,
    sl_price       REAL,
    tp_price       REAL,
    trail_atr_mult REAL,
    trail_anchor   REAL,
    highest_seen   REAL NOT NULL,
    lowest_seen    REAL NOT NULL,
    hold_days      INTEGER NOT NULL DEFAULT 0,
    status         TEXT NOT NULL DEFAULT 'OPEN',
    exit_date      TEXT,
    exit_price     REAL,
    exit_reason    TEXT,
    created_at     TEXT DEFAULT (datetime('now','localtime')),
    updated_at     TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_ft_shadow_pos_status ON ft_shadow_position(status);
CREATE INDEX IF NOT EXISTS idx_ft_shadow_pos_ticker ON ft_shadow_position(ticker);

CREATE TABLE IF NOT EXISTS ft_shadow_trade (
    signal_id    INTEGER PRIMARY KEY REFERENCES ft_signal(id),
    ticker       TEXT NOT NULL,
    strategy     TEXT NOT NULL,
    direction    TEXT NOT NULL,
    signal_date  TEXT NOT NULL,
    entry_date   TEXT NOT NULL,
    entry_price  REAL NOT NULL,
    exit_date    TEXT NOT NULL,
    exit_price   REAL NOT NULL,
    exit_reason  TEXT NOT NULL,
    pnl_pct      REAL NOT NULL,
    r_multiple   REAL NOT NULL,
    hold_days    INTEGER NOT NULL,
    mae_pct      REAL,
    mfe_pct      REAL,
    closed_at    TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_ft_shadow_trade_strat ON ft_shadow_trade(strategy, exit_date);
CREATE INDEX IF NOT EXISTS idx_ft_shadow_trade_ticker ON ft_shadow_trade(ticker);
"""
