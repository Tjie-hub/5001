"""Freeze-then-run-once for Rule Cards (D-055).

The three artefacts per candidate:
  CARD.yaml   written before any outcome data; frozen with FREEZE.json
  RESULT.json written once by `run`; its existence makes every later run refuse
  VERDICT.md  generated from RESULT.json; the author adds <= 5 lines of interpretation
plus one appended line in docs/research_programs/EXPERIMENT_LEDGER.jsonl.

FREEZE.json pins three hashes: the card, the rule script, and this framework
(research/rulecard/*.py). Changing any of them after the freeze makes `run` refuse —
the verdict logic lives here, so a framework edit is a goalpost move too.

Rule script contract (CARD.yaml -> signal.script, path relative to the card):
    def load_panel(ctx) -> DataFrame   # ticker,date,open,high,low,close,volume (+ own
                                       # columns, event data joined on availability date)
    def signal(panel) -> Series        # same index as `panel`; row value uses rows
                                       # dated <= that row's date only (LA-1 check)
    def control(panel) -> Series       # optional; only if estimand.control: true
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from research.rulecard import card as cardmod
from research.rulecard import checks, engine, evaluate

REPO_ROOT = Path(__file__).resolve().parents[2]
FRAMEWORK_DIR = Path(__file__).resolve().parent
DEFAULT_LEDGER = REPO_ROOT / "docs" / "research_programs" / "EXPERIMENT_LEDGER.jsonl"
FREEZE, RESULT, VERDICT, STARTED = "FREEZE.json", "RESULT.json", "VERDICT.md", "RUN_STARTED.json"


class RefusedError(RuntimeError):
    pass


def _utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def framework_sha256() -> str:
    h = hashlib.sha256()
    for p in sorted(FRAMEWORK_DIR.glob("*.py")):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def panel_fingerprint(P: pd.DataFrame) -> str:
    cols = engine.REQUIRED_COLS
    return hashlib.sha256(pd.util.hash_pandas_object(
        P[cols].reset_index(drop=True), index=False).values.tobytes()).hexdigest()


def _git_head() -> str | None:
    try:
        head = (REPO_ROOT / ".git" / "HEAD").read_text().strip()
        if head.startswith("ref: "):
            ref = REPO_ROOT / ".git" / head[5:]
            return ref.read_text().strip() if ref.exists() else head[5:]
        return head
    except OSError:
        return None


def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location(f"rulecard_script_{path.stem}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for fn in ("load_panel", "signal"):
        if not callable(getattr(mod, fn, None)):
            raise RefusedError(f"{path.name} must define {fn}()")
    return mod


def _compute(card_path: Path, card: dict, mode: str, with_returns: bool):
    mod = _load_module(cardmod.script_path(card, card_path))
    ctx = {"card": card, "card_dir": card_path.parent, "repo_root": REPO_ROOT, "mode": mode}
    pan = engine.Panel(mod.load_panel(ctx))
    scores = mod.signal(pan.P)
    if not isinstance(scores, pd.Series) or not scores.index.equals(pan.P.index):
        raise RefusedError("signal() must return a Series on the prepared panel's index")
    control = None
    if (card.get("estimand") or {}).get("control"):
        if not callable(getattr(mod, "control", None)):
            raise RefusedError("estimand.control is set but the script defines no control()")
        control = mod.control(pan.P)
    w = card.get("windows") or {}
    cal = engine.calendar(pan.P, w.get("start"), w.get("end"))
    months = engine.run_months(pan, scores, card, cal, control, with_returns=with_returns)
    forms = list(cal["formation"])
    res = [checks.prefix_invariance(pan, mod.signal, scores, forms),
           checks.traded_days_guard(pan, forms),
           checks.predictor_nondegenerate(months, pan, scores, forms, card["portfolio"]["bucketing"]),
           checks.entry_exit_order(months)]
    if with_returns:
        plac = engine.run_months(pan, engine.placebo_scores(pan, scores, cal), card, cal, None)
        res += [checks.forward_returns_nontrivial(months), checks.split_band(months),
                checks.placebo([m["primary"] for m in plac if m.get("valid") and "primary" in m],
                               int(card["estimand"].get("nw_lag", 3)))]
    return pan, months, res


def validate(card_path) -> dict:
    card_path = Path(card_path)
    card = cardmod.load(card_path)
    try:
        table = cardmod.validate(card, strict=True)
        return {"strict": "OK", "power": table}
    except cardmod.CardError as e:
        lenient = None
        try:
            lenient = cardmod.validate(card, strict=False)
        except cardmod.CardError as e2:
            return {"strict": e.problems, "lenient": e2.problems}
        return {"strict": e.problems, "lenient": "OK", "power": lenient}


def dry(card_path) -> dict:
    """Structure only: universe/bucket sizes and the no-return checks. Computes no
    return, so it is not a look at the outcome and needs no freeze (D-053 precedent)."""
    card_path = Path(card_path)
    card = cardmod.load(card_path)
    table = cardmod.validate(card, strict=False)
    pan, months, res = _compute(card_path, card, "dry", with_returns=False)
    valid = [m for m in months if m.get("valid")]
    out = {"card": card["id"], "mode": "dry", "generated_utc": _utc(), "power": table,
           "panel_rows": int(len(pan.P)), "panel_fingerprint": panel_fingerprint(pan.P),
           "non_sessions_dropped": len(pan.non_sessions_dropped),
           "months_total": len(months), "months_valid": len(valid),
           "median_universe": float(pd.Series([m["univ"] for m in valid]).median()) if valid else None,
           "checks": res,
           "skipped": [{"month": m["month"], "reason": m.get("reason")} for m in months if not m.get("valid")]}
    (card_path.parent / f"DRY_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json").write_text(
        json.dumps(out, indent=1, default=str))
    return out


def power(card_path, seeds: int = 10) -> dict:
    """Noise floor of the primary estimand on THIS panel (D-056, R5).

    Buckets are assigned at random — the rule script's signal() is never called — so the
    returns computed here carry no information about the rule. The mean standard
    deviation of the resulting primary series over `seeds` random draws is a LOWER bound
    on the real sigma (a real sort concentrates volatile names in the extreme buckets).
    Copy `sigma_noise_floor` and `months_valid` into the card before freezing."""
    card_path = Path(card_path)
    card = cardmod.load(card_path)
    cardmod.validate(card, strict=False)
    mod = _load_module(cardmod.script_path(card, card_path))
    ctx = {"card": card, "card_dir": card_path.parent, "repo_root": REPO_ROOT, "mode": "power"}
    pan = engine.Panel(mod.load_panel(ctx))
    w = card.get("windows") or {}
    cal = engine.calendar(pan.P, w.get("start"), w.get("end"))
    sds, n_valid, univ = [], 0, []
    for k in range(seeds):
        r = pd.Series(np.random.default_rng(1000 + k).random(len(pan.P)), index=pan.P.index)
        mm = [m for m in engine.run_months(pan, r, card, cal) if m.get("valid") and "primary" in m]
        prim = [m["primary"] for m in mm]
        if len(prim) > 2:
            sds.append(float(np.std(prim, ddof=1)))
        n_valid, univ = len(mm), [m["univ"] for m in mm]
    floor = float(np.mean(sds)) if sds else float("nan")
    probe = dict(card)
    probe["power"] = dict(card["power"], sigma_noise_floor=floor, n_months=n_valid)
    table = cardmod.power_table(probe)
    out = {"card": card["id"], "mode": "power", "generated_utc": _utc(), "seeds": seeds,
           "signal_called": False, "sigma_noise_floor": floor,
           "sigma_noise_floor_range": [min(sds), max(sds)] if sds else None,
           "months_valid": n_valid, "median_universe": float(np.median(univ)) if univ else None,
           "non_sessions_dropped": len(pan.non_sessions_dropped),
           "panel_fingerprint": panel_fingerprint(pan.P),
           "power_with_floor": table}
    (card_path.parent / f"POWER_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json").write_text(
        json.dumps(out, indent=1, default=str))
    return out


def freeze(card_path, owner_approval: str) -> dict:
    card_path = Path(card_path)
    if not owner_approval or not owner_approval.strip():
        raise RefusedError("owner_approval is required (who approved, when, where recorded)")
    fz = card_path.parent / FREEZE
    if fz.exists():
        raise RefusedError(f"{fz} exists: a card is frozen once. A changed rule is a new card id.")
    card = cardmod.load(card_path)
    table = cardmod.validate(card, strict=True)
    sp = cardmod.script_path(card, card_path)
    if not sp.exists():
        raise RefusedError(f"rule script not found: {sp}")
    rec = {"card_id": card["id"], "card_sha256": cardmod.sha256_file(card_path),
           "script": sp.name, "script_sha256": cardmod.sha256_file(sp),
           "framework_sha256": framework_sha256(), "frozen_utc": _utc(),
           "owner_approval": owner_approval.strip(), "power": table}
    fz.write_text(json.dumps(rec, indent=1))
    return rec


def _refuse_unless_frozen_intact(card_path: Path, card: dict) -> dict:
    fz = card_path.parent / FREEZE
    if not fz.exists():
        raise RefusedError("not frozen: run `freeze` first (owner approval required)")
    rec = json.loads(fz.read_text())
    now = {"card_sha256": cardmod.sha256_file(card_path),
           "script_sha256": cardmod.sha256_file(cardmod.script_path(card, card_path)),
           "framework_sha256": framework_sha256()}
    drift = [k for k, v in now.items() if rec.get(k) != v]
    if drift:
        raise RefusedError(f"changed since freeze: {drift} — a changed rule is a new card id")
    return rec


def run(card_path, ledger_path=None, resume_after_crash: bool = False) -> dict:
    card_path = Path(card_path)
    d = card_path.parent
    if (d / RESULT).exists():
        raise RefusedError(f"{d / RESULT} exists: this card has been run. Refusing to re-run.")
    card = cardmod.load(card_path)
    cardmod.validate(card, strict=True)
    frz = _refuse_unless_frozen_intact(card_path, card)
    started = d / STARTED
    if started.exists() and not resume_after_crash:
        raise RefusedError(f"{started} exists without RESULT.json: a previous run did not finish. "
                           "Re-run only with resume_after_crash=True; the resume is recorded.")
    prior_start = json.loads(started.read_text()) if started.exists() else None
    started.write_text(json.dumps({"started_utc": _utc(), "card_sha256": frz["card_sha256"]}))

    pan, months, res = _compute(card_path, card, "real", with_returns=True)
    summ = evaluate.summarize(months, card)
    verd = evaluate.verdict(card, summ, res)
    out = {"card": card["id"], "title": card["title"], "tier": card["tier"],
           "family_mapping": card["family_mapping"], "run_utc": _utc(), "freeze": frz,
           "resumed_after_crash": prior_start, "git_head": _git_head(),
           "panel": {"rows": int(len(pan.P)), "fingerprint": panel_fingerprint(pan.P),
                     "non_sessions_dropped": pan.non_sessions_dropped,
                     "first_date": str(pan.P["date"].min().date()),
                     "last_date": str(pan.P["date"].max().date())},
           "checks": res, "summary": summ, "verdict": verd, "months": months}
    tmp = d / (RESULT + ".tmp")
    tmp.write_text(json.dumps(out, indent=1, default=str))
    os.replace(tmp, d / RESULT)
    (d / VERDICT).write_text(render_verdict(out, card), encoding="utf-8")
    _append_ledger(Path(ledger_path) if ledger_path else DEFAULT_LEDGER, out, card, card_path)
    started.unlink(missing_ok=True)
    return out


def _append_ledger(path: Path, out: dict, card: dict, card_path: Path):
    try:
        rel = card_path.parent.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        rel = card_path.parent.as_posix()
    rec = {"record_type": "rule_card_run", "canonical_id": card["id"], "title": card["title"],
           "tier": card["tier"], "family": card["family_mapping"],
           "registration": {"status": "FROZEN", "card_sha256_16": out["freeze"]["card_sha256"][:16],
                            "frozen_utc": out["freeze"]["frozen_utc"],
                            "owner_approval": out["freeze"]["owner_approval"]},
           "execution": {"run_utc": out["run_utc"],
                         "script_sha256_16": out["freeze"]["script_sha256"][:16],
                         "framework_sha256_16": out["freeze"]["framework_sha256"][:16],
                         "panel_fingerprint_16": out["panel"]["fingerprint"][:16]},
           "result_classification": out["verdict"]["verdict"],
           "links": [f"{rel}/{RESULT}", f"{rel}/{VERDICT}"], "authority": "D-055"}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def _fmt(x):
    if isinstance(x, float):
        return f"{x:+.3f}"
    if isinstance(x, dict):
        return ", ".join(f"{k} {_fmt(v)}" for k, v in x.items())
    return str(x)


def render_verdict(out: dict, card: dict) -> str:
    v, W = out["verdict"], out["summary"]["windows"]
    fz = out["freeze"]
    L = [f"# {out['card']} — VERDICT: **{v['verdict']}**", "",
         f"**{out['title']}** · tier {out['tier']} · family {out['family_mapping']}",
         f"**Run:** {out['run_utc']} · git `{(out['git_head'] or '?')[:10]}` · "
         f"card `{fz['card_sha256'][:12]}` · script `{fz['script_sha256'][:12]}` · "
         f"framework `{fz['framework_sha256'][:12]}` · panel `{out['panel']['fingerprint'][:12]}` "
         f"({out['panel']['first_date']} → {out['panel']['last_date']})",
         f"**Frozen:** {fz['frozen_utc']} · owner approval: {fz['owner_approval']}", ""]
    if v["verdict"] == "INVALID":
        L += ["## Invalid — implementation/data, not a hypothesis result", ""]
        L += [f"- {r}" for r in v["reasons"]]
    else:
        L += ["## Criteria (computed by research/rulecard/evaluate.py, not by the script)", "",
              "| criterion | required | observed | pass |", "|---|---|---|---|"]
        L += [f"| {c['criterion']} | {c['required']} | {_fmt(c['observed'])} | "
              f"{'yes' if c['pass'] else '**no**'} |" for c in v["criteria"]]
        L += ["", f"Posterior P(null | data) ≥ {v['posterior_p_null_lower_bound']:.3f} "
              f"at prior P(true) = {v['prior_true_assumed']} (minimum Bayes factor)."]
    L += ["", "## Windows (%/month; NW t)", "",
          "| window | n | primary | t | deployment | t | uplift net of cost |", "|---|---|---|---|---|---|---|"]
    for k, w in W.items():
        if w.get("n"):
            L.append(f"| {k} | {w['n']} | {w['primary_mean']:+.3f} | {w['primary_t']:+.2f} | "
                     f"{w['deployment_mean']:+.3f} | {w['deployment_t']:+.2f} | {w['uplift_net_mean']:+.3f} |")
    L += ["", "Per year (primary): " + " · ".join(
        f"{y} {p['primary_mean']:+.2f} (n{p['n']})" for y, p in out["summary"]["per_year"].items())]
    L += ["", "## Mandatory checks", "", "| code | check | status |", "|---|---|---|"]
    L += [f"| {c['code']} | {c['check']} | {c['status']} |" for c in out["checks"]]
    L += ["", "## Registry actions (manual)", "",
          "- Append the result row to `docs/research_programs/HYPOTHESIS_REGISTRY.md`.",
          "- FAIL / FAIL_NOT_MONOTONE: append to `FAILURE_REGISTRY.md` (F2 unless the author "
          "defends another mode). INVALID is not a failure: fix, then a new card id.",
          "", "## Interpretation (author, at most 5 lines)", "", "_to be written_", ""]
    return "\n".join(L)
