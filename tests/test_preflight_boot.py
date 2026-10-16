"""scripts/preflight_boot.py decision (the boot itself runs in safe_restart.sh, not in the hermetic suite)."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "preflight_boot", Path(__file__).resolve().parent.parent / "scripts" / "preflight_boot.py")
pb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pb)


def test_verdict():
    assert pb.verdict(52, [])[0] is True
    assert pb.verdict(0, [], error="NameError: name 'run_post_close_sweep' is not defined")[0] is False  # 10-15
    assert pb.verdict(52, ["Scheduler failed to register job 'x'"])[0] is False
    assert pb.verdict(10, [])[0] is False


def test_safe_restart_runs_preflight_before_restarting():
    sh = (Path(__file__).resolve().parent.parent / "scripts" / "safe_restart.sh").read_text()
    assert sh.index("preflight_boot.py") < sh.index("systemctl --user restart")
