"""Exact two-sided deflation bar (D-064 §C, 2026-09-29) -- companion to the frozen
deflation_audit.py, which is left untouched as D-062's receipt.

WHY: deflation_audit.py applied the one-sided Bailey & Lopez de Prado approximation
E[max Z] = (1-g)*Phi^-1(1-1/N) + g*Phi^-1(1-1/(N*e)) to |Z|, a TWO-sided statistic.
The max of N |Z| is larger: E[max|Z|] = integral_0^inf 1 - (2*Phi(z)-1)^N dz for N
iid standard normals. At N=252 that is 3.04, not 2.84 -- every bar was ~0.2 lenient.

This script recomputes the bar exactly for each census depth D-062 used plus the
broad-search update (N=266), and re-reads every recorded headline |Z| against it.
Numbers only; no data is loaded.
"""
import json
from pathlib import Path

from scipy import integrate, stats

HERE = Path(__file__).resolve().parent
DEPTHS = {"registered_only (N=8)": 8, "registered+scans (N=50)": 50,
          "+discovery sprint (N=120)": 120, "all disclosed trials (N=252)": 252,
          "+broad search 2026-09-29 (N=266)": 266}


def e_max_abs_z(n: int) -> float:
    return integrate.quad(lambda z: 1.0 - (2.0 * stats.norm.cdf(z) - 1.0) ** n, 0, 40)[0]


def main():
    old = json.loads((HERE / "RESULT_2026-09-28.json").read_text())
    bars = {k: round(e_max_abs_z(n), 4) for k, n in DEPTHS.items()}
    heads = []
    for h in old["headlines"]:
        z = h.get("abs_z")
        if not isinstance(z, (int, float)):
            continue
        heads.append({"stat": h["stat"], "abs_z": z,
                      "survives_at_v1": h.get("survives_at"),
                      "survives_at_v2": [k for k, b in bars.items() if z >= b]})
    extra = [{"stat": "SCREEN-PM-LC-001 primary (broad search S2)", "abs_z": 3.66,
              "survives_at_v2": [k for k, b in bars.items() if 3.66 >= b]}]
    out = {"method": "E[max|Z|] = int_0^inf 1-(2*Phi(z)-1)^N dz (exact, iid two-sided)",
           "supersedes_method": old["method"], "bars_v1": old["deflation_bars"],
           "bars_v2": bars, "headlines": heads + extra}
    (HERE / "RESULT_2026-09-29_v2.json").write_text(json.dumps(out, indent=1))
    for k in DEPTHS:
        print(f"{k:38s} v1={old['deflation_bars'].get(k, '-')!s:>6}  v2={bars[k]}")
    for h in heads + extra:
        lost = set(h.get("survives_at_v1") or []) - set(h["survives_at_v2"])
        print(f"|Z|={h['abs_z']:<5} {h['stat'][:70]:70s} lost at: {sorted(lost) or '-'}")


if __name__ == "__main__":
    main()
