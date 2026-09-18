"""engine/historical/base.py — shared scaffolding for the Phase 8 systems.

Everything here is ENGINE CONVENTION scaffolding (position records, run
results, exit-convention declarations). Nothing here is a historical rule;
each system module carries its own provenance separating the two.

Exit mechanics — CORRECTED by the 2026-09-03 provenance closure audit. The
previous version of this docstring said no deterministic exit was recovered for
either author. That was wrong on both counts:

  Crabel 1990 states the exit used throughout the book's OWN test protocol:
      "the number of days into the trade (zero indicates an exit on the close
       the same day of entry, five indicates an exit on the close five days
       after the entry)" ... "no stops were used on the tests"
  -> ExitKind.MOC_AFTER_N_SESSIONS with N >= 0, and ProtectiveStopMode.
     NONE_TEST_PROTOCOL. N = 0 is the book's BASELINE case and the old
     `moc_hold_sessions >= 1` guard could not express it.

  Raschke & Connors, Street Smarts Ch. 19 rule 5 states a conditional time stop:
      "If the position is not profitable within two days and you have not been
       stopped out, exit the trade MOC (market on close.)"
  -> ExitKind.MOC_IF_UNPROFITABLE_AFTER_N_SESSIONS.

What remains PRIMARY SOURCE NOT RECOVERED is (a) Crabel's DISCRETIONARY trading
exit — "a two to three day run" is guidance, not a rule, and is recorded in
provenance.discretionary_guidance — and (b) Raschke's trailing stop ("Trail a
stop to lock in accrued profits"), which names no mechanism.

A research-protocol exit is NOT the same object as live trade management, and
the two must never be conflated: ExitConvention describes the former only.
"""
from dataclasses import dataclass, field

from engine.historical.kernel import KERNEL_VERSION
from engine.historical.telemetry import RejectionLog

SIGNAL_BASIS_STORED_RAW = "stored_raw"
"""As-stored prices with NO adjustment applied at load time. Caveat recorded in
Phase 9: rebuild-time splits are pre-adjusted at the source, so `stored_raw` is
exact raw only for post-rebuild history and for corporate actions the corpus
did not pre-adjust. Per-series basis provenance must be recorded alongside."""


class ExitKind:
    """Deterministic exit conventions. Two of these are now RECOVERED research
    protocols rather than engine inventions (see module docstring); the third
    is research scaffolding. All three are exposed and hashed either way."""

    MOC_AFTER_N_SESSIONS = "moc_after_n_sessions"
    """RECOVERED (Crabel 1990 test protocol). Exit on the close N sessions after
    the entry session. N = 0 means the close of the ENTRY session itself."""

    MOC_IF_UNPROFITABLE_AFTER_N_SESSIONS = "moc_if_unprofitable_after_n_sessions"
    """RECOVERED (Street Smarts Ch. 19 rule 5). At the close of session
    `profit_check_sessions` (the entry session counts as session 1), exit MOC if
    the position is not profitable. A profitable position is left open — the
    rule that would then manage it is a trailing stop, and its mechanism is
    PRIMARY SOURCE NOT RECOVERED."""

    HOLD_TO_END_OF_DATA = "hold_to_end_of_data"
    """ENGINE CONVENTION — research-only: the position survives the sample."""


class ProtectiveStopMode:
    """Whether a protective stop rests at all.

    Crabel 1990 documents BOTH modes and they are not interchangeable: the Ch. 1
    trading method rests an opposing stop ("the other stop is used as a
    protective stop"), while the book's statistical tests state plainly that
    "no stops were used on the tests". Replicating the test protocol with a stop
    installed would measure a different rule than the one the book reports."""

    ENABLED = "enabled"
    NONE_TEST_PROTOCOL = "none_test_protocol"


class ReversalPolicy:
    """Street Smarts Ch. 19 rule 3 / Ch. 20 rule 4 — RECOVERED.

    "if we are filled on the buy side, enter an additional sell-stop one tick
     below the ID/NR4 bar. This means that if the trade is a loser, not only
     will we get stopped out with a loss, we will reverse and go short."
    "This additional sell-stop is done on the entry day only, and expires on the
     close of this day."

    This belongs to the Raschke ID/NR4 system ONLY. Crabel's systems have no
    reversal — his opposing stop is a protective stop, not a stop-and-reverse —
    so the Crabel configs carry no field through which it could enter."""

    NONE = "none"
    ENTRY_DAY_ONLY = "entry_day_only"


class BreakevenPolicy:
    """Crabel protective-stop management. Recovered statement is INTRADAY
    ('stops were historically moved to break-even within one hour'); daily bars
    cannot represent an intraday hour, so both options below are ENGINE
    CONVENTIONS. PRIMARY SOURCE NOT RECOVERED (deterministic daily-bar mapping)."""
    NONE = "none"                    # protective stop stays at the opposite structural level
    AFTER_ENTRY_SESSION = "after_entry_session"  # moved to break-even at the start of the
                                                 # session following the entry session


_EXIT_KINDS = (ExitKind.MOC_AFTER_N_SESSIONS,
               ExitKind.MOC_IF_UNPROFITABLE_AFTER_N_SESSIONS,
               ExitKind.HOLD_TO_END_OF_DATA)


@dataclass(frozen=True)
class ExitConvention:
    kind: str                       # ExitKind.*
    moc_hold_sessions: int | None = None      # MOC_AFTER_N_SESSIONS; 0 = entry-session close
    profit_check_sessions: int | None = None  # MOC_IF_UNPROFITABLE_AFTER_N_SESSIONS

    def __post_init__(self):
        if self.kind not in _EXIT_KINDS:
            raise ValueError(f"unknown exit kind: {self.kind!r}")
        if self.kind == ExitKind.MOC_AFTER_N_SESSIONS:
            # >= 0, not >= 1: N = 0 (exit on the entry session's close) is the
            # Crabel 1990 test protocol's baseline case.
            if self.moc_hold_sessions is None or self.moc_hold_sessions < 0:
                raise ValueError("moc_after_n_sessions requires moc_hold_sessions >= 0")
        if self.kind == ExitKind.MOC_IF_UNPROFITABLE_AFTER_N_SESSIONS:
            if self.profit_check_sessions is None or self.profit_check_sessions < 1:
                raise ValueError(
                    "moc_if_unprofitable_after_n_sessions requires "
                    "profit_check_sessions >= 1")

    def echo(self) -> tuple:
        """Identity-material form: every parameter that changes the exit."""
        return (self.kind, self.moc_hold_sessions, self.profit_check_sessions)


# BreakevenPolicy is NOT part of ExitConvention: the Crabel systems carry it as
# a REQUIRED config field of their own (no default), because the recovered
# statement — "stops were historically moved to break-even within one hour" —
# is intraday, and the daily-bar mapping for it is PRIMARY SOURCE NOT RECOVERED.
# A silent default here would be an ahistorical choice.


@dataclass(frozen=True)
class SessionDefinition:
    """Session window metadata. The session START for the Opening Range and the
    overall session boundaries are market/era-specific:
    PRIMARY SOURCE NOT RECOVERED (1988 pit-session boundaries).
    """
    session_start: str              # 'HH:MM:SS' — anchor for Opening Range construction
    session_end: str | None = None  # informational for daily-bar mode (bar close IS the close)


@dataclass
class HistoricalTrade:
    """One executed historical trade. All trigger/level prices are RAW BASIS.
    Cost-adjusted accounting prices are recorded alongside, never substituted."""
    rule_id: str
    side: str                       # LONG / SHORT
    quantity: float
    signal_basis: str               # data basis the setup/trigger geometry was computed on
    pnl_basis: str                  # data basis the recorded pnl was computed on
    entry_date: str
    entry_price_raw: float
    entry_price_accounting: float   # cost model applied — accounting ONLY
    entry_fill_convention: str
    stop_level_raw: float | None    # protective stop actually resting after entry (raw);
                                    # None under ProtectiveStopMode.NONE_TEST_PROTOCOL
    exit_date: str = ""
    exit_price_raw: float = 0.0
    exit_price_accounting: float = 0.0
    exit_reason: str = ""
    pnl_raw: float = 0.0            # (raw exit − raw entry) * qty, direction-signed
    pnl_net: float = 0.0            # accounting prices, direction-signed
    pnl_basis_factor: float = 1.0   # raw→pnl-basis conversion factor applied (1.0 = same basis)
    conventions: dict = field(default_factory=dict)


@dataclass
class RunResult:
    """Outcome of one historical system run over one bar series."""
    rule_id: str
    signal_basis: str
    trades: list
    rejections: RejectionLog
    config_echo: dict
    identity: str

    @property
    def n_trades(self) -> int:
        return len(self.trades)

    @property
    def zero_trade(self) -> bool:
        return self.n_trades == 0

    def histogram(self) -> dict:
        return self.rejections.histogram()

    def to_summary(self) -> dict:
        """Machine-readable run summary. A zero-trade run MUST expose the full
        rejection histogram (Phase 9 §14) — this method always includes it."""
        return {
            "rule_id": self.rule_id,
            "identity": self.identity,
            "n_trades": self.n_trades,
            "zero_trade": self.zero_trade,
            "signal_basis": self.signal_basis,
            "rejection_histogram": self.histogram(),
            "rejections": self.rejections.to_list(),
            "kernel_version": KERNEL_VERSION,
            "config": self.config_echo,
        }
