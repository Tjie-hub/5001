"""RC1-C1 regression tests: the `.as_posix()` allowlist-matching pattern
applied to test_architecture_boundary.py, test_db_centralization.py,
test_research_data_fence.py, and test_config_hygiene.py must behave
identically regardless of which path-separator convention a Path object
carries. Uses pathlib.PureWindowsPath/PurePosixPath (no filesystem access,
so this runs identically on any host OS) to demonstrate the exact bug and
fix mechanism, independent of any one boundary test file.
"""
from pathlib import PurePosixPath, PureWindowsPath


def test_windows_and_posix_relative_paths_normalize_identically():
    win = PureWindowsPath("routes") / "backtest.py"
    posix = PurePosixPath("routes") / "backtest.py"
    assert win.as_posix() == posix.as_posix() == "routes/backtest.py"


def test_str_conversion_is_the_bug_as_posix_is_the_fix():
    """The exact RC1-C1 root cause: str() on a Windows-flavoured path always
    uses backslashes (platform-dependent), while .as_posix() always uses
    forward slashes (platform-independent) -- allowlists are written as
    forward-slash strings, so only .as_posix() matches them reliably."""
    win = PureWindowsPath("engine") / "agent_firm" / "config.py"
    assert str(win) == "engine\\agent_firm\\config.py"
    assert win.as_posix() == "engine/agent_firm/config.py"


def test_mixed_separator_input_normalizes_via_as_posix():
    mixed = PureWindowsPath("routes\\backtest.py")  # native Windows string form
    assert mixed.as_posix() == "routes/backtest.py"
    nested_mixed = PureWindowsPath("engine/agent_firm\\config.py")  # both seps present
    assert nested_mixed.as_posix() == "engine/agent_firm/config.py"


def test_allowlist_membership_matches_regardless_of_path_flavor():
    """Reproduces the actual bug: a set of forward-slash allowlist strings
    (as used in DOTENV_ALLOWED / ALLOWLIST / DAO_ALLOWLIST across the four
    fixed test files) must match a path relative_to()'d and rendered via
    .as_posix(), whichever OS produced the original Path object."""
    allowlist = {"routes/backtest.py", "engine/agent_firm/config.py", "data/db.py"}

    win_rel = (PureWindowsPath("routes") / "backtest.py").as_posix()
    posix_rel = (PurePosixPath("engine") / "agent_firm" / "config.py").as_posix()
    single_component = PurePosixPath("data/db.py").as_posix()

    assert win_rel in allowlist
    assert posix_rel in allowlist
    assert single_component in allowlist

    # the bug this regression-guards against: str() on the Windows-flavoured
    # path would NOT match the (forward-slash) allowlist.
    assert str(PureWindowsPath("routes") / "backtest.py") not in allowlist


def test_single_component_paths_are_unaffected_either_way():
    """A relative path with no directory separator (e.g. routes_backtest_multi.py,
    data/db.py's own PRODUCTION_FILES-style single-file entries) matches under
    both str() and .as_posix() -- confirms the bug was specifically about
    multi-component (nested) paths, not a universal allowlist failure."""
    p = PureWindowsPath("routes_backtest_multi.py")
    assert str(p) == p.as_posix() == "routes_backtest_multi.py"
