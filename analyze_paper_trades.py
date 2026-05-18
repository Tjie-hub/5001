import sqlite3
import os
from collections import defaultdict
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "walkforward.db")
OUT_DIR = os.path.join(os.path.dirname(__file__), "docs", "analysis")
TODAY = datetime.today().strftime("%Y-%m-%d")
OUT_FILE = os.path.join(OUT_DIR, f"{TODAY}-paper-trade-signal-audit.md")


def classify(row):
    status = row["status"]
    pnl = row["pnl_pct"] or 0
    if status == "OPEN":
        return "OPEN"
    return "WIN" if pnl > 0 else "LOSS"


def avg(vals):
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def fmt(v, decimals=2, suffix=""):
    if v is None:
        return "—"
    return f"{v:.{decimals}f}{suffix}"


def most_common(lst):
    lst = [x for x in lst if x is not None]
    if not lst:
        return "—"
    return max(set(lst), key=lst.count)


def vol_bucket(vr):
    if vr is None:
        return "unknown"
    if vr < 1.3:
        return "<1.3x"
    if vr < 2.0:
        return "1.3–2.0x"
    return ">2.0x"


def run():
    os.makedirs(OUT_DIR, exist_ok=True)

    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row

    rows = con.execute("""
        SELECT
            pt.ticker, pt.strategy, pt.entry_date, pt.entry_price,
            pt.tp_price, pt.sl_price, pt.pnl_pct, pt.pnl_rp,
            pt.exit_reason, pt.status, pt.adx_peak, pt.highest_seen, pt.atr14,
            ds.vol_ratio, ds.delta, ds.cum_delta, ds.signal,
            ds.consec_up, ds.vpin, ds.vpin_label, ds.vwap
        FROM paper_trades pt
        LEFT JOIN daily_screen ds
            ON pt.ticker = ds.ticker AND pt.entry_date = ds.date
        ORDER BY pt.entry_date
    """).fetchall()
    con.close()

    rows = [dict(r) for r in rows]
    for r in rows:
        r["outcome"] = classify(r)

    closed = [r for r in rows if r["outcome"] != "OPEN"]
    wins = [r for r in closed if r["outcome"] == "WIN"]
    losses = [r for r in closed if r["outcome"] == "LOSS"]
    open_trades = [r for r in rows if r["outcome"] == "OPEN"]

    total_pnl = sum(r["pnl_rp"] or 0 for r in closed)
    capital = sum(r.get("entry_price", 0) or 0 for r in rows)
    win_rate = len(wins) / len(closed) * 100 if closed else 0
    avg_return = avg([r["pnl_pct"] for r in closed])

    lines = []
    a = lines.append

    a(f"# Paper Trade Signal Edge Audit — {TODAY}\n")
    a("> Cross-referencing paper trade outcomes with screener signals at entry to identify edge conditions.\n")

    # 1. Executive Summary
    a("## 1. Executive Summary\n")
    a(f"| Metric | Value |")
    a(f"|--------|-------|")
    a(f"| Total trades | {len(rows)} |")
    a(f"| Closed | {len(closed)} |")
    a(f"| Open | {len(open_trades)} |")
    a(f"| Win rate (closed) | {win_rate:.0f}% ({len(wins)}W / {len(losses)}L) |")
    a(f"| Avg return (closed) | {fmt(avg_return)}% |")
    a(f"| Avg win return | {fmt(avg([r['pnl_pct'] for r in wins]))}% |")
    a(f"| Avg loss return | {fmt(avg([r['pnl_pct'] for r in losses]))}% |")
    a(f"| Total PnL | Rp {total_pnl:,.0f} |")
    a("")

    # 2. Signal Profile: Wins vs Losses
    a("## 2. Signal Profile: Wins vs Losses\n")
    a("| Metric | WINS | LOSSES |")
    a("|--------|------|--------|")

    def grp(group, key):
        return avg([r[key] for r in group])

    metrics = [
        ("Avg VPIN", "vpin", lambda v: fmt(v, 3)),
        ("Avg vol_ratio", "vol_ratio", lambda v: fmt(v)),
        ("Avg delta", "delta", lambda v: fmt(v, 0)),
        ("Avg cum_delta", "cum_delta", lambda v: fmt(v, 0)),
        ("Avg consec_up", "consec_up", lambda v: fmt(v, 1)),
        ("Avg ADX peak", "adx_peak", lambda v: fmt(v, 1)),
    ]
    for label, key, fmtfn in metrics:
        wv = grp(wins, key)
        lv = grp(losses, key)
        a(f"| {label} | {fmtfn(wv)} | {fmtfn(lv)} |")

    a(f"| Most common signal | {most_common([r['signal'] for r in wins])} | {most_common([r['signal'] for r in losses])} |")
    a(f"| Most common VPIN label | {most_common([r['vpin_label'] for r in wins])} | {most_common([r['vpin_label'] for r in losses])} |")
    a("")

    # 3. VPIN Distribution
    a("## 3. VPIN Label Distribution\n")
    a("| VPIN Label | Trades | Wins | Win Rate | Avg Return |")
    a("|------------|--------|------|----------|------------|")
    vpin_groups = defaultdict(list)
    for r in closed:
        vpin_groups[r["vpin_label"] or "unknown"].append(r)
    for label in ["LOW", "MODERATE", "HIGH", "TOXIC", "unknown"]:
        grp_rows = vpin_groups.get(label, [])
        if not grp_rows:
            continue
        w = [r for r in grp_rows if r["outcome"] == "WIN"]
        wr = len(w) / len(grp_rows) * 100
        ar = avg([r["pnl_pct"] for r in grp_rows])
        a(f"| {label} | {len(grp_rows)} | {len(w)} | {wr:.0f}% | {fmt(ar)}% |")
    a("")

    # 4. Volume Ratio Buckets
    a("## 4. Volume Ratio Buckets\n")
    a("| Vol Ratio | Trades | Win Rate | Avg Return |")
    a("|-----------|--------|----------|------------|")
    bkt_groups = defaultdict(list)
    for r in closed:
        bkt_groups[vol_bucket(r["vol_ratio"])].append(r)
    for bkt in ["<1.3x", "1.3–2.0x", ">2.0x", "unknown"]:
        grp_rows = bkt_groups.get(bkt, [])
        if not grp_rows:
            continue
        w = [r for r in grp_rows if r["outcome"] == "WIN"]
        wr = len(w) / len(grp_rows) * 100
        ar = avg([r["pnl_pct"] for r in grp_rows])
        a(f"| {bkt} | {len(grp_rows)} | {wr:.0f}% | {fmt(ar)}% |")
    a("")

    # 5. Per-Strategy Performance
    a("## 5. Per-Strategy Performance\n")
    a("| Strategy | Trades | Win Rate | Avg Return | Avg VPIN | Avg Vol Ratio |")
    a("|----------|--------|----------|------------|----------|----------------|")
    strat_groups = defaultdict(list)
    for r in closed:
        strat_groups[r["strategy"] or "unknown"].append(r)
    for strat, grp_rows in sorted(strat_groups.items()):
        w = [r for r in grp_rows if r["outcome"] == "WIN"]
        wr = len(w) / len(grp_rows) * 100
        ar = avg([r["pnl_pct"] for r in grp_rows])
        av = avg([r["vpin"] for r in grp_rows])
        avr = avg([r["vol_ratio"] for r in grp_rows])
        a(f"| {strat} | {len(grp_rows)} | {wr:.0f}% | {fmt(ar)}% | {fmt(av, 3)} | {fmt(avr)} |")
    a("")

    # 6. Per-Trade Audit Table
    a("## 6. Per-Trade Audit\n")
    a("| # | Ticker | Strategy | Entry Date | Signal | VPIN | VPin Label | Vol Ratio | Delta | PnL% | Exit Reason | Outcome |")
    a("|---|--------|----------|------------|--------|------|------------|-----------|-------|------|-------------|---------|")
    for i, r in enumerate(rows, 1):
        no_data = r["vpin"] is None
        signal = r["signal"] or ("*no data*" if no_data else "—")
        vpin = fmt(r["vpin"], 3) if r["vpin"] is not None else "*no data*"
        vpin_lbl = r["vpin_label"] or ("*no data*" if no_data else "—")
        vr = fmt(r["vol_ratio"]) if r["vol_ratio"] is not None else "*no data*"
        delta = fmt(r["delta"], 0) if r["delta"] is not None else "*no data*"
        pnl = fmt(r["pnl_pct"]) + "%" if r["pnl_pct"] is not None else "open"
        exit_r = r["exit_reason"] or "—"
        outcome = r["outcome"]
        strat_short = r["strategy"].replace("Momentum Following", "Momentum").replace("Conservative Confirm", "Conservative").replace("Volume Profile POC", "VP-POC") if r["strategy"] else "—"
        a(f"| {i} | {r['ticker']} | {strat_short} | {r['entry_date']} | {signal} | {vpin} | {vpin_lbl} | {vr} | {delta} | {pnl} | {exit_r} | **{outcome}** |")
    a("")

    # 7. Key Findings
    a("## 7. Key Findings\n")

    findings = []

    # VPIN finding
    avg_vpin_wins = avg([r["vpin"] for r in wins])
    avg_vpin_losses = avg([r["vpin"] for r in losses])
    if avg_vpin_wins is not None and avg_vpin_losses is not None:
        if avg_vpin_wins < avg_vpin_losses:
            findings.append(f"**Lower VPIN at entry → better outcomes.** Winning trades had avg VPIN {avg_vpin_wins:.3f} vs {avg_vpin_losses:.3f} for losses — entering when informed trading pressure is lower reduces adverse selection risk.")
        else:
            findings.append(f"**Higher VPIN at entry → better outcomes.** Winning trades had avg VPIN {avg_vpin_wins:.3f} vs {avg_vpin_losses:.3f} for losses.")

    # Vol ratio finding
    avg_vr_wins = avg([r["vol_ratio"] for r in wins])
    avg_vr_losses = avg([r["vol_ratio"] for r in losses])
    if avg_vr_wins is not None and avg_vr_losses is not None:
        diff = avg_vr_wins - avg_vr_losses
        direction = "higher" if diff > 0 else "lower"
        findings.append(f"**Volume ratio at entry:** Wins averaged {fmt(avg_vr_wins)}x vs {fmt(avg_vr_losses)}x for losses — {direction} volume at entry correlated with {'better' if diff > 0 else 'worse'} outcomes.")

    # Delta finding
    avg_delta_wins = avg([r["delta"] for r in wins])
    avg_delta_losses = avg([r["delta"] for r in losses])
    if avg_delta_wins is not None and avg_delta_losses is not None:
        findings.append(f"**Delta (buy pressure) at entry:** Wins had avg delta {fmt(avg_delta_wins, 0)} vs {fmt(avg_delta_losses, 0)} for losses.")

    # Best VPIN label
    best_label = None
    best_wr = -1
    for label, grp_rows in vpin_groups.items():
        if len(grp_rows) < 2:
            continue
        w = [r for r in grp_rows if r["outcome"] == "WIN"]
        wr = len(w) / len(grp_rows)
        if wr > best_wr:
            best_wr = wr
            best_label = label
    if best_label:
        findings.append(f"**Best VPIN label:** `{best_label}` achieved the highest win rate ({best_wr*100:.0f}%) among labels with ≥2 trades.")

    # Best vol bucket
    best_bkt = None
    best_bkt_wr = -1
    for bkt, grp_rows in bkt_groups.items():
        if len(grp_rows) < 2:
            continue
        w = [r for r in grp_rows if r["outcome"] == "WIN"]
        wr = len(w) / len(grp_rows)
        if wr > best_bkt_wr:
            best_bkt_wr = wr
            best_bkt = bkt
    if best_bkt:
        findings.append(f"**Best volume ratio bucket:** `{best_bkt}` had the highest win rate ({best_bkt_wr*100:.0f}%) among buckets with ≥2 trades.")

    # No screener data
    no_data_count = sum(1 for r in rows if r["vpin"] is None)
    if no_data_count:
        findings.append(f"**Missing screener data:** {no_data_count} trade(s) had no matching `daily_screen` row at entry date — these are excluded from signal comparisons.")

    # Strategy finding
    if strat_groups:
        best_strat = max(strat_groups.items(), key=lambda x: avg([r["pnl_pct"] for r in x[1] if r["pnl_pct"] is not None]) or -999)
        br = avg([r["pnl_pct"] for r in best_strat[1]])
        findings.append(f"**Best strategy by avg return:** `{best_strat[0]}` averaged {fmt(br)}% return across {len(best_strat[1])} closed trades.")

    for f in findings:
        a(f"- {f}")
    a("")
    a("---")
    a(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Source: `data/walkforward.db` tables: `paper_trades`, `daily_screen`*")

    report = "\n".join(lines)
    with open(OUT_FILE, "w") as fh:
        fh.write(report)

    print(f"Report written to: {OUT_FILE}")
    print(f"\n--- PREVIEW ---\n")
    print(report)


def run_weekly_tracking():
    """
    Weekly tracking: compare live metrics against Plan 2 targets.
    Generates table matching plan3.md P6 format.
    """
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row

    rows = con.execute("""
        SELECT ticker, strategy, entry_date, exit_date, entry_price, exit_price,
               pnl_pct, pnl_rp, exit_reason, status, tp_price, sl_price
        FROM paper_trades
        ORDER BY entry_date
    """).fetchall()
    con.close()

    rows = [dict(r) for r in rows]
    closed = [r for r in rows if r['status'] == 'CLOSED']
    wins = [r for r in closed if (r['pnl_pct'] or 0) > 0]
    losses = [r for r in closed if (r['pnl_pct'] or 0) <= 0]

    # Win rate
    win_rate = len(wins) / len(closed) * 100 if closed else 0
    avg_win = avg([r['pnl_pct'] for r in wins]) if wins else 0
    avg_loss = avg([r['pnl_pct'] for r in losses]) if losses else 0

    # Watch entries (trades where entry had 'watch' signal in daily_screen)
    con2 = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    watch_entries = 0
    total_audited = 0
    for r in closed:
        row = con2.execute(
            "SELECT signal FROM daily_screen WHERE ticker=? AND date=?",
            (r['ticker'], r['entry_date'])
        ).fetchone()
        if row:
            total_audited += 1
            if row[0] == 'watch':
                watch_entries += 1
    con2.close()

    # VR > 5x entries (check from ohlcv data)
    con3 = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    vr_excessive = 0
    for r in closed:
        ohlcv = con3.execute(
            "SELECT volume FROM ohlcv WHERE ticker=? AND date=?",
            (r['ticker'], r['entry_date'])
        ).fetchone()
        if ohlcv:
            recent = con3.execute(
                "SELECT volume FROM ohlcv WHERE ticker=? AND date < ? ORDER BY date DESC LIMIT 20",
                (r['ticker'], r['entry_date'])
            ).fetchall()
            if len(recent) >= 20:
                avg_vol = sum(v[0] for v in recent) / 20
                vr = ohlcv[0] / avg_vol if avg_vol > 0 else 0
                if vr > 5.0:
                    vr_excessive += 1
    con3.close()

    # Partial TP triggered
    partial_tp = sum(1 for r in closed if r['exit_reason'] == 'PARTIAL_TP')
    partial_tp_rate = partial_tp / len(closed) * 100 if closed else 0

    # Watch entry loss rate
    watch_losses = 0
    for r in closed:
        con4 = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        row = con4.execute(
            "SELECT signal FROM daily_screen WHERE ticker=? AND date=?",
            (r['ticker'], r['entry_date'])
        ).fetchone()
        con4.close()
        if row and row[0] == 'watch' and (r['pnl_pct'] or 0) <= 0:
            watch_losses += 1

    lines = []
    a = lines.append

    a(f"## Weekly Tracking — {TODAY}\n")
    a("| Metrik | Baseline (Plan 1) | Target (Plan 2) | Aktual |")
    a("|--------|-------------------|-----------------|--------|")
    a(f"| Win rate | 35.7% | 50-55% | {win_rate:.1f}% ({len(wins)}W/{len(losses)}L) |")
    a(f"| Avg win | +18.5% | +15-20% | +{avg_win:.1f}% |")
    a(f"| Avg loss | -5.2% | < -5% | {avg_loss:.1f}% |")
    if watch_entries > 0:
        a(f"| Watch entries (entry=watch signal) | 4 (100% loss) | 0 | {watch_entries} ({watch_losses}/{watch_entries} loss) |")
    else:
        a("| Watch entries (entry=watch signal) | 4 (100% loss) | 0 | 0 |")
    a(f"| VR > 5x entries | 4 (25% WR) | 0 | {vr_excessive} |")
    a(f"| Partial TP triggered | 0/14 (0%) | ≥ 40% | {partial_tp}/{len(closed)} ({partial_tp_rate:.0f}%) |")
    a("")
    a(f"*Audited trades: {total_audited}/{len(closed)} have daily_screen data*")
    a("")

    tracking_file = os.path.join(OUT_DIR, "weekly-tracking.md")
    section_title = f"## Weekly Tracking — {TODAY}"
    try:
        existing = open(tracking_file).read()
    except (FileNotFoundError, OSError):
        existing = "# Weekly Tracking\n\n"

    # Skip if today's section already exists
    if section_title in existing:
        print(f"Weekly tracking for {TODAY} already exists, skipping.")
    else:
        with open(tracking_file, "w") as f:
            f.write(existing)
            f.write("\n".join(lines))
        print(f"Weekly tracking saved to: {tracking_file}")
    return {
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'watch_entries': watch_entries,
        'vr_excessive': vr_excessive,
        'partial_tp': partial_tp,
        'total_closed': len(closed),
    }


if __name__ == "__main__":
    import sys
    if "--weekly" in sys.argv:
        run_weekly_tracking()
    else:
        run()
