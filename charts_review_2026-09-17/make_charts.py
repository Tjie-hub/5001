"""Review charts for TUGU / SMMT Sep-16 signal. Read-only against walkforward.db."""
import sqlite3
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import os

DB = os.path.join(os.path.dirname(__file__), "..", "data", "walkforward.db")
OUT = os.path.dirname(os.path.abspath(__file__))
con = sqlite3.connect(f"file:{os.path.abspath(DB)}?mode=ro", uri=True)
cur = con.cursor()

GREEN, RED, BLUE, GRAY = "#1a9850", "#d73027", "#4575b4", "#888888"


def fetch_daily(ticker, start, end):
    cur.execute(
        "SELECT date, open, high, low, close, volume FROM ohlcv "
        "WHERE ticker=? AND date>=? AND date<=? ORDER BY date",
        (ticker, start, end),
    )
    return cur.fetchall()


def draw_daily(axp, axv, rows, title, levels, marks):
    n = len(rows)
    for i, (d, o, h, l, c, v) in enumerate(rows):
        up = c >= o
        color = GREEN if up else RED
        axp.vlines(i, l, h, color=color, linewidth=0.9)
        body_low, body_h = min(o, c), max(abs(c - o), 0.5)
        axp.add_patch(Rectangle((i - 0.32, body_low), 0.64, body_h,
                                facecolor=color, edgecolor=color, linewidth=0.5))
        axv.bar(i, v / 1e6, width=0.64, color=color, alpha=0.75)
    for price, label, color in levels:
        axp.axhline(price, color=color, linewidth=1.0, linestyle="--", alpha=0.8)
        axp.text(n + 0.5, price, f" {label}", color=color, fontsize=8, va="center")
    for idx, label, yoff, color in marks:
        if idx is None or idx >= n:
            continue
            d, o, h, l, c, v = rows[idx]
            axp.annotate(label, xy=(idx, h), xytext=(idx, h * yoff),
                         fontsize=8, color=color, ha="center",
                         arrowprops=dict(arrowstyle="-", color=color, lw=0.7))
    axp.set_xlim(-1, n + 12)
    axp.set_title(title, fontsize=11, loc="left")
    axp.grid(axis="y", alpha=0.25)
    axv.grid(axis="y", alpha=0.25)
    ticks = list(range(0, n, max(n // 9, 1)))
    axv.set_xticks(ticks)
    axv.set_xticklabels([rows[i][0][5:] for i in ticks], rotation=45, fontsize=7)
    axp.tick_params(labelbottom=False)
    axv.set_ylabel("Vol (M sh)", fontsize=8)
    axv.tick_params(labelsize=7)
    axp.tick_params(labelsize=7)


def idx_of(rows, date):
    for i, r in enumerate(rows):
        if r[0] == date:
            return i
    return None


def intraday(ticker, day):
    cur.execute(
        "SELECT bar_time, price FROM stockbit_flow_bars "
        "WHERE ticker=? AND trade_date=? ORDER BY bar_time", (ticker, day))
    out = []
    for t, p in cur.fetchall():
        hh, mm = int(t[:2]), int(t[3:5])
        out.append(((hh - 9) * 60 + mm, p))
    return out


# ---------------- SMMT daily ----------------
smmt = fetch_daily("SMMT", "2026-03-01", "2026-09-16")
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 7.2), sharex=True,
                               gridspec_kw={"height_ratios": [3, 1]}, dpi=130)
draw_daily(
    ax1, ax2, smmt, "SMMT daily — Mar-Sep 2026 (base → first leg (UMA) → quiet consolidation → Sep-16 second leg)",
    levels=[(3230, "prior 52w high 3230 (Apr-28)", RED),
            (2610, "Sep-4 breakout close 2610", BLUE)],
    marks=[(idx_of(smmt, "2026-09-01"), "Sep-1\npremover 95\ncl 1995", 0.86, "#6633cc"),
           (idx_of(smmt, "2026-09-04"), "Sep-4\n+24.9% breakout", 1.02, GREEN),
           (idx_of(smmt, "2026-09-08"), "Sep-7/8\nUMA + vol 12.7x", 1.04, GRAY),
           (idx_of(smmt, "2026-09-14"), "Sep 9-15: 7 sessions\ntight 2630-2820, vol dries up", 0.82, BLUE),
           (idx_of(smmt, "2026-09-16"), "Sep-16\n+15.7% cl 3100\nvol 10.2x", 1.03, GREEN)])
fig.tight_layout()
fig.savefig(os.path.join(OUT, "smmt_daily.png"), bbox_inches="tight")
plt.close(fig)

# ---------------- TUGU daily ----------------
tugu = fetch_daily("TUGU", "2026-03-01", "2026-09-16")
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 7.2), sharex=True,
                               gridspec_kw={"height_ratios": [3, 1]}, dpi=130)
draw_daily(
    ax1, ax2, tugu, "TUGU daily — Mar-Sep 2026 (range 1290-1525 → Sep-10 shock → flag → Sep-16 breakout to new 52w high)",
    levels=[(1525, "prior 52w high 1525 (Feb-24)", RED),
            (1675, "Sep-2022 high 1675 (4-yr line)", GRAY)],
    marks=[(idx_of(tugu, "2026-09-10"), "Sep-10\nvol shock 14.4M\ncl 1435 (+5.9%)", 0.90, GREEN),
           (idx_of(tugu, "2026-09-14"), "Sep 11-15: flag\nhigher lows 1395→1420", 0.84, BLUE),
           (idx_of(tugu, "2026-09-16"), "Sep-16 +12.0% cl 1630\nH1 +76% earnings\nvol 27.3M", 1.03, GREEN)])
fig.tight_layout()
fig.savefig(os.path.join(OUT, "tugu_daily.png"), bbox_inches="tight")
plt.close(fig)

# ---------------- Sep-16 intraday ----------------
fig, axes = plt.subplots(1, 2, figsize=(13, 4.6), dpi=130, sharey=False)
for ax, tk, open_px, close_px in [(axes[0], "SMMT", 2700, 3100),
                                  (axes[1], "TUGU", 1460, 1630)]:
    path = intraday(tk, "2026-09-16")
    if not path:
        continue
    xs = [m for m, p in path]
    ys = [p for m, p in path]
    ax.plot(xs, ys, linewidth=1.4, color="#222222")
    ax.fill_between(xs, min(ys), ys, alpha=0.08, color=BLUE)
    for t, lab in [(30, "09:30"), (60, "10:00"), (120, "11:00"), (240, "13:00"), (330, "14:30")]:
        ax.axvline(t, color=GRAY, linewidth=0.6, linestyle=":", alpha=0.7)
        ax.text(t, ax.get_ylim()[0], lab, fontsize=7, color=GRAY, ha="center", va="bottom")
    ax.axhline(open_px, color=GRAY, linewidth=0.7, linestyle="--")
    ax.axhline(close_px, color=RED, linewidth=0.9, linestyle="--")
    ax.text(340, close_px, f" close {close_px}", color=RED, fontsize=8, va="bottom")
    ax.set_title(f"{tk} — Sep 16 intraday (open {open_px})", fontsize=10, loc="left")
    ax.set_xlabel("minutes since 09:00", fontsize=8)
    ax.grid(alpha=0.25)
    ax.tick_params(labelsize=7)
    # timing stats
    total = (close_px / open_px - 1) * 100
    for cut, lab in [(30, "09:30"), (60, "10:00"), (120, "11:00")]:
        before = [(m, p) for m, p in path if m <= cut]
        if before:
            p_at = before[-1][1]
            print(f"{tk} {lab}: px={p_at}  move-so-far={100*(p_at/open_px-1):+.1f}%  "
                  f"of-day's-move={100*((p_at-open_px)/(close_px-open_px)):.0f}%")
    hi = max(ys)
    print(f"{tk} day: open={open_px} close={close_px} ({total:+.1f}%) intraday_hi={hi} close_vs_hi={100*(close_px/hi-1):.1f}%")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "sep16_intraday.png"), bbox_inches="tight")
plt.close(fig)

# move accounting from earlier signals
print("--- move accounting ---")
for tk, ref_close, ref_lab in [("SMMT", 1995, "Sep-1 premover close"),
                               ("SMMT", 2610, "Sep-4 breakout close"),
                               ("SMMT", 2700, "Sep-9..15 consolidation mid"),
                               ("TUGU", 1355, "Sep-9 pre-shock close"),
                               ("TUGU", 1435, "Sep-10 shock close"),
                               ("TUGU", 1430, "Sep-11..15 flag mid")]:
    last = 3100 if tk == "SMMT" else 1630
    print(f"{tk}: {ref_lab} {ref_close} -> Sep-16 close {last} = {100*(last/ref_close-1):+.1f}%")
print("charts saved to", OUT)
