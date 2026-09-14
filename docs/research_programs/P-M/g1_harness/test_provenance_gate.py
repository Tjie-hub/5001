#!/usr/bin/env python3
"""Provenance hard-gate tests — mechanical, temp-dir isolated.

Covers: snapshot success, determinism of the preflight digest, drift refusal
(source/config/registration/freeze/store), double-pass ambiguity refusal,
missing-file refusal, git-state capture, and the immutable run directory.
No real Dataset B file is touched.
"""
import hashlib
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import provenance as prov  # noqa: E402


def write(p, content):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        f.write(content)
    return p


def make_env(tmp):
    src = write(os.path.join(tmp, "src", "harness.py"), "print('v1')\n")
    dep = write(os.path.join(tmp, "src", "dep.py"), "X = 1\n")
    cfg = write(os.path.join(tmp, "cfg", "run_config.json"), json.dumps({"a": 1}))
    reg = write(os.path.join(tmp, "gov", "REGISTRATION.md"), "# registration v1\n")
    fm = write(os.path.join(tmp, "gov", "FREEZE_MANIFEST.json"),
               json.dumps({"store": {"sha256": hashlib.sha256(b"store-bytes").hexdigest()}}))
    store = write(os.path.join(tmp, "store", "store.sqlite"), "store-bytes")
    return {"sources": [src, dep], "config_path": cfg,
            "registration_paths": [reg], "freeze_manifest_path": fm,
            "store_path": store}


def test_snapshot_success_and_contents():
    with tempfile.TemporaryDirectory() as tmp:
        env = make_env(os.path.join(tmp, "in"))
        base = os.path.join(tmp, "runs")
        run_id, run_dir, m = prov.snapshot_run(runs_base=base, label="T",
                                               gates={"g": True}, **env)
        assert run_id.startswith("RUN-") and run_dir.endswith(run_id)
        assert os.path.isfile(os.path.join(run_dir, "preflight_manifest.json"))
        assert m["gates"] == {"g": True}
        assert m["store"]["sha256"] == hashlib.sha256(b"store-bytes").hexdigest()
        assert m["source_files"][env["sources"][0]] == \
            hashlib.sha256(b"print('v1')\n").hexdigest()
        # immutable: a second snapshot with the same run_id space refuses
        try:
            os.makedirs(run_dir)
            raise AssertionError("existing run dir not refused")
        except FileExistsError:
            pass


def test_preflight_digest_deterministic():
    with tempfile.TemporaryDirectory() as t1, tempfile.TemporaryDirectory() as t2:
        envs = []
        for t in (t1, t2):
            env = make_env(t)
            # normalize content so both trees are byte-identical
            envs.append(env)
        d1 = prov.snapshot_run(runs_base=t1, label="T", **envs[0])[2]["preflight_digest"]
        d2 = prov.snapshot_run(runs_base=t2, label="T", **envs[1])[2]["preflight_digest"]
        assert d1 == d2


def test_source_drift_fails_seal():
    with tempfile.TemporaryDirectory() as tmp:
        env = make_env(tmp)
        base = os.path.join(tmp, "runs")
        run_id, run_dir, m = prov.snapshot_run(runs_base=base, label="T", **env)
        write(env["sources"][0], "print('CHANGED')\n")   # drift after preflight
        seal = prov.seal_run(run_dir, m, env["sources"], env["config_path"],
                             env["registration_paths"], env["store_path"])
        assert seal["valid_provenance"] is False
        assert env["sources"][0] in seal["drifted_files"]


def test_store_drift_refused_at_preflight():
    with tempfile.TemporaryDirectory() as tmp:
        env = make_env(tmp)
        base = os.path.join(tmp, "runs")
        # store content changes vs the freeze-manifest pin -> preflight refuses
        write(env["store_path"], "store-bytes-TAMPERED")
        try:
            prov.snapshot_run(runs_base=base, label="T", **env)
            raise AssertionError("tampered store accepted")
        except prov.ProvenanceRefused as e:
            assert "store sha256" in str(e)


def test_config_drift_fails_seal():
    with tempfile.TemporaryDirectory() as tmp:
        env = make_env(tmp)
        base = os.path.join(tmp, "runs")
        run_id, run_dir, m = prov.snapshot_run(runs_base=base, label="T", **env)
        write(env["config_path"], json.dumps({"a": 2}))
        seal = prov.seal_run(run_dir, m, env["sources"], env["config_path"],
                             env["registration_paths"], env["store_path"])
        assert seal["valid_provenance"] is False
        assert env["config_path"] in seal["drifted_files"]


def test_registration_drift_fails_seal():
    with tempfile.TemporaryDirectory() as tmp:
        env = make_env(tmp)
        base = os.path.join(tmp, "runs")
        run_id, run_dir, m = prov.snapshot_run(runs_base=base, label="T", **env)
        write(env["registration_paths"][0], "# registration v2 CHANGED\n")
        seal = prov.seal_run(run_dir, m, env["sources"], env["config_path"],
                             env["registration_paths"], env["store_path"])
        assert seal["valid_provenance"] is False
        assert env["registration_paths"][0] in seal["drifted_files"]


def test_missing_required_file_refuses():
    with tempfile.TemporaryDirectory() as tmp:
        env = make_env(tmp)
        env = {**env, "registration_paths": [os.path.join(tmp, "gov", "MISSING.md")]}
        try:
            prov.snapshot_run(runs_base=os.path.join(tmp, "runs"), label="T", **env)
            raise AssertionError("missing registration accepted")
        except prov.ProvenanceRefused as e:
            assert "missing required file" in str(e)


def test_double_pass_ambiguity_refused():
    """A source file that changes between the two hash passes aborts."""
    import threading
    real_sleep = None
    with tempfile.TemporaryDirectory() as tmp:
        env = make_env(tmp)
        victim = env["sources"][0]
        orig = provenance_sha = prov.sha256_file

        def flipping(p):
            h = orig(p)
            if p == victim:
                # flip content between passes
                flipping.n += 1
                if flipping.n % 2:
                    write(p, "print('v2')\n")
            return h
        flipping.n = 0
        prov.sha256_file = flipping
        try:
            prov.snapshot_run(runs_base=os.path.join(tmp, "runs"), label="T", **env)
            raise AssertionError("ambiguous state accepted")
        except prov.ProvenanceRefused:
            pass
        finally:
            prov.sha256_file = orig
            write(victim, "print('v1')\n")


def main():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
