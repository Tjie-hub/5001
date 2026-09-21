"""Persist alpha-falsification rejection records — research.db failure_registry only.

Part of the 2026-09-03 alpha falsification pass (audit handover task 5):
rejected candidates and their reasons are recorded so selection bias stays
measurable. Append-only, dedup-protected; no production tables touched.
"""
import sqlite3
import sys

from config import DB_PATH as WF_DB_PATH
from research.db import connect_research
from research.knowledge.models import FailureRecord
from research.knowledge.storage import insert_failure

SOURCE = "alpha-falsification-2026-09-03"

REJECTIONS = [
    FailureRecord(
        hypothesis_id=None,
        reject_reason=("Liquidity Sweep: pooled OOS expectancy negative under BOTH exit "
                       "rules — unbounded baseline -1.01%/trade (33,122 trades) and "
                       "hold_days=10 parity rule -1.00%/trade (40,539 trades); positive-"
                       "cell share falls 21.4%->19.0% under the parity rule. Per-ticker "
                       "positive tail inside a negative cross-ticker mean = multiplicity "
                       "artifact. Stays disabled."),
        source="manual",
        failing_stage="oos_evidence",
        evidence_ref=("data/reports/ls_hold10_parity_2026-09-03.md; wf_edge run 08ff0ca6 "
                      "(31,136 trades, -0.984%/trade)"),
        fingerprint=f"{SOURCE}:liquidity-sweep:hold10-parity",
    ),
    FailureRecord(
        hypothesis_id=None,
        reject_reason=("distribution (SELL/detector path): forward shadow cohort is the "
                       "largest forward sample in the system and is negative — 2,133 "
                       "closed trades at -0.05%/trade mean (Jun-Sep 2026), negative in "
                       "every month. No OOS edge; forward evidence confirms."),
        source="manual",
        failing_stage="forward_evidence",
        evidence_ref="ft_shadow_trade strategy='distribution' @ walkforward.db",
        fingerprint=f"{SOURCE}:distribution:shadow-negative",
    ),
    FailureRecord(
        hypothesis_id=None,
        reject_reason=("NR7 Breakout: falsified as a strategy-level edge. Persisted "
                       "wf_edge positive expectancy (+1.64pp, 54 cells) is a selection "
                       "artifact of the n>=20 aggregation floor — pooled over ALL 858 "
                       "tickers producing NR7 OOS trades, expectancy is -0.18%/trade "
                       "(6,183 trades, bootstrap 95% CI [-0.37, +0.02] includes 0). "
                       "Losses concentrate in illiquid names (low-volume tercile "
                       "-0.72pp); only 2025 of 5 years is positive; 2026 YTD -0.88pp. "
                       "Targeted rule-parity rerun (run 2597066b, weekly_mtf_trend gate, "
                       "warmup 160) narrows 54 bare cells to 3/959 tickers "
                       "(LAND +1.94 n=21, LAPD +3.59 n=27, TAMA +0.81 n=25), all with "
                       "consistency <=31.2% vs the 50% bar. Gatekeeper had already "
                       "REJECTed x5 (walk_forward consistency 47.96%); registry demoted "
                       "to SHADOW (D-029, 'No capital'). Stays SHADOW/blocked; not "
                       "PROVEN, not PROMISING."),
        source="manual",
        failing_stage="multiple_testing",
        evidence_ref=("data/reports/nr7_falsification_2026-09-03.md; "
                      "data/reports/ls_hold10_parity_2026-09-03.md; wf_edge_rule "
                      "run 2597066b @ walkforward.db"),
        fingerprint=f"{SOURCE}:nr7-breakout:strategy-level-falsified",
    ),
]


def main() -> int:
    # sanity: research db reachable and prod attached read-only by connect_research
    with connect_research() as conn:
        for rec in REJECTIONS:
            fid = insert_failure(conn, rec)
            print(f"recorded: {rec.fingerprint} -> {fid or 'dedup no-op'}")
    # read-only touch of prod db to confirm path sanity (no writes)
    sqlite3.connect(f"file:{WF_DB_PATH}?mode=ro", uri=True).close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
