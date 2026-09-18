"""engine/historical/crabel_orb.py — System A: crabel_orb.v1.

PRIMARY SOURCE, as recovered by the 2026-09-03 provenance closure audit:
Toby Crabel, *Day Trading with Short Term Price Patterns and Opening Range
Breakout*, Traders Press (1990) — Chapter 1 and the Glossary (pp. 281-287).
The 1988-89 S&C series is corroborating, not load-bearing: its article bodies
were NOT recovered, only the publisher's records. The previous version of this
module cited the 1988 Part 1 article as Tier A evidence for NR7, which that
article does not carry.

RECOVERED HISTORICAL RULES (verbatim primary text in provenance.historical_rules):
  - NR7: "a daily range that is narrower than the previous six days compared
    individually to the day in question" (Glossary p. 285). "Narrower than"
    is a strict inequality, so equal ranges do not qualify — this settles the
    tie question that was previously carried as unrecovered.
  - "The ORB is effective after ... any day that has a daily range less than the
    previous six days (NR7)" — the setup authorizes the NEXT session; the setup
    day never trades.
  - Opening Range: "the first thirty seconds of trade of each trading day"
    (Glossary p. 285). NOT a free parameter.
  - Stretch: "looking at the previous ten days and averaging ... the differences
    between the open for each day and the closest extreme to the open on each
    day" (Ch. 1).
  - "a buy stop is placed that amount above the high of the opening range and a
    sell stop is placed the same amount below the low of the opening range. The
    first stop that is traded is the position and the other stop is used as a
    protective stop." (Ch. 1)
  - Test protocol: "zero indicates an exit on the close the same day of entry,
    five indicates an exit on the close five days after the entry"; "no stops
    were used on the tests".

ENGINE CONVENTIONS (declared, hashed, never claimed as historical):
  - Session anchor / boundaries:  PRIMARY SOURCE NOT RECOVERED (era/market).
  - Stretch window anchor:        PRIMARY SOURCE NOT RECOVERED ("the previous
                                   ten days" never names its end day).
  - Daily-bar break-even mapping: PRIMARY SOURCE NOT RECOVERED (the recovered
                                   one-hour statement is intraday).
  - Gap-through-stop fill, intra-session OCO ordering: PRIMARY SOURCE NOT RECOVERED.
  - Data basis: stored_raw (no adjustment at load). Costs apply to PnL only.

Excluded by construction: Raschke 1-tick offsets, the Raschke stop-and-reverse,
ATR, True Range, volume filters, 89 SMA, modern trend filters. The config has no
fields through which any of them could enter.
"""
from dataclasses import dataclass

from engine.historical.base import (BreakevenPolicy, ExitConvention,
                                    ProtectiveStopMode, RunResult,
                                    SessionDefinition)
from engine.historical.data import BASIS_STORED_RAW, OpeningRangeUnavailable
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

RULE_ID = "crabel_orb.v1"

_PSR = "PRIMARY SOURCE NOT RECOVERED."

#: Crabel 1990, Glossary p. 285: "OPENING RANGE (OR) — is the first thirty
#: seconds of trade of each trading day." The S&C records for Parts 7 and 8
#: give the contemporaneous band as "the first 30 seconds to 5 minutes".
#: This is a RECOVERED RULE VALUE, not a default to be overridden casually.
RECOVERED_OPENING_RANGE_SECONDS = 30

PROVENANCE = HistoricalProvenance(
    tier=ProvenanceTier.TIER_A_DIRECT,
    citations=(
        "Toby Crabel, 'Day Trading with Short Term Price Patterns and Opening "
        "Range Breakout', Traders Press, Greenville, SC (1990) — Chapter 1 and "
        "Glossary pp. 281-287; primary text recovered 2026-09-03.",
        "Corroborating: Toby Crabel, 'Opening Range Breakout' series, Technical "
        "Analysis of Stocks & Commodities, Parts 1-8, V.6:9 (337-339) through "
        "V.7:7 (208-210), 1988-1989 — publisher records only; article bodies "
        "NOT recovered.",
    ),
    historical_rules=(
        "NR7: 'a daily range that is narrower than the previous six days compared "
        "individually to the day in question' (1990 Glossary p. 285).",
        "'Narrower than' is strict: a range equal to a prior day's range does not "
        "qualify, so ties are excluded by the definition itself.",
        "'The ORB is effective after inside days ... and for that matter after any "
        "day that has a daily range less than the previous six days (NR7) whether "
        "an inside day or not' — the setup authorizes the NEXT session; the setup "
        "day never trades.",
        "Opening Range: 'the first thirty seconds of trade of each trading day' "
        "(1990 Glossary p. 285).",
        "Stretch: 'determined by looking at the previous ten days and averaging "
        "the sum of the differences between the open for each day and the closest "
        "extreme to the open on each day' (1990 Ch. 1).",
        "'a buy stop is placed that amount above the high of the opening range and "
        "a sell stop is placed the same amount below the low of the opening range' "
        "(1990 Ch. 1).",
        "'The first stop that is traded is the position and the other stop is used "
        "as a protective stop' (1990 Ch. 1).",
        "Test protocol exit: 'zero indicates an exit on the close the same day of "
        "entry, five indicates an exit on the close five days after the entry'; "
        "'no stops were used on the tests'. This is the book's RESEARCH protocol, "
        "not its live trade management.",
        "'In general stops should be moved to break even within one hour after "
        "entry' (1990 Ch. 1) — an intraday statement.",
    ),
    discretionary_guidance=(
        "'the objective of these entry techniques is to establish a position for a "
        "two to three day run, but this can be considered only if a substantial "
        "profit is realized by the end of the session' (1990 Ch. 1) — guidance, "
        "not a mechanical rule; deliberately NOT implemented.",
        "'In general the earlier in the session the entry is taken the better the "
        "chances for success' (1990 Ch. 1).",
    ),
    engine_conventions=(
        "Session anchor/boundaries are required engine parameters (source-insufficient).",
        "Stretch window anchor day is an engine convention: the recovered phrase "
        "'the previous ten days' does not name the day the window ends on.",
        "Daily-bar mapping of the intraday break-even statement is an engine convention.",
        "Gap policy and intra-session OCO ambiguity policy are engine conventions.",
        "Costs apply to PnL accounting only; triggers/levels stay raw.",
    ),
    data_basis=BASIS_STORED_RAW,
    entry_mechanism="stop orders at OR High/Low +/- Stretch, OCO, intraday ticks "
                    "used for trigger ordering where available",
    exit_mechanism="protective stop (opposite OR side, break-even per convention) "
                   "under ProtectiveStopMode.ENABLED, or no stop at all under "
                   "NONE_TEST_PROTOCOL; plus the recovered MOC-after-N-sessions "
                   "test-protocol exit (N >= 0)",
    session_definition="required SessionDefinition(session_start[, session_end]); "
                       "boundaries " + _PSR,
    tick_size="not_applicable: System A entries carry no tick-offset mechanics",
    tie_policy="strict inequality ('narrower than'), recovered from the 1990 "
               "Glossary; TiePolicy.MIN_INCLUSIVE is ahistorical legacy parity only",
    gap_policy="required explicit GapPolicy; " + _PSR,
    unrecovered_items=(
        "Historical session boundaries (era/market): " + _PSR,
        "Stretch window anchor day: " + _PSR,
        "Gap-through-stop fill behavior: " + _PSR,
        "Intra-session ordering when both OCO legs trigger on one daily bar: " + _PSR,
        "Deterministic mapping of the intraday break-even statement to daily bars: " + _PSR,
        "Crabel's discretionary (non-test-protocol) trading exit: " + _PSR,
    ),
    witness=UNCONTROLLED_WITNESS,
)


@dataclass(frozen=True)
class CrabelOrbConfig:
    """Source-insufficient values are REQUIRED (no defaults to trip over);
    recovered values carry the recovered default."""
    opening_range_seconds: int           # RECOVERED (30); explicit so a run states it
    session: SessionDefinition           # PRIMARY SOURCE NOT RECOVERED
    gap_policy: GapPolicy                # PRIMARY SOURCE NOT RECOVERED
    ambiguity_policy: AmbiguityPolicy    # PRIMARY SOURCE NOT RECOVERED
    exit_convention: ExitConvention      # MOC-after-N is recovered; N is the choice
    breakeven_move: str                  # BreakevenPolicy.* — daily mapping: PSNR
    protective_stop_mode: str            # ENABLED (Ch.1) vs NONE_TEST_PROTOCOL (tests)
    nr7_tie_policy: TiePolicy = TiePolicy.STRICT_LESS      # RECOVERED default
    stretch_lookback: int = STRETCH_LOOKBACK               # RECOVERED value
    stretch_anchor: StretchAnchor = StretchAnchor.INCLUDE_SETUP_DAY   # convention
    quantity: float = 1.0
    capital: float | None = None         # None → no sizing gate (research mode)

    def __post_init__(self):
        if self.opening_range_seconds <= 0:
            raise ValueError("invalid_configuration: opening_range_seconds must be > 0")
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
            "entry_mechanism": "stop_at_opening_range_high_low_plus_stretch",
            "entry_timing": "next_session_after_setup, stop orders rest from session open",
            "stretch_definition": "mean_of_min_abs_open_high_abs_open_low",
            "stretch_lookback": self.stretch_lookback,
            "stretch_anchor": self.stretch_anchor.value,
            "opening_range_seconds": self.opening_range_seconds,
            "session_definition": (self.session.session_start, self.session.session_end),
            "tick_size": "not_applicable",
            "data_basis": BASIS_STORED_RAW,
            "gap_policy": self.gap_policy.value,
            "ambiguity_policy": self.ambiguity_policy.value,
            "exit_mechanism": self.exit_convention.echo(),
            "protective_stop_mode": self.protective_stop_mode,
            "reversal_policy": "none",
            "breakeven_move": self.breakeven_move,
            "kernel_version": KERNEL_VERSION,
        }


def run(bars, config: CrabelOrbConfig, or_provider, *,
        ticks_by_date: dict[str, list[Tick]] | None = None,
        cost_model=None, log: RejectionLog | None = None) -> RunResult:
    """System A over a RAW-basis bar list.

    `or_provider(date) -> {or_high, or_low, ...} | OpeningRangeUnavailable | None`
    supplies the Opening Range for each execution day. A session whose OR cannot
    be built is rejected — `insufficient_intraday_resolution` when the source
    cannot resolve the recovered thirty-second window, `insufficient_intraday_data`
    otherwise. The engine never fabricates an Opening Range from daily bars and
    never widens the window to fit the data.
    """
    from engine.historical.costs import CostModel
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

        exec_date = bars[t + 1].date
        or_data = or_provider(exec_date)
        if isinstance(or_data, OpeningRangeUnavailable):
            log.record(exec_date, RejectionReason(or_data.reason), **or_data.details)
            return None
        if or_data is None:
            log.record(exec_date, RejectionReason.INSUFFICIENT_INTRADAY_DATA,
                       what="opening range",
                       opening_range_seconds=config.opening_range_seconds,
                       session_start=config.session.session_start)
            return None
        or_high, or_low = float(or_data["or_high"]), float(or_data["or_low"])
        buy_level = or_high + stretch
        sell_level = or_low - stretch

        def protective_for(fill) -> StopOrder:
            # Recovered: "the other stop is used as a protective stop".
            # Long filled at OR High + Stretch → protective SELL at OR Low − Stretch;
            # Short filled at OR Low − Stretch → protective BUY at OR High + Stretch.
            return StopOrder(side=SELL if fill.side == BUY else BUY,
                             level=sell_level if fill.side == BUY else buy_level,
                             kind="protective", order_id=f"{RULE_ID}#prot")

        return EntryPlan(
            orders=[
                StopOrder(side=BUY, level=buy_level, kind="entry",
                          oco_group="orb", order_id=f"{RULE_ID}#buy"),
                StopOrder(side=SELL, level=sell_level, kind="entry",
                          oco_group="orb", order_id=f"{RULE_ID}#sell"),
            ],
            meta={"stretch": stretch, "or_high": or_high, "or_low": or_low,
                  "opening_range_seconds": config.opening_range_seconds,
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
