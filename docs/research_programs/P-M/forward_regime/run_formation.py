"""FWD-PM-REGIME-002 formation recorder.

Appends closed trades to ledger.json. Read-only against the production DB.

Records `ihsg_regime_at_entry` and `ihsg_weekly_regime_at_entry`
(BULL / BEAR / SIDEWAYS, from the production classifier
`engine.regime_filter.detect_regime` on daily and weekly IHSG bars) purely as
OBSERVABILITY attributes. It is never used to filter, gate or size anything: every signal the
frozen section 2 specification emits is recorded regardless of regime, and the
section 3 endpoint is computed over all of them. Its purpose is to let the 2029
decision be informed by FORWARD evidence on regime conditioning rather than a
backtest fitted to 9 BULL episodes.
Run daily after the settled-bar write. Never back-fills: a trade whose entry
predates `opened_utc` is refused, because replaying the backtest into this
ledger would convert in-sample discovery into an apparent forward record.
"""
import json, sys, hashlib
from datetime import datetime, timezone
from pathlib import Path
import numpy as np, pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from data.db import connect                      # the one sanctioned connection path
from engine.exits.costs import COMMISSION_BUY, COMMISSION_SELL, SLIPPAGE
from engine.regime_filter import detect_regime   # observability only — never gates anything

HERE = Path(__file__).parent
LEDGER = HERE / "ledger.json"
BUY = COMMISSION_BUY + SLIPPAGE                  # 0.25%
SELL = COMMISSION_SELL + SLIPPAGE                # 0.35%
SLOPE_MIN, ER_MIN, PA_MIN, ATR_MULT, CAP = 0.02, 0.30, 0.70, 3.0, 60
ADV_MIN, PX_MIN, WARMUP = 1e9, 50.0, 25
NZ_MIN = 18          # 002: >=18 of trailing 20 sessions must have traded (volume>0)

def load_panel(conn):
    df = pd.read_sql(
        "SELECT ticker,date,open,high,low,close,volume FROM ohlcv "
        "WHERE is_final=1 AND close>0 AND volume>=0", conn)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values(["ticker", "date"]).reset_index(drop=True)

def features(df):
    g = df.groupby("ticker", sort=False)
    df["ema20"] = g["close"].transform(lambda s: s.ewm(span=20, adjust=False, min_periods=20).mean())
    df["atr14"] = g.apply(lambda x: (x.high - x.low).rolling(14, min_periods=14).mean(),
                          include_groups=False).reset_index(level=0, drop=True)
    df["adv20"] = g.apply(lambda x: (x.close * x.volume).rolling(20, min_periods=15).mean(),
                          include_groups=False).reset_index(level=0, drop=True)
    df["adv20"] = df.groupby("ticker", sort=False)["adv20"].shift(1)
    df["slope"] = df["ema20"] / g["ema20"].shift(10) - 1
    absmv = g["close"].transform(lambda s: s.diff().abs().rolling(20, min_periods=20).sum())
    df["er"] = g["close"].transform(lambda s: (s - s.shift(20)).abs()) / absmv.replace(0, np.nan)
    df["pa"] = g.apply(lambda x: (x.close > x.ema20).rolling(20, min_periods=20).mean(),
                       include_groups=False).reset_index(level=0, drop=True)
    df["n"] = g.cumcount()
    # 002 traded-days guard: a suspended IDX name prints a zero-volume carry-forward bar,
    # which drives Kaufman ER toward 1.0 because the denominator stops growing.
    df["nz"] = (df.volume > 0).astype(int)
    df["nz20"] = g["nz"].transform(lambda s: s.shift(1).rolling(20, min_periods=20).sum())
    gg = df.groupby("ticker", sort=False)
    # state is evaluated on data through t-1 only
    df["UP"] = ((gg["slope"].shift(1) > SLOPE_MIN) & (gg["er"].shift(1) >= ER_MIN)
                & (gg["pa"].shift(1) >= PA_MIN)).fillna(False)
    df["liq"] = ((df.adv20 >= ADV_MIN) & (df.close >= PX_MIN) & (df.n >= WARMUP)
                 & (df.volume > 0) & (df.nz20 >= NZ_MIN)).fillna(False)
    return df

def ihsg_regimes(df, since):
    """BULL/BEAR/SIDEWAYS per session from the production classifier.

    Computed only for sessions at or after `since` (entries can only be as old
    as the 60-session cap), each from history up to that bar — no look-ahead.
    Fail-soft: any classifier error records None rather than dropping the trade,
    because this attribute must never be able to block a formation.
    """
    ih = df[df.ticker == "IHSG"][["date", "open", "high", "low", "close", "volume"]]
    ih = ih.sort_values("date").reset_index(drop=True)
    out = {}
    start = max(0, ih.index[ih.date >= since].min() - 1 if (ih.date >= since).any() else 0)
    for i in range(int(start), len(ih)):
        try:
            out[ih.date.iloc[i]] = detect_regime(ih.iloc[max(0, i - 120):i + 1].copy())
        except Exception:
            out[ih.date.iloc[i]] = None
    return out


def weekly_regimes(df, since):
    """BULL/BEAR/SIDEWAYS from WEEKLY IHSG bars, keyed by the week's close date.

    No look-ahead, and this is the subtle part: an entry on a Wednesday can only
    see the last CLOSED weekly bar, never the in-progress one. `weekly_at` below
    therefore selects the latest week whose close date is strictly BEFORE the
    entry date.
    """
    ih = df[df.ticker == "IHSG"].set_index("date").sort_index()
    wk = ih.resample("W-FRI").agg(
        open=("open", "first"), high=("high", "max"),
        low=("low", "min"), close=("close", "last"),
        volume=("volume", "sum")).dropna().reset_index()
    wk = wk[wk.date >= since - pd.Timedelta(weeks=70)].reset_index(drop=True)
    out = []
    for i in range(len(wk)):
        if i < 30:
            out.append((wk.date.iloc[i], None)); continue
        try:
            out.append((wk.date.iloc[i], detect_regime(wk.iloc[max(0, i - 60):i + 1].copy())))
        except Exception:
            out.append((wk.date.iloc[i], None))
    return out


def weekly_at(weeks, entry_date):
    """Regime of the last weekly bar CLOSED strictly before `entry_date`."""
    prior = [r for (d0, r) in weeks if d0 < entry_date]
    return prior[-1] if prior else None


def closed_trades(df, ihsg, opened, regimes, weeks):
    out = []
    for tk, x in df.groupby("ticker", sort=False):
        up, lq = x.UP.values, x.liq.values
        if not up.any():
            continue
        cl, hi, at, dt = x.close.values, x.high.values, x.atr14.values, x.date.values
        N = len(x)
        starts = np.where(up & ~np.r_[False, up[:-1]] & lq & ~np.isnan(at))[0]
        for i in starts:
            if pd.Timestamp(dt[i]) < opened:       # never back-fill
                continue
            peak, j, why = hi[i], None, None
            for k in range(1, min(CAP, N - 1 - i) + 1):
                p = i + k
                peak = max(peak, hi[p])
                if cl[p] < peak - ATR_MULT * at[p]:
                    j, why = p, "atr3_trail"
                    break
            if j is None:
                if i + CAP <= N - 1:
                    j, why = i + CAP, "cap_60"
                else:
                    continue                        # still open, not a closed trade
            ie, ix = ihsg.get(pd.Timestamp(dt[i])), ihsg.get(pd.Timestamp(dt[j]))
            if ie is None or ix is None:
                continue
            gross = cl[j] / cl[i] - 1
            net = gross - BUY - SELL
            mkt = ix / ie - 1
            out.append(dict(
                ticker=tk, entry_date=str(pd.Timestamp(dt[i]).date()), entry_close=float(cl[i]),
                exit_date=str(pd.Timestamp(dt[j]).date()), exit_close=float(cl[j]),
                sessions_held=int(j - i), exit_reason=why,
                gross_return=round(float(gross), 6), net_return=round(float(net), 6),
                ihsg_entry=float(ie), ihsg_exit=float(ix),
                market_return=round(float(mkt), 6), excess=round(float(net - mkt), 6),
                ihsg_regime_at_entry=regimes.get(pd.Timestamp(dt[i])),
                ihsg_weekly_regime_at_entry=weekly_at(weeks, pd.Timestamp(dt[i])),
                generated_utc=datetime.now(timezone.utc).isoformat()))
    return out

def main():
    led = json.loads(LEDGER.read_text())
    if not led.get("opened_utc"):
        sys.exit("ledger not opened: opened_utc is null. Set it and `family` before running.")
    opened = pd.Timestamp(led["opened_utc"][:10])
    with connect(read_only=True) as conn:
        df = features(load_panel(conn))
    regimes = ihsg_regimes(df, opened - pd.Timedelta(days=200))
    weeks = weekly_regimes(df, opened - pd.Timedelta(days=200))
    ih = df[df.ticker == "IHSG"].set_index("date")["close"].to_dict()
    df = df[df.ticker != "IHSG"]
    have = {(t["ticker"], t["entry_date"]) for t in led["trades"]}
    new = [t for t in closed_trades(df, ih, opened, regimes, weeks) if (t["ticker"], t["entry_date"]) not in have]
    if not new:
        print("no new closed trades")
        return
    led["trades"].extend(sorted(new, key=lambda t: (t["entry_date"], t["ticker"])))
    body = json.dumps(led["trades"], sort_keys=True).encode()
    led["fingerprint_sha256"] = hashlib.sha256(body).hexdigest()
    led["last_append_utc"] = datetime.now(timezone.utc).isoformat()
    LEDGER.write_text(json.dumps(led, indent=2))
    print(f"appended {len(new)} closed trades; total {len(led['trades'])}; "
          f"fingerprint {led['fingerprint_sha256'][:12]}…")

if __name__ == "__main__":
    main()
