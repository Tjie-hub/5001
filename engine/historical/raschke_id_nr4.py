"""engine/historical/raschke_id_nr4.py — the genuine Raschke system: raschke_id_nr4.v1.

PRIMARY SOURCE: Linda Bradford Raschke & Larry Connors, *Street Smarts: High
Probability Short-Term Trading Strategies*, M. Evans & Co. (1995) —
**Chapter 19, "Range Contraction"** (p. 109) and **Chapter 20, "Historical
Volatility Meets Toby Crabel"** (p. 115).

WHY THIS MODULE EXISTS
----------------------
The 2026-09-03 provenance closure audit recovered the full text of Street Smarts
and established two things that invalidated the previous `raschke_nr7.v1`
provenance:

  1. Chapter 16 is "News". It contains no setup at all. The rule set is in
     Chapters 19 and 20.
  2. The numbered rule set is stated for **ID/NR4**, and only for ID/NR4. NR7
     appears in Street Smarts exactly once, as a bias filter Raschke attributes
     to Crabel: "One of the simplest concepts which I use regularly is Toby's
     NR7 ... I automatically use this as a filter to switch to a breakout mode
     the day following an NR7." That is not an entry/stop/exit rule set.

So this module implements what Street Smarts actually states. The NR7 variant
survives as `raschke_nr7.v1` under ProvenanceTier.TIER_T_TRANSFER — a declared
transfer, never Tier A.

RECOVERED RULES (Ch. 19, verbatim, rules 1-5):
    1. Identify an ID/NR4.
    2. The next day only, place a buy-stop one tick above and a sell-stop one
       tick below the ID/NR4 bar.
    3. On entry day only, if we are filled on the buy side, enter an additional
       sell-stop one tick below the ID/NR4 bar. This means that if the trade is
       a loser, not only will we get stopped out with a loss, we will reverse
       and go short. (The rule is reversed if initially filled on the short side.)
    4. Trail a stop to lock in accrued profits.
    5. If the position is not profitable within two days and you have not been
       stopped out, exit the trade MOC (market on close.)

Ch. 20 adds the reversal order's lifetime: "This additional sell-stop is done on
the entry day only, and expires on the close of this day."

WHAT IS NOT IMPLEMENTED, DELIBERATELY: rule 4. "Trail a stop" names no
mechanism, so any trail would be invented. PRIMARY SOURCE NOT RECOVERED.

MANDATED EXCLUSIONS: no Crabel Stretch, no Opening Range, no ATR, no True Range,
no 89 SMA, no volume filters, no modern trend filters. The config has no fields
through which any of them could enter, and the entry mechanism never reads
Stretch or OR data.
"""
from dataclasses import dataclass

from engine.historical.base import (ExitConvention, ProtectiveStopMode,
                                    ReversalPolicy, RunResult, SessionDefinition)
from engine.historical.costs import CostModel
from engine.historical.data import BASIS_STORED_RAW
from engine.historical.id_nr4 import evaluate_id_nr4
from engine.historical.kernel import (BUY, AmbiguityPolicy, GapPolicy, SELL,
                                      StopOrder, Tick)
from engine.historical.nr7 import (NR4_LOOKBACK, TiePolicy,
                                   is_historical_tie_policy, nr7_range)
from engine.historical.provenance import (UNCONTROLLED_WITNESS,
                                          HistoricalProvenance, ProvenanceTier,
                                          register_historical_spec)
from engine.historical.runner import EntryPlan, run_bracket_system
from engine.historical.telemetry import RejectionLog, RejectionReason
from engine.rule_identity import historical_rule_id

RULE_ID = "raschke_id_nr4.v1"

_PSR = "PRIMARY SOURCE NOT RECOVERED."

#: Street Smarts Ch. 19 rule 5 — "not profitable within two days".
RECOVERED_PROFIT_CHECK_SESSIONS = 2

PROVENANCE = HistoricalProvenance(
    tier=ProvenanceTier.TIER_A_DIRECT,
    citations=(
        "Linda Bradford Raschke & Larry Connors, 'Street Smarts: High "
        "Probability Short-Term Trading Strategies', M. Evans & Co. (1995), "
        "Chapter 19 'Range Contraction' (p. 109) — rules 1-5; primary text "
        "recovered 2026-09-03.",
        "Same work, Chapter 20 'Historical Volatility Meets Toby Crabel' "
        "(p. 115) — the reversal order's entry-day-only lifetime.",
    ),
    historical_rules=(
        "'An NR4 is a trading day with the narrowest daily range of the last four "
        "days. An inside day has a higher low than the previous day's low and a "
        "lower high than the previous day's high. Combining the two conditions "
        "sets up an ID/NR4 day.' (Ch. 19)",
        "Rule 2: 'The next day only, place a buy-stop one tick above and a "
        "sell-stop one tick below the ID/NR4 bar.'",
        "Rule 3: 'On entry day only, if we are filled on the buy side, enter an "
        "additional sell-stop one tick below the ID/NR4 bar ... not only will we "
        "get stopped out with a loss, we will reverse and go short.'",
        "Ch. 20 rule 4: 'This additional sell-stop is done on the entry day only, "
        "and expires on the close of this day.'",
        "Rule 5: 'If the position is not profitable within two days and you have "
        "not been stopped out, exit the trade MOC (market on close.)'",
        "One tick means the instrument's minimum price increment; the offset "
        "itself is the historical rule.",
    ),
    discretionary_guidance=(
        "Rule 4: 'Trail a stop to lock in accrued profits' — no mechanism is "
        "specified, so no trail is implemented.",
        "Ch. 20: 'I will stay in the position as long as it continues to move in "
        "my favor. Usually though, I am out within one to four days.'",
    ),
    engine_conventions=(
        "Day counting for rule 5 (the entry session counts as session 1) is an "
        "engine convention; the text says 'within two days' without naming the "
        "anchor.",
        "The reversed leg rests no protective stop of its own: the text states "
        "none, and inventing one would be an ahistorical addition.",
        "Tie policy for the NR4 comparison follows the recovered strict "
        "inequality; MIN_INCLUSIVE is ahistorical legacy parity only.",
        "Session boundaries, gap policy and intra-session OCO ambiguity policy "
        "are engine conventions.",
        "The numeric tick size is an exchange/instrument parameter, not a "
        "historical unknown.",
        "Costs apply to PnL accounting only; triggers/levels stay raw.",
    ),
    adaptations=(),
    data_basis=BASIS_STORED_RAW,
    entry_mechanism="stop orders at setup-day High + 1 tick / Low - 1 tick, OCO, "
                    "intraday ticks used for trigger ordering where available",
    exit_mechanism="protective stop one tick beyond the opposite setup-day extreme, "
                   "which on the entry day reverses the position (Ch. 19 rule 3); "
                   "plus the recovered two-day unprofitable MOC time stop (rule 5)",
    session_definition="required SessionDefinition(session_start[, session_end]); "
                       "historical session boundaries " + _PSR,
    tick_size="one tick = the instrument's minimum price increment; an "
              "exchange/instrument parameter, not a source gap",
    tie_policy="strict inequality ('narrowest daily range of the last four days'); "
               "TiePolicy.MIN_INCLUSIVE is ahistorical legacy parity only",
    gap_policy="required explicit GapPolicy; " + _PSR,
    unrecovered_items=(
        "Trailing-stop mechanism (Ch. 19 rule 4): " + _PSR,
        "Protective stop for the reversed leg: " + _PSR,
        "Historical session boundaries (era/market): " + _PSR,
        "Gap-through-stop fill behavior: " + _PSR,
        "Intra-session ordering when both OCO legs trigger on one daily bar: " + _PSR,
    ),
    witness=UNCONTROLLED_WITNESS,
)


@dataclass(frozen=True)
class RaschkeIdNr4Config:
    tick_size: float                      # instrument minimum price increment
    session: SessionDefinition            # PRIMARY SOURCE NOT RECOVERED
    gap_policy: GapPolicy                 # PRIMARY SOURCE NOT RECOVERED
    ambiguity_policy: AmbiguityPolicy     # PRIMARY SOURCE NOT RECOVERED
    exit_convention: ExitConvention       # rule 5 = MOC_IF_UNPROFITABLE_AFTER_N_SESSIONS
    setup_tie_policy: TiePolicy = TiePolicy.STRICT_LESS         # RECOVERED default
    reversal_policy: str = ReversalPolicy.ENTRY_DAY_ONLY        # RECOVERED (rule 3)
    protective_stop_mode: str = ProtectiveStopMode.ENABLED      # RECOVERED (rule 3)
    quantity: float = 1.0
    capital: float | None = None

    def __post_init__(self):
        if self.tick_size <= 0:
            raise ValueError("invalid_configuration: tick_size must be > 0")
        if self.reversal_policy not in (ReversalPolicy.NONE, ReversalPolicy.ENTRY_DAY_ONLY):
            raise ValueError(f"invalid_configuration: reversal_policy "
                             f"{self.reversal_policy!r}")
        if self.protective_stop_mode not in (ProtectiveStopMode.ENABLED,
                                             ProtectiveStopMode.NONE_TEST_PROTOCOL):
            raise ValueError("invalid_configuration: protective_stop_mode "
                             f"{self.protective_stop_mode!r}")

    @property
    def tie_policy_is_historical(self) -> bool:
        return is_historical_tie_policy(self.setup_tie_policy)

    def identity_material(self) -> dict:
        from engine.historical.kernel import KERNEL_VERSION
        return {
            "rule_id": RULE_ID,
            "setup_definition": "inside_day_and_nr4_high_minus_low",
            "setup_lookback": NR4_LOOKBACK,
            "setup_tie_policy": self.setup_tie_policy.value,
            "setup_tie_policy_is_historical": self.tie_policy_is_historical,
            "entry_mechanism": "stop_at_setup_high_plus_1_tick_low_minus_1_tick",
            "entry_timing": "next_session_after_setup, stop orders rest from session open",
            "tick_size": self.tick_size,
            "session_definition": (self.session.session_start, self.session.session_end),
            "data_basis": BASIS_STORED_RAW,
            "gap_policy": self.gap_policy.value,
            "ambiguity_policy": self.ambiguity_policy.value,
            "exit_mechanism": self.exit_convention.echo(),
            "protective_stop_mode": self.protective_stop_mode,
            "reversal_policy": self.reversal_policy,
            "breakeven_move": "not_applicable",   # static opposite-extreme stop (recovered)
            "kernel_version": KERNEL_VERSION,
        }


def run(bars, config: RaschkeIdNr4Config, *,
        ticks_by_date: dict[str, list[Tick]] | None = None,
        cost_model=None, log: RejectionLog | None = None) -> RunResult:
    """The Street Smarts Ch. 19 system over a RAW-basis bar list."""
    cost_model = cost_model or CostModel.zero()
    log = log or RejectionLog()
    identity = historical_rule_id(config.identity_material())
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    ranges = [nr7_range(h, l) for h, l in zip(highs, lows)]
    tick = float(config.tick_size)

    def planner(t: int) -> EntryPlan | None:
        setup_date = bars[t].date
        try:
            verdict = evaluate_id_nr4(highs, lows, ranges, t, config.setup_tie_policy)
        except ValueError:
            log.record(setup_date, RejectionReason.INSUFFICIENT_HISTORY,
                       what="id/nr4 window", setup_t=t)
            return None
        if verdict == "not_inside_day":
            log.record(setup_date, RejectionReason.NOT_INSIDE_DAY,
                       range=ranges[t], rule=RULE_ID)
            return None
        if verdict == "tie_rejected":
            log.record(setup_date, RejectionReason.TIE_REJECTED,
                       range=ranges[t], rule=RULE_ID)
            return None
        if verdict != "ok":
            log.record(setup_date, RejectionReason.NR4_FALSE,
                       range=ranges[t], rule=RULE_ID)
            return None

        setup_high, setup_low = float(highs[t]), float(lows[t])
        buy_level = setup_high + tick
        sell_level = setup_low - tick

        def protective_for(fill) -> StopOrder:
            # Rule 3: the additional stop one tick beyond the OPPOSITE extreme.
            # On the entry day it both closes and reverses (ReversalPolicy);
            # after that day it is a plain protective stop, because the reversal
            # order "expires on the close of this day" (Ch. 20).
            return StopOrder(side=SELL if fill.side == BUY else BUY,
                             level=sell_level if fill.side == BUY else buy_level,
                             kind="protective", order_id=f"{RULE_ID}#prot")

        return EntryPlan(
            orders=[
                StopOrder(side=BUY, level=buy_level, kind="entry",
                          oco_group="id_nr4", order_id=f"{RULE_ID}#buy"),
                StopOrder(side=SELL, level=sell_level, kind="entry",
                          oco_group="id_nr4", order_id=f"{RULE_ID}#sell"),
            ],
            meta={"setup_high": setup_high, "setup_low": setup_low,
                  "tick_size": tick, "setup_date": setup_date},
            protective_for=protective_for,
        )

    return run_bracket_system(
        rule_id=RULE_ID, bars=bars, exit_convention=config.exit_convention,
        tie_policy=config.setup_tie_policy, gap_policy=config.gap_policy,
        ambiguity_policy=config.ambiguity_policy,
        breakeven_move="none", cost_model=cost_model,
        quantity=config.quantity, capital=config.capital,
        signal_basis=BASIS_STORED_RAW, identity=identity,
        config_echo=config.identity_material(),
        entry_planner=planner,
        protective_stop_mode=config.protective_stop_mode,
        reversal_policy=config.reversal_policy,
        ticks_by_date=ticks_by_date or {}, log=log)


def spec():
    from engine.strategy_specs import StrategySpec
    return StrategySpec(name=RULE_ID, family="historical", live_checker=False,
                        provenance=PROVENANCE)


register_historical_spec(spec())
