"""WatchlistAdapter — put the EOD and Premarket plans under forward test.

WHY THIS EXISTS (audit 2026-09-02, finding F-1)
------------------------------------------------
`SignalAdapter` reads exactly one source table: `scheduled_signals`. EOD and
Premarket publish to `watchlist_snapshot`, which nothing in `forward_testing/`
read. So the only pipeline actually producing signals the operator acts on was
the only one with no forward-test ledger -- while the ledger that did run was
fed exclusively by a heuristic short signal nobody trades.

This adapter ingests the append-only publication log
(`watchlist_snapshot_log`, engine/watchlist_ledger.py) into the existing
`ft_signal` -> `ft_shadow_position` -> `ft_shadow_trade` machinery, unchanged.
Cohorts stay separated by `ft_signal.strategy` ('eod', 'premarket') and are never
pooled -- pooling them would hide exactly the EOD-vs-revision comparison the
rebuild exists to make measurable.

`ft_signal_meta` carries the fields the outcome analysis needs and `ft_signal`
has no column for: source tags, confluence, the attributing walk-forward
strategy and its OOS evidence AS OF PUBLICATION, the rule_id, the Agent Firm's
decision and confidence, the premarket revision action and reason, and the
decision price/basis/entry rule. It is append-only, enforced by triggers: a
frozen signal cannot be revised after the fact.

Entry timing is unchanged and still safe: ShadowPositionManager fills at
`resolver.next_open(ticker, signal_date)`, so a plan published at 16:40 on D is
entered at D+1's open. No retrospective price selection anywhere.
"""
from __future__ import annotations

import json
import sqlite3

from forward_testing.lifecycle.states import SignalState
from forward_testing.storage.db import ft_get_db

SHADOW = "SHADOW"
COHORTS = ("eod", "premarket")

SIGNAL_META_DDL = """
CREATE TABLE IF NOT EXISTS ft_signal_meta (
    signal_id            INTEGER PRIMARY KEY REFERENCES ft_signal(id),
    cohort               TEXT NOT NULL,
    plan_date            TEXT NOT NULL,
    revision             INTEGER,
    source_tags          TEXT,
    confluence           INTEGER,
    strategy_fn          TEXT,
    rule_id              TEXT,
    admission_path       TEXT,
    wf_expectancy_pct    REAL,
    wf_n_trades          INTEGER,
    wf_last_computed     TEXT,
    decision_price       REAL,
    decision_price_basis TEXT,
    entry_rule           TEXT,
    agent_decision       TEXT,
    agent_confidence     REAL,
    veto_reason          TEXT,
    market_regime        TEXT,
    revision_action      TEXT,
    revision_reason_code TEXT,
    revision_reason      TEXT,
    provenance           TEXT,
    recorded_at          TEXT
)
"""

_META_TRIGGERS = (
    ("ft_signal_meta_no_update", "UPDATE"),
    ("ft_signal_meta_no_delete", "DELETE"),
)


def ensure_meta_table(db_path: str) -> None:
    with ft_get_db(db_path) as c:
        c.execute(SIGNAL_META_DDL)
        for name, event in _META_TRIGGERS:
            c.execute(
                f"CREATE TRIGGER IF NOT EXISTS {name} BEFORE {event} ON "
                f"ft_signal_meta BEGIN SELECT RAISE(ABORT, "
                f"'ft_signal_meta is append-only: a frozen signal cannot be "
                f"revised'); END"
            )
        c.commit()


class WatchlistAdapter:
    """Ingest published EOD / Premarket plans as forward-test signals."""

    def __init__(self, repo, db_path, cohorts=COHORTS):
        self.repo = repo
        self.db_path = db_path
        self.cohorts = tuple(cohorts)
        self._vcache: dict = {}

    def _version(self, cohort, strategy_fn):
        """Canonical version id + config hash for the thing that produced this
        signal. Prefer the attributing walk-forward strategy; fall back to the
        cohort pseudo-strategy so an unattributed heuristic row is still pinned
        to the code that generated it (audit blocker #3)."""
        from engine import strategy_version as sv
        key = strategy_fn or cohort
        cached = self._vcache.get(key)
        if cached is not None:
            return cached
        with ft_get_db(self.db_path) as c:
            got = sv.resolve(c, key)
        self._vcache[key] = got
        return got

    def ingest(self, run_date) -> int:
        """Ingest every plan published for `run_date`. Returns NEW signals.

        Idempotent: `ft_signal` de-duplicates on
        (signal_date, ticker, strategy, track), and the meta row is written with
        INSERT OR IGNORE, so a re-run adds nothing and rewrites nothing.
        """
        ensure_meta_table(self.db_path)
        n = 0
        for cohort in self.cohorts:
            for row in self._published_rows(run_date, cohort):
                vid, chash = self._version(cohort, row.get("strategy_fn"))
                sid = self.repo.insert_signal(
                    signal_date=run_date,
                    ticker=row["ticker"],
                    strategy=cohort,
                    track=SHADOW,
                    direction="LONG",
                    entry_price_intent=row.get("decision_price"),
                    conviction=row.get("confidence"),
                    strategy_version_id=vid,
                    source_table="watchlist_snapshot_log",
                    source_id=row.get("log_id"),
                    config_hash=chash,
                )
                self._write_meta(sid, cohort, run_date, row)
                if self.repo.get_signal_state(sid) is None:
                    self.repo.init_signal_state(sid, SignalState.GENERATED.value)
                    self.repo.write_transition(
                        sid, None, SignalState.GENERATED.value, run_date,
                        actor="watchlist_adapter", reason="ingest",
                    )
                    n += 1
        return n

    def _published_rows(self, run_date, cohort):
        """Latest published revision of `cohort`'s plan for `run_date`."""
        with ft_get_db(self.db_path) as c:
            try:
                rev = c.execute(
                    "SELECT MAX(revision) FROM watchlist_snapshot_log "
                    "WHERE date=? AND strategy=?", (run_date, cohort)).fetchone()
            except sqlite3.Error:
                return []           # ledger not created yet -> nothing to ingest
            if not rev or rev[0] is None:
                return []
            cur = c.execute(
                "SELECT id AS log_id, ticker, rank, confidence, conviction, "
                "       confluence, sources, strategy_fn, rule_id, "
                "       admission_path, wf_expectancy_pct, wf_n_trades, "
                "       wf_last_computed, decision_price, decision_price_basis, "
                "       entry_rule, provenance, revision "
                "FROM watchlist_snapshot_log "
                "WHERE date=? AND strategy=? AND revision=? ORDER BY rank",
                (run_date, cohort, rev[0]))
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]

    def _write_meta(self, signal_id, cohort, run_date, row):
        prov = {}
        try:
            prov = json.loads(row.get("provenance") or "{}")
        except (ValueError, TypeError):
            prov = {}
        rev_block = prov.get("premarket_revision") or {}
        with ft_get_db(self.db_path) as c:
            c.execute(
                "INSERT OR IGNORE INTO ft_signal_meta "
                "(signal_id, cohort, plan_date, revision, source_tags, confluence, "
                " strategy_fn, rule_id, admission_path, wf_expectancy_pct, "
                " wf_n_trades, wf_last_computed, decision_price, "
                " decision_price_basis, entry_rule, agent_decision, "
                " agent_confidence, veto_reason, market_regime, revision_action, "
                " revision_reason_code, revision_reason, provenance, recorded_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, "
                "        datetime('now','localtime'))",
                (signal_id, cohort, run_date, row.get("revision"),
                 row.get("sources"), row.get("confluence"),
                 row.get("strategy_fn"), row.get("rule_id"),
                 row.get("admission_path"), row.get("wf_expectancy_pct"),
                 row.get("wf_n_trades"), row.get("wf_last_computed"),
                 row.get("decision_price"), row.get("decision_price_basis"),
                 row.get("entry_rule"),
                 "approve" if row.get("confidence") is not None else None,
                 row.get("confidence"),
                 prov.get("veto_reason"),
                 prov.get("market_regime") or (rev_block.get("evidence") or {}).get("market_regime"),
                 rev_block.get("action"), rev_block.get("reason_code"),
                 rev_block.get("reason"),
                 json.dumps(prov, default=str)),
            )
            c.commit()
