"""Rule Card loading and validation (D-055, RULE_FIRST_PROTOCOL_2026-09-24 §2-§3).

A card is admissible only when every field the protocol requires is filled.
Two strictness levels:
  - lenient (dry runs): structure and power only; PENDING owner fields allowed.
  - strict (freeze, real run): no PENDING anywhere; Tier-R literature and
    external prior present; power admissible.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from research.rulecard.stats import needed_effect

PENDING = "PENDING"

# Tier hurdles — a card may raise its own hurdle, never lower it (R3).
TIER_MIN_T = {"R": 2.0, "N": 3.0}
TIER_N_MIN_DSR = 0.95
ADMISSIBLE_LIT_TAGS = {"V", "V2"}          # [M] (memory) never counts toward a prior
BUCKETINGS = {"decile": 10, "quintile": 5, "flag": 2}
PRIMARY_KINDS = {"top_minus_bottom", "bucket_minus_rest"}
FINGERPRINTS = {"adv_tercile", "price_tercile", "market_state"}
SIGNS = {"negative", "positive"}


class CardError(ValueError):
    """Raised with every problem listed at once (same posture as config.validate_config)."""

    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__("Rule Card not admissible:\n  - " + "\n  - ".join(self.problems))


def sha256_file(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path) -> dict:
    card = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(card, dict):
        raise CardError([f"{path}: not a YAML mapping"])
    return card


def _get(card, dotted):
    cur = card
    for k in dotted.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def _blank(v) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "") or v == [] or v == {}


REQUIRED = [
    "id", "title", "tier", "tier_justification",
    "mechanism.statement", "mechanism.loser", "mechanism.barrier", "mechanism.side",
    "literature", "signal.script", "signal.description", "signal.parameter_source",
    "signal.formation", "universe.preset",
    "portfolio.bucketing", "portfolio.use", "portfolio.use_end",
    "estimand.primary_kind", "estimand.predicted_sign",
    "deployment.predicted_sign",
    "power.sigma_planning", "power.sigma_source", "power.literature_effect",
    "power.haircut", "power.n_months",
    "fingerprints", "windows.split", "costs.round_trip_pct",
    "survivorship_direction", "kill_rule", "family_mapping",
]
STRICT_ONLY = ["external_prior.series", "external_prior.sign",
               "power.sigma_noise_floor"]          # measured by `cli power` before freeze (D-056)


def hurdle_t(card) -> float:
    tier = card.get("tier")
    floor = TIER_MIN_T.get(tier, 3.0)
    declared = _get(card, "hurdle.t_min")
    return float(max(floor, declared)) if declared is not None else float(floor)


def power_table(card) -> dict:
    """R5: plan on literature effect x haircut; admissible iff it reaches 80% power.

    sigma used = max(literature sigma, noise floor measured on THIS panel by `power`):
    a published sigma comes from the paper's universe (often every listed stock, ~40
    names per decile); ours has ~12-15 per decile. The noise floor is measured with
    random buckets, so it carries no information about the signal (D-056)."""
    sig_lit = float(_get(card, "power.sigma_planning"))
    floor = _get(card, "power.sigma_noise_floor")
    sigma = max(sig_lit, float(floor)) if floor not in (None, "") else sig_lit
    eff = abs(float(_get(card, "power.literature_effect")))
    haircut = float(_get(card, "power.haircut"))
    n = int(_get(card, "power.n_months"))
    t_star = hurdle_t(card)
    need = needed_effect(t_star, sigma, n)
    plan = eff * haircut
    return {"sigma": sigma, "sigma_literature": sig_lit,
            "sigma_noise_floor": None if floor in (None, "") else float(floor),
            "literature_effect": eff, "haircut": haircut,
            "planning_effect": plan, "n_months": n, "t_star": t_star,
            "needed_effect_80pct": need, "admissible": bool(plan >= need - 1e-12)}


def validate(card, strict: bool = False) -> dict:
    """Return the derived power table; raise CardError listing every problem."""
    p = []
    disp = card.get("disposition")
    if strict and disp:
        # a closed card (e.g. "underpowered, not tested") can never be frozen: re-opening
        # the same rule after its disposition is a new card id with the history disclosed
        p.append(f"card is closed ({disp.get('status') if isinstance(disp, dict) else disp}); "
                 "a changed or re-opened rule is a new card id")
    for f in REQUIRED + (STRICT_ONLY if strict else []):
        v = _get(card, f)
        if _blank(v):
            p.append(f"missing: {f}")
        elif strict and isinstance(v, str) and PENDING in v:
            p.append(f"still PENDING: {f}")
    if strict:
        # walk every string leaf: nothing may be left PENDING at freeze
        def walk(x, path=""):
            if isinstance(x, dict):
                for k, v in x.items():
                    walk(v, f"{path}.{k}" if path else k)
            elif isinstance(x, list):
                for i, v in enumerate(x):
                    walk(v, f"{path}[{i}]")
            elif isinstance(x, str) and PENDING in x and not any(path == f for f in REQUIRED + STRICT_ONLY):
                p.append(f"still PENDING: {path}")
        walk(card)

    tier = card.get("tier")
    if tier not in TIER_MIN_T:
        p.append("tier must be R or N")
    declared = _get(card, "hurdle.t_min")
    if declared is not None and tier in TIER_MIN_T and float(declared) < TIER_MIN_T[tier]:
        p.append(f"hurdle.t_min {declared} is below the tier-{tier} floor {TIER_MIN_T[tier]}")
    if _get(card, "portfolio.bucketing") not in BUCKETINGS:
        p.append(f"portfolio.bucketing must be one of {sorted(BUCKETINGS)}")
    if _get(card, "portfolio.use") not in {"avoid", "long"}:
        p.append("portfolio.use must be avoid or long")
    if _get(card, "portfolio.use_end") not in {"high", "low"}:
        p.append("portfolio.use_end must be high or low")
    if _get(card, "estimand.primary_kind") not in PRIMARY_KINDS:
        p.append(f"estimand.primary_kind must be one of {sorted(PRIMARY_KINDS)}")
    for f in ("estimand.predicted_sign", "deployment.predicted_sign"):
        if _get(card, f) not in SIGNS:
            p.append(f"{f} must be negative or positive")
    if _get(card, "portfolio.bucketing") == "flag" and _get(card, "estimand.primary_kind") == "top_minus_bottom":
        p.append("flag bucketing has no top/bottom — use bucket_minus_rest")
    if _get(card, "signal.formation") != "month_end":
        p.append("signal.formation: only month_end is implemented (event-time rules need a v2 engine)")
    if _get(card, "universe.preset") != "liquid_idx_v1":
        p.append("universe.preset: only liquid_idx_v1 is implemented")

    if _get(card, "monotonicity.grid") not in (None, "quintile", "native"):
        p.append("monotonicity.grid must be quintile or native")
    if _get(card, "monotonicity.shape") not in (None, "full", "tail"):
        p.append("monotonicity.shape must be full or tail")
    if _get(card, "monotonicity.shape") == "tail" and _blank(_get(card, "monotonicity.shape_justification")):
        p.append("monotonicity.shape tail needs shape_justification (why the mechanism acts in the tail)")

    fps = card.get("fingerprints") or []
    for i, fp in enumerate(fps if isinstance(fps, list) else []):
        if not isinstance(fp, dict) or fp.get("name") not in FINGERPRINTS:
            p.append(f"fingerprints[{i}].name must be one of {sorted(FINGERPRINTS)}")
        elif fp.get("predicted_sign") not in SIGNS:
            p.append(f"fingerprints[{i}].predicted_sign must be negative or positive")

    lit = card.get("literature") or []
    if tier == "R":
        good = [x for x in lit if isinstance(x, dict) and x.get("tag") in ADMISSIBLE_LIT_TAGS]
        if len(good) < 2:
            p.append("tier R needs >= 2 literature anchors tagged V or V2 ([M] does not count)")
    if tier == "N" and strict:
        if _blank(_get(card, "trials.n_trials")):
            p.append("tier N needs trials.n_trials (every variant ever computed on this data)")

    table = None
    try:
        table = power_table(card)
        # Underpowered blocks freeze/run, not a structural dry run: a dry run may be what
        # measures event density before the power table can be finalised (C2 issuance).
        if strict and not table["admissible"]:
            p.append(f"underpowered: planning effect {table['planning_effect']:.3f} < "
                     f"{table['needed_effect_80pct']:.3f} needed (record 'underpowered, not tested')")
    except (TypeError, ValueError) as e:
        p.append(f"power table not computable: {e}")

    if p:
        raise CardError(p)
    return table


def script_path(card, card_path) -> Path:
    return (Path(card_path).parent / _get(card, "signal.script")).resolve()
