"""T7 invariant #7 -- execution-model compatibility, enforced via source-hash
pinning.

Investigation (Audit/T7_PRODUCTION_EXECUTION_BOUNDARY_AUDIT.md §8) compared
research's backtest execution model against production's live scan for the
one live registry entry, NR7_BULL, on bar finality, entry timing/price,
signal timestamp, scan frequency, and partial-bar handling. Finding: the two
are currently ALIGNED (research: signal on a fully-closed prior bar, fill at
the next bar's open, via `research/jobs.py`'s `final_only=True` load; live:
`check_nr7_signal` reads its signal off `df.iloc[-2]` -- a prior, closed bar
-- and prices entry at `df.iloc[-1]`'s `open`, which is fixed from market
open regardless of whether that bar itself is still forming). Production
scans intraday do admit partial bars in general (`data/loaders.py`'s
documented default), but NR7's checker never reads a mutable field
(high/low/close) off the potentially-partial last bar, so it isn't exposed.

The gap this file closes: nothing MECHANICALLY verifies this alignment
holds going forward. `engine/registry_loader.py`'s `requires{}`/
`ENGINE_VERSIONS` compatibility gate exists but (per `git log -p --all --
engine/registry_loader.py`) has been touched in exactly one commit -- its
introduction -- and is never bumped or tested against real code changes.
Separately, `registry/manifests/NR7_BULL_v1.yaml` already pins a
`config_hash` (sha256 of the research-side `strategy_nr7_breakout` source)
but nothing re-verifies it still matches; and the live production checker
(`check_nr7_signal`) has no pin at all. Both are closed here by pinning the
actual source hash of both functions, so any future edit that could change
the bar-convention/entry-timing/pricing assumptions NR7_BULL's evidence
relied on fails a test instead of shipping unnoticed.

If either test below ever fails from a DELIBERATE, reviewed code change:
do not just update the pinned hash to make it pass. First confirm whether
the change affects the execution-model assumptions in this docstring; if it
does, NR7_BULL's approval evidence (registry/manifests/NR7_BULL_v1.yaml,
grandfathered via engine.registry_loader._LIFECYCLE_DEBT) may no longer
describe the live execution model, which is exactly the situation T7
invariant #7 exists to catch.

--------------------------------------------------------------------------
AMENDED 2026-09-02 — the "ALIGNED" finding above was WRONG, and this is the
situation the file was written to catch.

The original reasoning was that live and research agree because both price the
entry at the same number: `df.iloc[-1]['open']`, "fixed from market open
regardless of whether that bar itself is still forming". Stability of the VALUE
was mistaken for equivalence of the EXECUTION MODEL. They are not the same
thing. Research decides at the open and fills at that open. Live decides at
10:05 / 11:05 / 14:35 and would have filled at a print hours in the past —
unattainable, and systematically favourable, because NR7's trigger condition
IS "the open gapped above the setup bar's high", so only the entries that had
already moved the right way were ever taken.

Two production changes follow (see docs/audit/SIGNAL_PROVENANCE_AUDIT_2026-09-02.md,
findings L-1 and L-2), and BOTH change this function's source, hence the new
pin below:

  * `check_nr7_signal` now declares `details['price_basis'] = session_open` and
    `details['entry_rule'] = NEXT_SESSION_OPEN`. The trigger comparison is
    unchanged — the gap-up test is still the correct rule; only the honesty
    about what that price IS has been added.
  * `engine/entry_convention.py` refuses to fill any price on a retrospective
    basis. A live scan now STAGES a signal for the next session's open, which
    is the convention every walk-forward strategy function already fills on.

The prior finding is preserved above verbatim rather than corrected in place:
it is the record of what was believed when NR7_BULL's evidence was assessed.
NR7_BULL is SHADOW as of 2026-08-19 (D-029) and authorises no capital, so no
live position was ever opened under the mistaken model.

--------------------------------------------------------------------------
AMENDED 2026-10-01 — P4-2 (ARA/ARB fillability, ZCODE brief
ZCODE_BRIEF_P4_EVIDENCE_HONESTY_2026-09-30.md) changed strategy_nr7_breakout's
source deliberately, hence the new pin below.

`strategy_nr7_breakout` now caps its TP/SL to the entry-day auto-rejection
band (engine/exits/price_limits.cap_levels — the same cap and capped-level
re-gate paper_trade.open_trade applies live), so a target beyond ARA can no
longer fill at a price the exchange never prints. Entry timing, trigger
logic and the next-bar-open fill convention are UNCHANGED — this is a
level-fillability correction, not a timing change.

What that means for NR7_BULL v1's approval evidence: the expectancy the v1
approval rested on was computed under the uncapped model and is therefore
STALE. NR7_BULL remains SHADOW and authorises no capital, so nothing live is
affected; the honest re-measured expectancy is the P4-2 re-run recorded in
docs/superpowers/results/2026-07-07-nr7-generalization-study.md. Whether
NR7_BULL's admission should be re-decided under the corrected numbers is an
Owner call, flagged in the P4 handoff — updating this pin records what the
code now is, not that the v1 evidence still describes it.

CORRECTED same day (reconcile brief §1): the pin below follows the 2026-09-02
precedent properly — the current source hash is pinned HERE as a test constant
and the manifests are left alone. A manifest's config_hash is the
APPROVAL-TIME provenance and is not updated when the source later changes;
test_nr7_bull_manifests_pin_the_approval_time_hash guards both manifests
against exactly that mistake (an earlier version of the P4-2 commit
overwrote v1's hash, which also left v1 and v2 disagreeing).
"""
import hashlib
import inspect
import os

import yaml

import engine.registry_loader as rl


def _src_hash(fn) -> str:
    return hashlib.sha256(inspect.getsource(fn).encode()).hexdigest()


def test_nr7_backtest_source_matches_pinned_manifest_config_hash():
    """The research-side function whose backtest produced NR7_BULL's evidence,
    pinned to its CURRENT source hash (a test constant, per the 2026-09-02
    precedent — the live checker below uses the same pattern).

    This is the "what the code is now" pin: a deliberate execution-model
    change must consciously update it (see the module docstring's amendment
    history). The manifests keep the approval-time hash instead — see
    test_nr7_bull_manifests_pin_the_approval_time_hash."""
    from engine.strategies import strategy_nr7_breakout
    assert _src_hash(strategy_nr7_breakout) == _NR7_BACKTEST_HASH, (
        "strategy_nr7_breakout source has changed since the pin below was "
        "recorded. See this file's module docstring before updating it.")


# The hash of strategy_nr7_breakout's source as of the P4-2 fillability fix
# (2026-10-01). Recomputed at that time; do not copy from a manifest.
_NR7_BACKTEST_HASH = "a87badb0c138722e9fee33df7d8c4ccc9202993de15b10507597b2e9afacada1"

_NR7_LIVE_CHECKER_HASH = "3efae1a0615b4ce56ef550f65c4a1c343ed54813f2354eda1b8418ad75c42861"


def test_nr7_bull_manifests_pin_the_approval_time_hash():
    """Guard (reconcile brief §1): both NR7_BULL manifests' config_hash are the
    APPROVAL-TIME provenance and must stay frozen at the hash the v1 approval
    was measured under — regardless of later source changes. Overwriting a
    manifest hash to make a pin pass rewrites what was approved."""
    approval_hash = ("8845c57b918a67ed513e67357d89f5f60388ce6110"
                     "5c20d8d496e303eab87a08")
    manifests_dir = os.path.join(os.path.dirname(rl.REGISTRY_PATH), "manifests")
    for name in ("NR7_BULL_v1.yaml", "NR7_BULL_v2.yaml"):
        with open(os.path.join(manifests_dir, name)) as f:
            manifest = yaml.safe_load(f)
        assert manifest["artifacts"]["config_hash"] == approval_hash, (
            f"{name} config_hash must remain the approval-time hash; it is "
            "provenance, not a pin to keep current. Update the test constant "
            "_NR7_BACKTEST_HASH instead.")


def test_nr7_live_checker_source_is_pinned():
    """check_nr7_signal (engine/strategies.py) is the function that actually
    decides live entries -- pin it so a change to its entry price/timing
    convention (currently: signal off the prior closed bar, fill at the
    current bar's open) is caught even though no registry-schema field
    covers it today."""
    from engine.strategies import check_nr7_signal
    assert _src_hash(check_nr7_signal) == _NR7_LIVE_CHECKER_HASH, (
        "check_nr7_signal source has changed. See this file's module "
        "docstring before updating the pinned hash.")
