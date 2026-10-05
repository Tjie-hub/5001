"""Cross-asset overnight series acquisition -- brief ZCODE_BRIEF_X1_OVERNIGHT_2026-10-05, P0-B.

Fetches the {X} signal legs and alignment benchmark from Yahoo Finance via yfinance
(free, no auth -- standing rule) into cross_asset/data/*.csv, with one MANIFEST.json
recording source, fetch UTC, yfinance version, auto_adjust setting, row count, date
range and sha256 for every file, plus a calendar-gap report (the USDIDR=X 214-day gap
must be locatable).

Core series (brief P0-B):
  EIDO     primary signal leg, US-listed 2010-05, adjusted (splits+dividends) close
  TLK      NYSE ADR, adjusted close (+ raw close kept for the ADS-ratio check)
  SPY      broad-US arm, adjusted close
  USDIDR=X indicative aggregate, close (NOT JISDOR -- see MANIFEST note)
  ^JKSE    alignment only; IDX prices for the book come from our corpus

Auxiliary (validity legs, not signal series):
  TLK raw close + TLKM.JK raw close: the ADS-ratio validity gate (a ratio change would
  show as a return in the raw pair after FX conversion).

Run from WSL:  ~/venv-x/bin/python fetch_cross_asset.py
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

CORE = [
    ("eido.csv", "EIDO", "EIDO iShares MSCI Indonesia ETF (US-listed 2010-05); adjusted close (auto_adjust=True: splits+dividends) + volume; PRIMARY signal leg"),
    ("tlk.csv", "TLK", "TLK Telkom Indonesia ADR (NYSE, 1995-10 IPO); adjusted close + volume; signal leg"),
    ("spy.csv", "SPY", "SPDR S&P 500 ETF; adjusted close + volume; broad-US arm"),
    ("usdidr.csv", "USDIDR=X", "USD/IDR Yahoo FX aggregate; close; INDICATIVE, not BI JISDOR"),
    ("jkse.csv", "^JKSE", "IDX composite (^JKSE); open+close; ALIGNMENT ONLY + discovery-half IHSG benchmark open->close (corpus IHSG starts 2021-07)"),
]
AUX = [
    ("tlk_raw.csv", "TLK", "TLK UNADJUSTED close; ADS-ratio / validity-gate leg"),
    ("tlkm_raw.csv", "TLKM.JK", "TLKM.JK UNADJUSTED close (IDX line); ADS-ratio / validity-gate leg"),
]


def sha256_of(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def gap_report(dates: pd.Series, min_days: int = 7) -> list[dict]:
    d = pd.to_datetime(dates).sort_values().reset_index(drop=True)
    diffs = d.diff().dt.days
    out = []
    for i in diffs[diffs > min_days].index:
        out.append({"from": str(d[i - 1].date()), "to": str(d[i].date()),
                    "gap_days": int(diffs[i])})
    return out


def fetch_one(ticker: str, auto_adjust: bool):
    t = yf.Ticker(ticker)
    h = t.history(period="max", auto_adjust=auto_adjust)
    if h is None or h.empty:
        raise RuntimeError(f"{ticker}: empty history")
    h = h.reset_index()
    dcol = "Date" if "Date" in h.columns else "index"
    h["date"] = pd.to_datetime(h[dcol]).dt.tz_localize(None).dt.normalize()
    h = h.rename(columns={"Close": "close", "Volume": "volume"})
    return t, h


def main() -> None:
    DATA.mkdir(exist_ok=True)
    man_p = HERE / "MANIFEST.json"
    manifest = json.loads(man_p.read_text()) if man_p.exists() else {
        "source": "Yahoo Finance via yfinance", "files": {}, "notes": [],
        "gap_report_gt_7d": {}}
    manifest["generated_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest["source"] = "Yahoo Finance via yfinance (free, scriptable, no auth) -- memo 04 POC path"
    manifest["yfinance_version"] = yf.__version__
    manifest["auto_adjust_core"] = True
    manifest.setdefault("host", "tjiejet / WSL Ubuntu (compute side per brief)")
    manifest.setdefault("files", {})
    manifest.setdefault("notes", [])
    manifest.setdefault("gap_report_gt_7d", {})
    # re-runs re-append these; drop stale copies of the standing notes first
    manifest["notes"] = [n for n in manifest["notes"] if not str(n).startswith(
        ("USDIDR=X is an indicative", "Adjusted closes (auto_adjust=True)",
         "^JKSE is alignment only"))]
    manifest["notes"] += [
        "USDIDR=X is an indicative aggregate, NOT BI's JISDOR fixing (memo 04). "
        "JISDOR public-download status is recorded separately in TIMING.md/PRIORS_X.md.",
        "Adjusted closes (auto_adjust=True) apply splits AND dividends -- total-return "
        "basis for EIDO/TLK/SPY as the brief requires. Raw closes are kept for TLK and "
        "TLKM.JK so the ADS-ratio validity gate can be run on unadjusted prices.",
        "^JKSE is alignment only; the LW book and TLKM outcomes come from the corpus "
        "through research.rulecard.data.load_extended_ohlcv(issuance=True).",
    ]
    splits_rows = []
    for fname, ticker, note in CORE + AUX:
        auto_adj = fname not in ("tlk_raw.csv", "tlkm_raw.csv")
        t, h = fetch_one(ticker, auto_adjust=auto_adj)
        h = h.rename(columns={"Open": "open"})
        cols = ["date", "close"] + (["open"] if fname == "jkse.csv" else []) + \
               (["volume"] if "volume" in h.columns else [])
        df = h[cols]
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        if "volume" in df.columns:
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
        df = df.dropna(subset=["close"]).reset_index(drop=True)
        p = DATA / fname
        df.to_csv(p, index=False)
        try:
            sp = t.splits
            if sp is not None and len(sp):
                for dt, ratio in sp.items():
                    if float(ratio) != 0:
                        splits_rows.append({"ticker": ticker, "date": str(pd.Timestamp(dt).date()),
                                            "ratio": float(ratio)})
        except Exception as e:  # noqa: BLE001 -- splits are a bonus; record failure
            splits_rows.append({"ticker": ticker, "error": f"{type(e).__name__}: {e}"[:120]})
        manifest["files"][fname] = {
            "ticker": ticker, "note": note, "auto_adjust": auto_adj,
            "rows": int(len(df)), "start": str(df["date"].min().date()),
            "end": str(df["date"].max().date()), "sha256": sha256_of(p),
        }
        if fname in {c[0] for c in CORE}:
            manifest["gap_report_gt_7d"][fname] = gap_report(df["date"])
    if splits_rows:
        sp_df = pd.DataFrame(splits_rows)
        sp_df.to_csv(DATA / "splits.csv", index=False)
        manifest["files"]["splits.csv"] = {
            "ticker": "EIDO/TLK/SPY/TLKM.JK", "note": "split events as reported by Yahoo (an ADS-ratio change must appear here)",
            "rows": int(len(sp_df)), "sha256": sha256_of(DATA / "splits.csv"),
        }
    (HERE / "MANIFEST.json").write_text(json.dumps(manifest, indent=1))
    print(json.dumps({k: v for k, v in manifest.items() if k != "files"}, indent=1))
    for f, meta in manifest["files"].items():
        print(f"{f:16s} {meta.get('ticker', ''):10s} rows={meta['rows']:6d} "
              f"{meta.get('start', '')}..{meta.get('end', '')}")
    gaps = manifest["gap_report_gt_7d"].get("usdidr.csv", [])
    print("USDIDR=X gaps>7d:", json.dumps(gaps))
    print("WROTE", HERE / "MANIFEST.json")


if __name__ == "__main__":
    sys.exit(main())
