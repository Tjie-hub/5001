#!/usr/bin/env python3
"""Daily signal audit — run at 4pm WIB after 14:35 scan completes."""
import sqlite3
import datetime
import pathlib

BASE = pathlib.Path(__file__).parent
DB = BASE / "data" / "walkforward.db"
LOG = BASE / "logs" / "audit_signals.log"


def audit():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    today = datetime.date.today().isoformat()

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute(
        "SELECT COUNT(*), MAX(scan_time) FROM scheduled_signals WHERE DATE(scan_time) = ?",
        (today,),
    )
    count, latest_scan = cur.fetchone()

    cur.execute(
        """
        SELECT ticker, strategies, flow_score, flow_verdict, smart_money, scan_time
        FROM scheduled_signals
        WHERE DATE(scan_time) = ?
        ORDER BY flow_score DESC
        """,
        (today,),
    )
    rows = cur.fetchall()
    conn.close()

    lines = [f"=== SIGNAL AUDIT {now} ==="]
    lines.append(f"Date       : {today}")
    lines.append(f"Signals    : {count}")
    lines.append(f"Latest scan: {latest_scan or 'NONE'}")

    if count == 0:
        lines.append("STATUS     : WARNING — no signals today")
    elif latest_scan and latest_scan[:10] < today:
        lines.append("STATUS     : WARNING — latest scan is from a previous day")
    else:
        lines.append("STATUS     : OK")

    if rows:
        lines.append("")
        lines.append(f"{'TICKER':<8} {'FLOW':>4}  {'VERDICT':<14} {'SMART_MONEY':<14}  SCAN_TIME")
        lines.append("-" * 70)
        for ticker, strategies, flow_score, flow_verdict, smart_money, scan_time in rows:
            lines.append(
                f"{ticker:<8} {flow_score:>4}  {str(flow_verdict):<14} {str(smart_money):<14}  {scan_time}"
            )

    output = "\n".join(lines) + "\n"
    print(output)
    with open(LOG, "a") as f:
        f.write(output + "\n")


if __name__ == "__main__":
    audit()
