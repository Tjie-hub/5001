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
"""
import hashlib
import inspect
import os

import yaml

import engine.registry_loader as rl


def _src_hash(fn) -> str:
    return hashlib.sha256(inspect.getsource(fn).encode()).hexdigest()


def test_nr7_backtest_source_matches_pinned_manifest_config_hash():
    """The research-side function whose backtest produced NR7_BULL's approval
    evidence must still be byte-identical to what was hashed at approval
    time -- registry/manifests/NR7_BULL_v1.yaml's artifacts.config_hash."""
    from engine.strategies import strategy_nr7_breakout
    man_path = os.path.join(os.path.dirname(rl.REGISTRY_PATH),
                            "manifests", "NR7_BULL_v1.yaml")
    with open(man_path) as f:
        manifest = yaml.safe_load(f)
    pinned = manifest["artifacts"]["config_hash"]
    assert _src_hash(strategy_nr7_breakout) == pinned, (
        "strategy_nr7_breakout source has changed since NR7_BULL v1 was "
        "approved -- its backtest evidence may no longer describe the "
        "current strategy logic. See this file's module docstring before "
        "updating the pinned hash.")


# No registry-schema field currently pins the LIVE checker's source (only
# the research-side backtest function is covered by the manifest's
# config_hash) -- pinned here as a plain constant, the same pattern this
# codebase already uses for shrink-only debt allowlists.
_NR7_LIVE_CHECKER_HASH = "f4cbc983deee1cf27450466470eeea09c47d7015e8a76ccc0aa8e070be2084ea"


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
