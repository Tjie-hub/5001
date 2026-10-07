"""Date-logic and guard tests for the owner-todo cron jobs (scripts/ops).

Modules are loaded straight from scripts/ops via importlib — they are
stdlib-only at import time by design, so no .env, no venv, no network, and no
repository DB is touched. DB_PATH is pointed at tmp files per the production
safety rule (tests never run against ~/idx-walkforward-5001).
"""
from __future__ import annotations

import base64
import importlib.util
import json
import sqlite3
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

OPS_DIR = Path(__file__).resolve().parents[1] / "scripts" / "ops"
WIB = ZoneInfo("Asia/Jakarta")


def load_module(name: str):
    spec = importlib.util.spec_from_file_location(f"opsjob_{name}", OPS_DIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── J1 owner_reminders ──────────────────────────────────────────────────────

def test_items_due_exact_date_and_multiple(tmp_path):
    j1 = load_module("owner_reminders")
    items = [
        {"date": "2026-10-01", "text": "first"},
        {"date": "2026-10-01", "text": "second"},
        {"date": "2026-10-02", "text": "tomorrow"},
        {"date": "2026-09-30", "text": "yesterday"},
        {"date": "2026-10-01", "text": "   "},        # blank text → skipped
        {"text": "no date"},                          # no date → skipped
        {"date": "2026-10-01"},                       # no text → skipped
    ]
    assert j1.items_due(items, "2026-10-01") == ["first", "second"]
    assert j1.items_due(items, "2026-12-25") == []


def test_reminder_message_format():
    j1 = load_module("owner_reminders")
    msg = j1.build_message("2026-10-02", ["item a", "item b"])
    assert msg.startswith("[OPS]")
    assert "Owner to-do for 2026-10-02" in msg
    assert "• item a" in msg and "• item b" in msg


def test_seeded_todo_json_loads_and_has_expected_days():
    j1 = load_module("owner_reminders")
    seed = OPS_DIR.parents[1] / "ops" / "owner_todo.json"
    items = j1.load_items(seed)
    # pruned 2026-10-07: only the three forward-looking items remain active
    assert {it["date"] for it in items} == {"2026-10-23", "2026-10-28", "2026-10-31"}
    assert all(it.get("text", "").strip() for it in items)
    # the pre-2026-10-07 items moved to a `done` list, not deleted
    with open(seed, encoding="utf-8") as fh:
        data = json.load(fh)
    done = data.get("done", [])
    assert {it["date"] for it in done} == {"2026-10-01", "2026-10-02", "2026-10-05"}
    assert all(it.get("text", "").strip() for it in done)


# ── J1–J5 telegram routing (consolidation 2026-10-07) ───────────────────────

JOB_EVENTS = {
    "owner_reminders.py": "ops.owner_reminders",
    "p1_3_preflight.py": "ops.p1_3_preflight",
    "fq_snapshot_monthend.py": "ops.fq_snapshot",
    "ledger_push_weekly.py": "ops.ledger_push",
    "ops_health_daily.py": "ops.health_daily",
}


def test_ops_events_registered_with_brief_tiers():
    """The routing the consolidation brief orders: J1/J2/J3 are digest-tier
    decision support; J4/J5 send only on failure/anomaly (alert tier)."""
    from utils import notify_policy
    expected_tiers = {
        "ops.owner_reminders": notify_policy.TIER_DIGEST,
        "ops.p1_3_preflight": notify_policy.TIER_DIGEST,
        "ops.fq_snapshot": notify_policy.TIER_DIGEST,
        "ops.ledger_push": notify_policy.TIER_SEND,
        "ops.health_daily": notify_policy.TIER_SEND,
    }
    for event, tier in expected_tiers.items():
        assert event in notify_policy.EVENTS, event
        assert notify_policy.EVENTS[event][0] == tier, event


def test_every_send_ops_call_site_has_its_job_event():
    """AST check mirroring tests/test_notify_policy_classification.py but for
    the send_ops indirection: every job script passes its own registered
    ops.* event literal."""
    import ast
    for fname, expected_event in JOB_EVENTS.items():
        tree = ast.parse((OPS_DIR / fname).read_text())
        calls = [n for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                 and n.func.id == "send_ops"]
        assert calls, f"{fname}: no send_ops call sites found"
        for node in calls:
            kw = {k.arg: k for k in node.keywords}
            assert "event" in kw, f"{fname}:{node.lineno} — send_ops without event="
            val = kw["event"].value
            assert getattr(val, "value", None) == expected_event, \
                f"{fname}:{node.lineno} — expected {expected_event}"


def test_send_ops_requires_event_and_prints_in_dry(capsys):
    common = load_module("_common")
    with pytest.raises(TypeError):
        common.send_ops("[OPS] no event passed")          # event= is mandatory
    common.send_ops("[OPS] dry print", event="ops.owner_reminders", dry=True)
    assert "[OPS] dry print" in capsys.readouterr().out    # dry: print, no telegram


# ── J2 p1_3_preflight ───────────────────────────────────────────────────────

SAMPLE_DRY_RUN = """DRY RUN -- no files will be modified. Pass --apply to execute.
  source (prod):     data/walkforward.db
  destination:       data/research.db
  would migrate: research_runs (123 rows)
  would migrate: gate_decisions (45 rows)
  already migrated (absent from source): regime_profiles
  NOTE: this line is known chatter
  something odd happened
"""


def test_parse_dry_run_splits_counts_absent_unexpected():
    j2 = load_module("p1_3_preflight")
    counts, absent, unexpected = j2.parse_dry_run(SAMPLE_DRY_RUN)
    assert counts == {"research_runs": 123, "gate_decisions": 45}
    assert absent == ["regime_profiles"]
    assert unexpected == ["something odd happened"]


def test_preflight_message_flags_missing_tables():
    j2 = load_module("p1_3_preflight")
    counts = {"research_runs": 10, "gate_decisions": 2}
    absent = ["regime_profiles"]
    tables = j2.FALLBACK_TIER1_TABLES
    missing = [t for t in tables if t not in counts and t not in absent]
    msg = j2.build_message(counts, absent, tables, ["weird line"], missing, None)
    assert msg.startswith("[OPS]")
    assert "research_runs: 10 rows" in msg
    assert "regime_profiles: already migrated" in msg
    assert "tables missing from dry-run output" in msg
    assert "weird line" in msg
    # all 8 Tier-1 tables are named somewhere in the message
    for t in tables:
        assert t in msg


def test_preflight_is_exact_date_one_shot():
    j2 = load_module("p1_3_preflight")
    assert j2.TARGET_DATE == "2026-10-01"
    assert len(j2.FALLBACK_TIER1_TABLES) == 8


# ── J3 fq_snapshot_monthend ─────────────────────────────────────────────────

@pytest.mark.parametrize("day,expected", [
    (date(2026, 10, 30), True),   # Oct 31 2026 is a Saturday
    (date(2026, 10, 29), False),  # Thursday, but Friday 30 remains
    (date(2026, 12, 31), True),   # Dec 31 2026 is a Thursday
    (date(2027, 1, 29), True),    # Jan 31 2027 is a Sunday
    (date(2026, 1, 30), True),    # Jan 31 2026 is a Saturday
    (date(2026, 11, 30), True),   # Nov 30 2026 is Monday AND the last day of November
    (date(2026, 11, 27), False),  # Friday, Mon 30 remains
])
def test_last_weekday_of_month(day, expected):
    j3 = load_module("fq_snapshot_monthend")
    assert j3.is_last_weekday_of_month(day) is expected


@pytest.mark.parametrize("day,weekday", [
    (date(2026, 10, 30), True), (date(2026, 10, 31), False), (date(2026, 10, 29), True),
])
def test_weekday_gate(day, weekday):
    j3 = load_module("fq_snapshot_monthend")
    assert j3.is_weekday(day) is weekday


def test_month_key_zero_padded():
    j3 = load_module("fq_snapshot_monthend")
    assert j3.month_key(date(2027, 1, 15)) == "2027-01"
    assert j3.month_key(date(2026, 11, 1)) == "2026-11"


def _make_jwt(claims: dict) -> str:
    b64 = lambda obj: base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")
    return f"{b64({'alg': 'none'})}.{b64(claims)}."


def test_token_status_paths(tmp_path):
    j3 = load_module("fq_snapshot_monthend")
    now = time.time()
    ok = tmp_path / "tok_ok"
    ok.write_text(_make_jwt({"exp": now + 3600}))
    assert j3.token_status(ok, now_ts=now) is None
    expired = tmp_path / "tok_expired"
    expired.write_text(_make_jwt({"exp": now - 10}))
    assert "exp" in j3.token_status(expired, now_ts=now)
    margin = tmp_path / "tok_margin"
    margin.write_text(_make_jwt({"exp": now + 60}))
    assert "margin" in j3.token_status(margin, now_ts=now)
    noexp = tmp_path / "tok_noexp"
    noexp.write_text(_make_jwt({"iat": now}))
    assert "no exp" in j3.token_status(noexp, now_ts=now)
    garbage = tmp_path / "tok_garbage"
    garbage.write_text("not-a-jwt")
    assert "JWT" in j3.token_status(garbage, now_ts=now)
    empty = tmp_path / "tok_empty"
    empty.write_text("   \n")
    assert "empty" in j3.token_status(empty, now_ts=now)
    assert "no token file" in j3.token_status(tmp_path / "tok_missing", now_ts=now)


def test_distinct_captured_readonly(tmp_path):
    j3 = load_module("fq_snapshot_monthend")
    db = tmp_path / "research.db"
    assert j3.distinct_captured(db, "2026-10") == 0          # file absent → 0
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE fq_keystats_snapshot (ticker TEXT, snapshot_month TEXT)")
    conn.executemany("INSERT INTO fq_keystats_snapshot VALUES (?,?)",
                     [("A", "2026-10"), ("B", "2026-10"), ("A", "2026-10"), ("C", "2026-09")])
    conn.commit()
    conn.close()
    assert j3.distinct_captured(db, "2026-10") == 2
    plain = tmp_path / "plain.db"                             # table missing → 0
    sqlite3.connect(plain).close()
    assert j3.distinct_captured(plain, "2026-10") == 0


def test_snapshot_guards_order_and_reasons(tmp_path, monkeypatch):
    j3 = load_module("fq_snapshot_monthend")
    root = tmp_path
    monkeypatch.setenv("DB_PATH", str(tmp_path / "never_used.db"))
    # nothing exists → three reasons, month-count skipped
    reasons = j3.snapshot_guards(root, root / "data" / "research.db",
                                 root / "research" / "fq_snapshot.py",
                                 root / ".stockbit_token", "2026-10")
    assert any("research.db" in r for r in reasons)
    assert any("fq_snapshot.py" in r for r in reasons)
    assert any("token" in r for r in reasons)
    # everything present, token fresh, no rows → READY (empty reasons)
    (root / "data").mkdir()
    sqlite3.connect(root / "data" / "research.db").close()
    (root / "research").mkdir()
    (root / "research" / "fq_snapshot.py").write_text("# placeholder\n")
    root.joinpath(".stockbit_token").write_text(_make_jwt({"exp": time.time() + 7200}))
    assert j3.snapshot_guards(root, root / "data" / "research.db",
                              root / "research" / "fq_snapshot.py",
                              root / ".stockbit_token", "2026-10") == []
    # existing rows for the month → NOT READY
    conn = sqlite3.connect(root / "data" / "research.db")
    conn.execute("CREATE TABLE fq_keystats_snapshot (ticker TEXT, snapshot_month TEXT)")
    conn.execute("INSERT INTO fq_keystats_snapshot VALUES ('A','2026-10')")
    conn.commit()
    conn.close()
    reasons = j3.snapshot_guards(root, root / "data" / "research.db",
                                 root / "research" / "fq_snapshot.py",
                                 root / ".stockbit_token", "2026-10")
    assert any("already has rows" in r for r in reasons)


def test_parse_run_output_tolerates_surrounding_noise():
    j3 = load_module("fq_snapshot_monthend")
    payload = {"captured": ["A", "B"], "failed": [], "universe_size": 50}
    noisy = "WARNING something\n" + json.dumps(payload, indent=2) + "\ntail line\n"
    assert j3.parse_run_output(noisy) == payload
    assert j3.parse_run_output(json.dumps(payload)) == payload


# ── J4 ledger_push_weekly ───────────────────────────────────────────────────

def test_push_rejection_detection():
    j4 = load_module("ledger_push_weekly")
    assert j4.push_rejected(" ! [rejected] master -> master (non-fast-forward)") is True
    assert j4.push_rejected("error: failed to push some refs") is False
    assert j4.BRANCH == "ops/hardening-2026-07-10"


# ── J5 ops_health_daily ─────────────────────────────────────────────────────

def _write_app_log(path: Path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")


def test_staged_fill_marker_counts_today_only(tmp_path):
    j5 = load_module("ops_health_daily")
    today = datetime.now(WIB).date()
    yes_iso = (datetime.now(WIB) - timedelta(days=1)).isoformat()
    now_iso = datetime.now(WIB).isoformat()
    log = tmp_path / "app.log"
    _write_app_log(log, [
        {"time": yes_iso, "msg": "[09:10] staged fills: 1 filled"},
        {"time": now_iso, "msg": "[10:10] staged fills: 0 filled"},
        {"time": now_iso, "msg": "unrelated"},
        {"time": now_iso, "msg": "staged fills: but malformed json"},  # bad json → next line
    ])
    # replace last record with a non-JSON line to exercise the lenient path
    lines = log.read_text().splitlines()
    lines[-1] = "not json at all staged fills:"
    log.write_text("\n".join(lines) + "\n")
    assert j5.staged_fill_markers_today(log, today) == 1


def test_count_sync_conflicts(tmp_path):
    j5 = load_module("ops_health_daily")
    git = tmp_path / ".git"
    git.mkdir()
    assert j5.count_sync_conflicts(git) == 0
    for i in range(4):
        (git / f"index.sync-conflict-2026081{i}-x").write_text("")
    assert j5.count_sync_conflicts(git) == j5.EXPECTED_SYNC_CONFLICTS == 4


def test_stuck_provider_switch_count(tmp_path, monkeypatch):
    j5 = load_module("ops_health_daily")
    db = tmp_path / "walkforward.db"
    monkeypatch.setenv("DB_PATH", str(db))
    assert j5.stuck_provider_switch_count(db) == 0     # no table → 0
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE audit_events (id INTEGER PRIMARY KEY, action TEXT, detail TEXT)")
    conn.executemany("INSERT INTO audit_events (action, detail) VALUES (?,?)", [
        ("provider_switch", "session limit; resumes ~2026-07-10T11:20:00+00:00"),
        ("provider_switch", "session limit; resumes ~2026-07-10T11:20:00+00:00"),
        ("provider_switch", "session limit; resumes ~2026-09-11T09:00:00+00:00"),
        ("something_else", "resumes ~2026-07-10T11:20:00+00:00"),
    ])
    conn.commit()
    conn.close()
    assert j5.stuck_provider_switch_count(db) == 2


def _make_fake_tree(tmp_path):
    """Minimal repo tree: scheduler/jobs.py WITHOUT the P3 symbol → marker check skipped."""
    root = tmp_path / "repo"
    (root / "scheduler").mkdir(parents=True)
    (root / "scheduler" / "jobs.py").write_text("def other(): pass\n")
    (root / "data").mkdir()
    sqlite3.connect(root / "data" / "walkforward.db").close()
    return root


def test_evaluate_healthy_silent_and_records_state(tmp_path, monkeypatch):
    j5 = load_module("ops_health_daily")
    root = _make_fake_tree(tmp_path)
    monkeypatch.setenv("DB_PATH", str(root / "data" / "walkforward.db"))
    anomalies, new_state = j5.evaluate(
        root, date(2026, 10, 2),
        paused=lambda: True,
        conflicts=lambda git_dir: 4,
        branch=lambda r: "ops/hardening-2026-07-10",
        active=lambda: True,
        markers=lambda log, today: 1,
        stuck_count=lambda db: 5,
        state={"provider_switch_stuck": 5},
    )
    assert anomalies == []
    assert new_state["provider_switch_stuck"] == 5
    assert new_state["as_of"] == "2026-10-02"


def test_evaluate_reports_each_anomaly(tmp_path, monkeypatch):
    j5 = load_module("ops_health_daily")
    root = _make_fake_tree(tmp_path)
    monkeypatch.setenv("DB_PATH", str(root / "data" / "walkforward.db"))
    anomalies, new_state = j5.evaluate(
        root, date(2026, 10, 2),
        paused=lambda: False,                       # anomaly 1
        conflicts=lambda git_dir: 5,                # anomaly 2
        branch=lambda r: "research/x",              # anomaly 3
        active=lambda: False,                       # anomaly 4
        markers=lambda log, today: 0,               # skipped (no P3 symbol in fake tree)
        stuck_count=lambda db: 9,                   # anomaly 6 (increase)
        state={"provider_switch_stuck": 2},
    )
    assert len(anomalies) == 5
    assert any("UNPAUSED" in a for a in anomalies)
    assert any("sync-conflict" in a for a in anomalies)
    assert any("research/x" in a for a in anomalies)
    assert any("not active" in a for a in anomalies)
    assert any("2026-07-10T11:20:00" in a and "2 -> 9" in a for a in anomalies)
    assert new_state["provider_switch_stuck"] == 9


def test_evaluate_first_run_baseline_no_alert(tmp_path, monkeypatch):
    j5 = load_module("ops_health_daily")
    root = _make_fake_tree(tmp_path)
    monkeypatch.setenv("DB_PATH", str(root / "data" / "walkforward.db"))
    anomalies, _ = j5.evaluate(
        root, date(2026, 10, 2),
        paused=lambda: True, conflicts=lambda g: 4,
        branch=lambda r: "ops/hardening-2026-07-10", active=lambda: True,
        markers=lambda log, today: 1, stuck_count=lambda db: 7, state={},
    )
    assert anomalies == []          # no baseline yet → record only


def test_evaluate_p3_marker_check_activates_with_symbol(tmp_path, monkeypatch):
    j5 = load_module("ops_health_daily")
    root = _make_fake_tree(tmp_path)
    (root / "scheduler" / "jobs.py").write_text("def run_staged_entry_fills(): pass\n")
    monkeypatch.setenv("DB_PATH", str(root / "data" / "walkforward.db"))
    anomalies, _ = j5.evaluate(
        root, date(2026, 10, 2),
        paused=lambda: True, conflicts=lambda g: 4,
        branch=lambda r: "ops/hardening-2026-07-10", active=lambda: True,
        markers=lambda log, today: 0, stuck_count=lambda db: 1, state={},
    )
    assert len(anomalies) == 1
    assert "staged fills" in anomalies[0]
