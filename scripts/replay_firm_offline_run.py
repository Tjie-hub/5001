"""Runtime replay harness — runs the Agent Firm exactly as production does,
for the 8 tickers from the 04:43 UTC offline run.

Uses the REAL production path: engine.agent_firm.firm.evaluate_staged(), with
a real ProviderRouter built by factory.build_router(), against the real DB.
No mocks, no bypasses.

Adds a distinct scan_time marker ("REPLAY-2026-07-21T12:16") so the rows this
script writes to agent_decisions / agent_traces / provider_events can be
identified and cleaned up separately from real scheduler activity.
"""
import asyncio
import datetime as dt
import json
import sys
import time

# Ensure the project root is importable when run as a script.
sys.path.insert(0, "/home/tjiesar/10 Projects/idx-walkforward-5001")

from engine.agent_firm import config as firm_cfg  # noqa: E402
from engine.agent_firm import firm as firm_mod  # noqa: E402
from engine.agent_firm.providers.factory import build_router  # noqa: E402
from engine.agent_firm.schemas import SignalCandidate  # noqa: E402

TICKERS = ["CDIA", "ADRO", "JGLE", "TRON", "LPPS", "COCO", "RAJA", "MLPL"]
SCAN_TIME = "2026-07-21 REPLAY-12:16-UTC"


def banner(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def build_candidates():
    # Same fields production uses (scheduler/jobs.py:831-836).
    return [
        SignalCandidate(
            ticker=t, strategy="eod", score=1.0, scan_time=SCAN_TIME,
            flow_verdict=None,
            indicators={"sources": ["R"], "confluence": 1, "vol_ratio": 1.0,
                        "net_value": 0.0},
        )
        for t in TICKERS
    ]


def snapshot_provider_events(db_path, since_id):
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, event_type, provider, substr(reason,1,55) AS reason, "
        "reset_time, created_at FROM provider_events WHERE id > ? "
        "ORDER BY id".replace("?", str(since_id))
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def main():
    banner("PRE-FLIGHT: runtime configuration")
    print(f"FIRM_ENABLED           : {firm_cfg.FIRM_ENABLED}")
    print(f"PROVIDER_MODE          : {firm_cfg.PROVIDER_MODE}")
    print(f"PROVIDER_ORDER         : {firm_cfg.PROVIDER_ORDER}")
    print(f"ZAI_API_KEY set        : {bool(firm_cfg.ZAI_API_KEY)}")
    print(f"CLAUDE_MAX_CALLS_PER_DAY: {firm_cfg.CLAUDE_MAX_CALLS_PER_DAY}")
    print(f"UTC now                : {dt.datetime.now(dt.timezone.utc).isoformat()}")

    banner("PRE-FLIGHT: build the production router (factory.build_router)")
    router = build_router()
    print("Router provider_status() snapshot:")
    for s in router.provider_status():
        print(f"  {s['provider']:<8} available={s['available']!s:<5} "
              f"circuit={s['circuit_state']:<8} reason={s['reason']} "
              f"hold_until={s['quota_hold_until']}")

    # Capture the event id watermark so we can attribute events this run creates.
    import data.db as _db
    db_path = str(_db.DB_PATH)
    import sqlite3
    pre_max_id = sqlite3.connect(db_path).execute(
        "SELECT COALESCE(MAX(id),0) FROM provider_events").fetchone()[0]
    print(f"\nprovider_events id watermark before replay: {pre_max_id}")

    banner(f"REPLAY: evaluate_staged() for {len(TICKERS)} tickers "
           f"(real production path, real providers)")
    firm_mod.reset_market_ctx()
    t0 = time.monotonic()
    try:
        decisions = firm_mod.evaluate_staged(build_candidates())
        outcome = "OK"
        err = None
    except Exception as e:
        decisions = []
        outcome = "EXCEPTION"
        err = f"{type(e).__name__}: {e}"
    elapsed = time.monotonic() - t0
    print(f"evaluate_staged returned in {elapsed:.1f}s — outcome={outcome}")
    if err:
        print(f"ERROR: {err}")

    banner("PER-TICKER RESULTS (decision + per-agent traces)")
    print(f"{'Ticker':<7}{'Decision':<10}{'Conf':<6}{'#traces':<9}"
          f"{'Providers':<22}{'Rationale':<30}")
    print("-" * 84)
    for d in decisions:
        provs = ",".join(d.providers_used) or "-"
        conf = f"{d.confidence:.2f}" if d.confidence is not None else "-"
        rat = (d.rationale or "")[:28]
        print(f"{d.ticker:<7}{d.decision:<10}{conf:<6}{len(d.traces):<9}"
              f"{provs:<22}{rat:<30}")

    banner("PER-TICKER PER-AGENT BREAKDOWN")
    for d in decisions:
        print(f"\n--- {d.ticker} (decision={d.decision}) ---")
        if not d.traces:
            print("  (no traces — decision was bypassed/degraded with no LLM call)")
            continue
        print(f"  {'Role':<11}{'Status':<8}{'Provider':<10}{'Failover':<9}"
              f"{'Dur(s)':<8}{'Error/Output':<40}")
        for tr in d.traces:
            err_or_out = (tr.error or "")[:38] or \
                (json.dumps(tr.output)[:38] if tr.output else "")
            print(f"  {tr.role:<11}{tr.status:<8}{tr.provider or '-':<10}"
                  f"{str(tr.failover):<9}{tr.duration_s:<8.2f}{err_or_out:<40}")

    banner("PROVIDER EVENTS WRITTEN BY THIS REPLAY")
    new_events = snapshot_provider_events(db_path, pre_max_id)
    print(f"{len(new_events)} new provider_events rows (id > {pre_max_id}):")
    print(f"  {'event_type':<26}{'provider':<9}{'created_at':<22}reason")
    for e in new_events[:60]:
        print(f"  {e['event_type']:<26}{e['provider']:<9}{e['created_at']:<22}"
              f"{e['reason']}")

    # Tally
    from collections import Counter
    tally = Counter((e["provider"], e["event_type"]) for e in new_events)
    banner("PROVIDER USAGE SUMMARY (this replay)")
    for (prov, etype), n in sorted(tally.items()):
        print(f"  {prov:<8} {etype:<28} {n}")
    if not tally:
        print("  (no provider events — no LLM calls attempted)")

    banner("VERDICT")
    n_approve = sum(1 for d in decisions if d.decision == "approve")
    n_veto = sum(1 for d in decisions if d.decision == "veto")
    n_degraded = sum(1 for d in decisions if d.decision == "degraded")
    n_bypassed = sum(1 for d in decisions if d.decision == "bypassed")
    print(f"  approve={n_approve}  veto={n_veto}  degraded={n_degraded}  "
          f"bypassed={n_bypassed}  (total {len(decisions)})")
    real_evals = n_approve + n_veto
    if real_evals > 0:
        print(f"  -> Firm OPERATIONAL: {real_evals}/{len(TICKERS)} tickers got a "
              f"real AI evaluation (approve/veto).")
    elif n_degraded > 0 and real_evals == 0:
        print(f"  -> Firm OFFLINE: all {n_degraded} tickers degraded (no provider "
              f"could serve the risk agent).")
    elif n_bypassed > 0:
        print(f"  -> Firm DISABLED (bypassed). Check FIRM_ENABLED / kill-switch.")
    else:
        print("  -> AMBIGUOUS outcome — inspect per-ticker breakdown above.")


if __name__ == "__main__":
    main()
