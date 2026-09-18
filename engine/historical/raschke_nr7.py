"""engine/historical/raschke_nr7.py — System B-transfer: raschke_nr7.v1.

**THIS IS NOT A PRIMARY-SOURCE RASCHKE SYSTEM.** Tier T (transfer).

The 2026-09-03 provenance closure audit recovered the full text of Street Smarts
and established that it contains NO standalone NR7 rule set. NR7 appears there
exactly once, in Chapter 19, and not as a rule set:

    "One of the simplest concepts which I use regularly is Toby's NR7. This
     represents the narrowest range of the last seven days. I automatically use
     this as a filter to switch to a breakout mode the day following an NR7.
     This means that I will not try to countertrend trade. Instead, I will try
     and enter the market in the direction it is moving."

That is a bias filter, attributed by Raschke to Crabel. The numbered rule set
this module executes — one-tick entry beyond the setup extreme, protective stop
one tick beyond the opposite extreme — is stated in Chapter 19 for **ID/NR4**,
not for NR7. Combining Crabel's NR7 setup with Raschke's ID/NR4 mechanics is a
TRANSFER that no source states, so:

  - the tier is ProvenanceTier.TIER_T_TRANSFER, never TIER_A_DIRECT;
  - the transfer is named in provenance.adaptations;
  - the genuine Street Smarts system lives in
    engine/historical/raschke_id_nr4.py (raschke_id_nr4.v1) and is the one that
    carries Tier A.

The previous version of this module claimed Tier A and cited "Chapters 16 and
20". Chapter 16 is "News" and contains no setup at all.

NO STOP-AND-REVERSE HERE. Rule 3's reversal is part of the ID/NR4 rule set and
is implemented only in raschke_id_nr4.v1. Transferring the setup was already one
unsupported step; transferring the reversal on top of it would compound it.

EXIT: the two-day unprofitable MOC time stop is likewise an ID/NR4 rule. What
this module carries is whatever ExitConvention the caller declares, and that
choice is an ENGINE CONVENTION here.

MANDATED EXCLUSIONS: no Crabel Stretch, no Opening Range, no ATR, no True Range,
no 89 SMA, no volume filters, no modern trend filters. The config has no fields
through which any of them could enter.
"""
from dataclasses import dataclass

from engine.historical.base import (ExitConvention, ProtectiveStopMode,
                                    RunResult, SessionDefinition)
from engine.historical.costs import CostModel
from engine.historical.data import BASIS_STORED_RAW
from engine.historical.kernel import (AmbiguityPolicy, GapPolicy, StopOrder,
                                      Tick)
from engine.historical.nr7 import (NR7_LOOKBACK, TiePolicy, evaluate_nr7,
                                   is_historical_tie_policy, nr7_range)
from engine.historical.provenance import (UNCONTROLLED_WITNESS,
                                          HistoricalProvenance, ProvenanceTier,
                                          register_historical_spec)
from engine.historical.runner import EntryPlan, run_bracket_system
from engine.historical.telemetry import RejectionLog, RejectionReason
from engine.rule_identity import historical_rule_id

RULE_ID = "raschke_nr7.v1"

_PSR = "PRIMARY SOURCE NOT RECOVERED."

PROVENANCE = HistoricalProvenance(
    tier=ProvenanceTier.TIER_T_TRANSFER,
    citations=(
        "SETUP: Toby Crabel, 'Day Trading with Short Term Price Patterns and "
        "Opening Range Breakout', Traders Press (1990), Glossary p. 285 — the "
        "NR7 definition; primary text recovered 2026-09-03.",
        "MECHANICS: Linda Bradford Raschke & Larry Connors, 'Street Smarts', "
        "M. Evans & Co. (1995), Chapter 19 'Range Contraction' and Chapter 20 "
        "'Historical Volatility Meets Toby Crabel' — stated there for ID/NR4, "
        "NOT for NR7.",
        "Street Smarts Chapter 19 also records Raschke's own NR7 usage: a bias "
        "filter ('a filter to switch to a breakout mode the day following an "
        "NR7'), not an entry/stop/exit rule set.",
    ),
    historical_rules=(
        "NR7: 'a daily range that is narrower than the previous six days compared "
        "individually to the day in question' (Crabel 1990, Glossary p. 285).",
        "Raschke uses NR7 as a breakout-mode bias filter on the following "
        "session, and attributes the pattern to Crabel (Street Smarts Ch. 19).",
        "The one-tick offset mechanism is genuine Raschke rule language, stated "
        "for the ID/NR4 setup (Ch. 19 rule 2).",
    ),
    adaptations=(
        "This system pairs Crabel's NR7 setup with the one-tick entry and "
        "opposite-extreme protective stop that Street Smarts states for ID/NR4. "
        "No primary source states those mechanics for NR7; the pairing is a "
        "TRANSFER and is not a recovered rule.",
        "Raschke's recovered NR7 usage is a directional bias filter, not a "
        "mechanical entry; treating it as an entry rule is part of the transfer.",
        "The stop-and-reverse (Ch. 19 rule 3) and the two-day unprofitable MOC "
        "exit (rule 5) are deliberately NOT transferred here — see "
        "raschke_id_nr4.v1, which implements them under Tier A.",
    ),
    discretionary_guidance=(
        "Street Smarts Ch. 19: 'Trail a stop to lock in accrued profits' — no "
        "mechanism specified.",
    ),
    engine_conventions=(
        "The exit convention is an engine choice here: the recovered two-day MOC "
        "rule belongs to the ID/NR4 rule set, not to this transfer.",
        "Tie policy follows the recovered strict inequality; MIN_INCLUSIVE is "
        "ahistorical legacy parity only.",
        "Session boundaries, gap policy and intra-session OCO ambiguity policy "
        "are engine conventions.",
        "The numeric tick size is an exchange/instrument parameter, not a "
        "historical unknown.",
        "Costs apply to PnL accounting only; triggers/levels stay raw.",
    ),
    data_basis=BASIS_STORED_RAW,
    entry_mechanism="stop orders at setup-day High + 1 tick / Low - 1 tick "
                    "(TRANSFERRED from the ID/NR4 rule set), OCO, intraday ticks "
                    "used for trigger ordering where available",
    exit_mechanism="protective stop one tick beyond the opposite setup-day extreme "
                   "(transferred); no stop-and-reverse; deterministic exit is an "
                   "engine convention for this transfer",
    session_definition="required SessionDefinition(session_start[, session_end]); "
                       "historical session boundaries " + _PSR,
    tick_size="one tick = the instrument's minimum price increment; an "
              "exchange/instrument parameter, not a source gap",
    tie_policy="strict inequality ('narrower than'), recovered from the 1990 "
               "Glossary; TiePolicy.MIN_INCLUSIVE is ahistorical legacy parity only",
    gap_policy="required explicit GapPolicy; " + _PSR,
    unrecovered_items=(
        "Any Raschke rule set for NR7 as a standalone setup: " + _PSR,
        "Deterministic exit for this transfer: " + _PSR,
        "Historical session boundaries (era/market): " + _PSR,
        "Gap-through-stop fill behavior: " + _PSR,
        "Intra-session ordering when both OCO legs trigger on one daily bar: " + _PSR,
    ),
    witness=UNCONTROLLED_WITNESS,
)


@dataclass(frozen=True)
class RaschkeNr7Config:
    tick_size: float                     # instrument minimum price increment
    session: SessionDefinition           # PRIMARY SOURCE NOT RECOVERED
    gap_policy: GapPolicy                # PRIMARY SOURCE NOT RECOVERED
    ambiguity_policy: AmbiguityPolicy    # PRIMARY SOURCE NOT RECOVERED
    exit_convention: ExitConvention      # engine convention for this transfer
    nr7_tie_policy: TiePolicy = TiePolicy.STRICT_LESS       # RECOVERED default
    protective_stop_mode: str = ProtectiveStopMode.ENABLED
    quantity: float = 1.0
    capital: float | None = None

    def __post_init__(self):
        if self.tick_size <= 0:
            raise ValueError("invalid_configuration: tick_size must be > 0")
        if self.protective_stop_mode not in (ProtectiveStopMode.ENABLED,
                                             ProtectiveStopMode.NONE_TEST_PROTOCOL):
            raise ValueError("invalid_configuration: protective_stop_mode "
                             f"{self.protective_stop_mode!r}")

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
            "entry_mechanism": "stop_at_setup_high_plus_1_tick_low_minus_1_tick",
            "entry_timing": "next_session_after_setup, stop orders rest from session open",
            "tick_size": self.tick_size,
            "session_definition": (self.session.session_start, self.session.session_end),
            "data_basis": BASIS_STORED_RAW,
            "gap_policy": self.gap_policy.value,
            "ambiguity_policy": self.ambiguity_policy.value,
            "exit_mechanism": self.exit_convention.echo(),
            "protective_stop_mode": self.protective_stop_mode,
            "reversal_policy": "none",   # the reversal belongs to raschke_id_nr4.v1
            "provenance_tier": ProvenanceTier.TIER_T_TRANSFER.value,
            "breakeven_move": "not_applicable",  # static opposite-extreme stop
            "kernel_version": KERNEL_VERSION,
        }


def run(bars, config: RaschkeNr7Config, *,
        ticks_by_date: dict[str, list[Tick]] | None = None,
        cost_model: CostModel | None = None,
        log: RejectionLog | None = None) -> RunResult:
    """System B over a RAW-basis bar list. Entry anchors are the SETUP day's
    extremes ± 1 tick — no Stretch, no Opening Range, no ATR anywhere."""
    cost_model = cost_model or CostModel.zero()
    log = log or RejectionLog()
    identity = historical_rule_id(config.identity_material())
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    ranges = [nr7_range(h, l) for h, l in zip(highs, lows)]
    tick = config.tick_size

    def planner(t: int) -> EntryPlan | None:
        setup_bar = bars[t]
        setup_date = setup_bar.date
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

        buy_level = float(setup_bar.high) + tick
        sell_level = float(setup_bar.low) - tick

        def protective_for(fill) -> StopOrder:
            # Recovered: 1 tick beyond the OPPOSITE extreme of the setup day.
            return StopOrder(side="SELL" if fill.side == "BUY" else "BUY",
                             level=sell_level if fill.side == "BUY" else buy_level,
                             kind="protective", order_id=f"{RULE_ID}#prot")

        return EntryPlan(
            orders=[
                StopOrder(side="BUY", level=buy_level, kind="entry",
                          oco_group="rsk", order_id=f"{RULE_ID}#buy"),
                StopOrder(side="SELL", level=sell_level, kind="entry",
                          oco_group="rsk", order_id=f"{RULE_ID}#sell"),
            ],
            meta={"setup_high": float(setup_bar.high),
                  "setup_low": float(setup_bar.low),
                  "tick_size": tick, "setup_date": setup_date},
            protective_for=protective_for,
        )

    return run_bracket_system(
        rule_id=RULE_ID, bars=bars, exit_convention=config.exit_convention,
        tie_policy=config.nr7_tie_policy, gap_policy=config.gap_policy,
        ambiguity_policy=config.ambiguity_policy,
        breakeven_move="none", cost_model=cost_model,
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
