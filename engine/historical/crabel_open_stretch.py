"""engine/historical/crabel_open_stretch.py — System A2: crabel_open_stretch.v1.

TIER B — A DECLARED SYNTHESIS, NOT A RECOVERED RULE.

The 2026-09-03 provenance closure audit recovered the full primary text of
Crabel (1990) and found that it does NOT state "Open ± Stretch". What it states
is that the open-anchored and the Stretch-anchored constructions are two
DIFFERENT things, and that the book's tests use the former with a constant value:

    "Opening range breakout is defined as a trade taken at a predetermined
     amount off the open. It should be noted that when I introduce this trading
     concept in Chapter One I use a mathematical technique, called the stretch,
     to determine the point of entry. In later testing you will notice that I
     use a constant value off the open rather than the stretch point.
     Experience has shown this to be a better method."  (1990, Introduction)

The book's own tests are accordingly run at fixed tick distances from the open
("an entry 16 tics above the open ... 8 tics below the open"), never at
Open ± Stretch. Pairing the open anchor with the Stretch amount is therefore
OUR synthesis of two separate primary constructions. It is declared in
provenance.adaptations and the tier stays B; it is NOT promoted, and the stale
claim that the 1990 text could not be recovered has been removed.

ISOLATION MANDATE: this is a COMPLETELY SEPARATE rule identity from
crabel_orb.v1. Configuration cannot transform one into the other: distinct
rule_ids, distinct config classes, distinct entry mechanisms, and the identity
hash covers the entry mechanism. No Opening Range is constructed here — System
A2 never touches OR data.

ENGINE CONVENTIONS (declared, hashed, never claimed as historical):
  - Session boundaries, Stretch window anchor, daily-bar break-even mapping,
    gap policy, intra-session OCO ambiguity policy: PRIMARY SOURCE NOT RECOVERED.
"""
from dataclasses import dataclass

from engine.historical.base import (BreakevenPolicy, ExitConvention,
                                    ProtectiveStopMode, RunResult,
                                    SessionDefinition)
from engine.historical.costs import CostModel
from engine.historical.data import BASIS_STORED_RAW
from engine.historical.kernel import (BUY, AmbiguityPolicy, GapPolicy, SELL,
                                      StopOrder, Tick)
from engine.historical.nr7 import (NR7_LOOKBACK, TiePolicy, evaluate_nr7,
                                   is_historical_tie_policy, nr7_range)
from engine.historical.provenance import (UNCONTROLLED_WITNESS,
                                          HistoricalProvenance, ProvenanceTier,
                                          register_historical_spec)
from engine.historical.runner import EntryPlan, run_bracket_system
from engine.historical.stretch import (STRETCH_LOOKBACK, StretchAnchor,
                                       stretch_at_setup)
from engine.historical.telemetry import RejectionLog, RejectionReason
from engine.rule_identity import historical_rule_id

RULE_ID = "crabel_open_stretch.v1"

_PSR = "PRIMARY SOURCE NOT RECOVERED."

PROVENANCE = HistoricalProvenance(
    tier=ProvenanceTier.TIER_B_CONTEMPORARY_SECONDARY,
    citations=(
        "Toby Crabel, 'Day Trading with Short Term Price Patterns and Opening "
        "Range Breakout', Traders Press, Greenville, SC (1990) — Introduction, "
        "Chapter 1 and Glossary; primary text recovered 2026-09-03. The text "
        "distinguishes the open anchor from the Stretch amount and does not "
        "state Open +/- Stretch.",
        "Corroborating: Toby Crabel, 'Opening Range Breakout Part 5', Technical "
        "Analysis of Stocks & Commodities V.7:4 (119-120), 1989 — publisher "
        "record describes 'a trade taken at a predetermined amount above or "
        "below the opening price'; article body NOT recovered.",
    ),
    historical_rules=(
        "NR7 setup identical to System A: 'narrower than the previous six days "
        "compared individually to the day in question' (1990 Glossary p. 285); "
        "the setup day never trades.",
        "Stretch identical to System A: 'the previous ten days ... averaging ... "
        "the differences between the open for each day and the closest extreme "
        "to the open on each day' (1990 Ch. 1).",
        "An open-anchored entry exists in the primary text: 'a trade taken at a "
        "predetermined amount off the open' (1990 Introduction).",
        "The book's tests anchor on the open with a CONSTANT value, not the "
        "Stretch: 'I use a constant value off the open rather than the stretch "
        "point' (1990 Introduction).",
    ),
    adaptations=(
        "Buy = Open + Stretch; Sell = Open - Stretch. NO primary source states "
        "this pairing: the recovered text anchors the Stretch on the opening "
        "range and anchors the open on a constant tick value, and presents the "
        "two as alternatives. This system is a synthesis of both and is not a "
        "recovered Crabel rule.",
        "The opposite entry level is used as the protective stop, by analogy "
        "with the Chapter 1 opening-range construction; the primary text does "
        "not state a protective stop for an open-anchored entry.",
    ),
    discretionary_guidance=(
        "'the objective of these entry techniques is to establish a position for "
        "a two to three day run' (1990 Ch. 1) — guidance, not a mechanical rule.",
    ),
    engine_conventions=(
        "Session anchor/boundaries are required engine parameters.",
        "Stretch window anchor day is an engine convention ('the previous ten "
        "days' does not name its end day).",
        "Daily-bar break-even mapping is an engine convention.",
        "Gap policy and intra-session OCO ambiguity policy are engine conventions.",
        "Costs apply to PnL accounting only; triggers/levels stay raw.",
    ),
    data_basis=BASIS_STORED_RAW,
    entry_mechanism="stop orders at execution-session Open +/- Stretch (SYNTHESIS), "
                    "OCO, intraday ticks used for trigger ordering where available",
    exit_mechanism="protective stop at the opposite Open +/- Stretch level under "
                   "ProtectiveStopMode.ENABLED, or no stop under NONE_TEST_PROTOCOL; "
                   "plus the recovered MOC-after-N-sessions test-protocol exit (N >= 0)",
    session_definition="required SessionDefinition(session_start[, session_end]); "
                       "boundaries " + _PSR,
    tick_size="not_applicable: System A2 entries carry no tick-offset mechanics",
    tie_policy="strict inequality ('narrower than'), recovered from the 1990 "
               "Glossary; TiePolicy.MIN_INCLUSIVE is ahistorical legacy parity only",
    gap_policy="required explicit GapPolicy; " + _PSR,
    unrecovered_items=(
        "Primary support for the Open +/- Stretch pairing itself: " + _PSR,
        "Historical session boundaries (era/market): " + _PSR,
        "Stretch window anchor day: " + _PSR,
        "Gap-through-stop fill behavior: " + _PSR,
        "Deterministic mapping of the intraday break-even statement to daily bars: " + _PSR,
        "Crabel's discretionary (non-test-protocol) trading exit: " + _PSR,
    ),
    witness=UNCONTROLLED_WITNESS,
)


@dataclass(frozen=True)
class CrabelOpenStretchConfig:
    """No Opening Range field exists here by construction — A2 never touches
    OR data, so no configuration can drift A2 toward A."""
    session: SessionDefinition            # PRIMARY SOURCE NOT RECOVERED
    gap_policy: GapPolicy                 # PRIMARY SOURCE NOT RECOVERED
    ambiguity_policy: AmbiguityPolicy     # PRIMARY SOURCE NOT RECOVERED
    exit_convention: ExitConvention       # MOC-after-N is recovered; N is the choice
    breakeven_move: str                   # BreakevenPolicy.* — daily mapping: PSNR
    protective_stop_mode: str             # ENABLED vs NONE_TEST_PROTOCOL
    nr7_tie_policy: TiePolicy = TiePolicy.STRICT_LESS      # RECOVERED default
    stretch_lookback: int = STRETCH_LOOKBACK               # RECOVERED value
    stretch_anchor: StretchAnchor = StretchAnchor.INCLUDE_SETUP_DAY   # convention
    quantity: float = 1.0
    capital: float | None = None

    def __post_init__(self):
        if self.breakeven_move not in (BreakevenPolicy.NONE, BreakevenPolicy.AFTER_ENTRY_SESSION):
            raise ValueError(f"invalid_configuration: breakeven_move {self.breakeven_move!r}")
        if self.protective_stop_mode not in (ProtectiveStopMode.ENABLED,
                                             ProtectiveStopMode.NONE_TEST_PROTOCOL):
            raise ValueError("invalid_configuration: protective_stop_mode "
                             f"{self.protective_stop_mode!r}")
        if self.stretch_lookback < 1:
            raise ValueError("invalid_configuration: stretch_lookback must be >= 1")

    @property
    def tie_policy_is_historical(self) -> bool:
        return is_historical_tie_policy(self.nr7_tie_policy)

    def identity_material(self) -> dict:
        from engine.historical.kernel import KERNEL_VERSION
        return {
            "rule_id": RULE_ID,
            "setup_definition": "nr7_high_minus_low",
            "setup_lookback": NR7_LOOKBACK,
            "setup_tie_policy": self.nr7_tie_policy.value,
            "setup_tie_policy_is_historical": self.tie_policy_is_historical,
            "entry_mechanism": "stop_at_session_open_plus_minus_stretch",
            "entry_timing": "next_session_after_setup, stop orders rest from session open",
            "stretch_definition": "mean_of_min_abs_open_high_abs_open_low",
            "stretch_lookback": self.stretch_lookback,
            "stretch_anchor": self.stretch_anchor.value,
            "session_definition": (self.session.session_start, self.session.session_end),
            "tick_size": "not_applicable",
            "data_basis": BASIS_STORED_RAW,
            "gap_policy": self.gap_policy.value,
            "ambiguity_policy": self.ambiguity_policy.value,
            "exit_mechanism": self.exit_convention.echo(),
            "protective_stop_mode": self.protective_stop_mode,
            "reversal_policy": "none",
            "breakeven_move": self.breakeven_move,
            "provenance_tier": ProvenanceTier.TIER_B_CONTEMPORARY_SECONDARY.value,
            "kernel_version": KERNEL_VERSION,
        }


def run(bars, config: CrabelOpenStretchConfig, *,
        ticks_by_date: dict[str, list[Tick]] | None = None,
        cost_model=None, log: RejectionLog | None = None) -> RunResult:
    """System A2 over a RAW-basis bar list. No Opening Range is constructed."""
    cost_model = cost_model or CostModel.zero()
    log = log or RejectionLog()
    identity = historical_rule_id(config.identity_material())
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    opens = [b.open for b in bars]
    ranges = [nr7_range(h, l) for h, l in zip(highs, lows)]

    def planner(t: int) -> EntryPlan | None:
        setup_date = bars[t].date
        try:
            verdict = evaluate_nr7(ranges, t, config.nr7_tie_policy)
        except ValueError:
            log.record(setup_date, RejectionReason.INSUFFICIENT_HISTORY,
                       what="nr7 window", setup_t=t)
            return None
        if verdict == "tie_rejected":
            log.record(setup_date, RejectionReason.TIE_REJECTED,
                       range=ranges[t], rule=RULE_ID)
            return None
        if verdict != "ok":
            log.record(setup_date, RejectionReason.NR7_FALSE,
                       range=ranges[t], rule=RULE_ID)
            return None
        try:
            stretch = stretch_at_setup(opens, highs, lows, t,
                                       config.stretch_lookback, config.stretch_anchor)
        except ValueError:
            log.record(setup_date, RejectionReason.INSUFFICIENT_HISTORY,
                       what="stretch window", setup_t=t,
                       stretch_anchor=config.stretch_anchor.value)
            return None

        exec_bar = bars[t + 1]
        buy_level = exec_bar.open + stretch
        sell_level = exec_bar.open - stretch

        def protective_for(fill) -> StopOrder:
            return StopOrder(side=SELL if fill.side == BUY else BUY,
                             level=sell_level if fill.side == BUY else buy_level,
                             kind="protective", order_id=f"{RULE_ID}#prot")

        return EntryPlan(
            orders=[
                StopOrder(side=BUY, level=buy_level, kind="entry",
                          oco_group="open_stretch", order_id=f"{RULE_ID}#buy"),
                StopOrder(side=SELL, level=sell_level, kind="entry",
                          oco_group="open_stretch", order_id=f"{RULE_ID}#sell"),
            ],
            meta={"stretch": stretch, "open_anchor": exec_bar.open,
                  "stretch_anchor": config.stretch_anchor.value,
                  "setup_date": setup_date},
            protective_for=protective_for,
        )

    return run_bracket_system(
        rule_id=RULE_ID, bars=bars, exit_convention=config.exit_convention,
        tie_policy=config.nr7_tie_policy, gap_policy=config.gap_policy,
        ambiguity_policy=config.ambiguity_policy,
        breakeven_move=config.breakeven_move, cost_model=cost_model,
        quantity=config.quantity, capital=config.capital,
        signal_basis=BASIS_STORED_RAW, identity=identity,
        config_echo=config.identity_material(),
        entry_planner=planner,
        protective_stop_mode=config.protective_stop_mode,
        ticks_by_date=ticks_by_date or {}, log=log)


def spec():
    from engine.strategy_specs import StrategySpec
    return StrategySpec(name=RULE_ID, family="historical", live_checker=False,
                        provenance=PROVENANCE)


register_historical_spec(spec())
