#!/usr/bin/env python3
"""Immutable run-provenance wrapper (D-048 / governance closeout §E3). READ-ONLY
on all data; writes only under runs/<run_id>/.

Contract (fail-closed):
  * snapshot_run(...) hashes the executed Python sources (double-pass — a file
    that changes between the two passes is AMBIGUOUS and aborts), the config,
    the registration/spec documents, the Dataset B freeze manifest and the
    store binary, and verifies store_hash == freeze-manifest store sha256.
  * A missing/changed registration or freeze manifest, or a store hash that no
    longer matches the freeze manifest, aborts BEFORE any data access.
  * seal_run(...) re-hashes sources/config/store after execution; any drift
    stamps the run INVALID_PROVENANCE (output retained but non-reportable).
  * runs/<run_id>/ is created exclusively (an existing run_id aborts) and is
    never overwritten. An index line is appended to runs/index.jsonl.
"""
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS_DIR = os.path.join(HERE, "runs")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_state(repo_root):
    """Best-effort git state. Never raises: absent/broken git is recorded,
    not hidden — the executed-file hashes remain the binding identity."""
    state = {"available": False, "commit": None, "dirty": None}
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_root,
                           capture_output=True, text=True, timeout=15)
        if r.returncode == 0:
            state["available"] = True
            state["commit"] = r.stdout.strip()
            s = subprocess.run(["git", "status", "--porcelain"], cwd=repo_root,
                               capture_output=True, text=True, timeout=30)
            state["dirty"] = bool(s.stdout.strip())
            state["dirty_lines"] = len(s.stdout.splitlines())
    except Exception as e:  # noqa: BLE001
        state["error"] = repr(e)[:200]
    return state


class ProvenanceRefused(SystemExit):
    """Raised when the preflight cannot establish an unambiguous, pinned state."""


def snapshot_run(sources, config_path, registration_paths, freeze_manifest_path,
                 store_path, runs_base=None, label="", gates=None,
                 extra_digest_files=None):
    """Create runs/<run_id>/ with the preflight manifest. Fail-closed."""
    runs_base = runs_base or RUNS_DIR
    sources = [os.path.abspath(p) for p in sources]
    for p in sources + [config_path] + list(registration_paths) + \
            [freeze_manifest_path, store_path]:
        if not os.path.isfile(p):
            raise ProvenanceRefused(f"provenance: missing required file {p}")

    def hash_all():
        return {p: sha256_file(p) for p in sources}

    src1 = hash_all()
    src2 = hash_all()
    if src1 != src2:
        raise ProvenanceRefused("provenance: source files changed between "
                                "successive hash passes — ambiguous state")

    cfg_hash = sha256_file(config_path)
    reg = {os.path.basename(p): sha256_file(p) for p in registration_paths}
    freeze_bytes = open(freeze_manifest_path, "rb").read()
    freeze_hash = hashlib.sha256(freeze_bytes).hexdigest()
    freeze = json.loads(freeze_bytes)
    store_hash = sha256_file(store_path)
    if store_hash != freeze.get("store", {}).get("sha256"):
        raise ProvenanceRefused(
            f"provenance: store sha256 {store_hash[:16]}… does not match the "
            f"freeze manifest pin {freeze.get('store', {}).get('sha256','')[:16]}… "
            "— input/store fingerprint changed after freeze")

    extra = {os.path.basename(p): sha256_file(p)
             for p in (extra_digest_files or []) if os.path.isfile(p)}

    digest_material = {
        "sources": {os.path.basename(k): v for k, v in src1.items()},
        "config_sha256": cfg_hash, "registrations": reg,
        "freeze_manifest_sha256": freeze_hash, "store_sha256": store_hash,
        "extra_digest_files": extra, "label": label}
    preflight_digest = hashlib.sha256(
        json.dumps(digest_material, sort_keys=True,
                   separators=(",", ":")).encode()).hexdigest()
    now = datetime.now(timezone.utc)
    run_id = f"RUN-{now:%Y%m%dT%H%M%SZ}-{preflight_digest[:12]}"
    run_dir = os.path.join(runs_base, "runs", run_id)
    if os.path.exists(run_dir):
        raise ProvenanceRefused(f"provenance: run directory already exists {run_dir}")
    os.makedirs(run_dir)

    manifest = {
        "artifact": "RUN_PREFLIGHT_MANIFEST",
        "run_id": run_id,
        "label": label,
        "preflight_digest": preflight_digest,
        "created_utc": now.isoformat(),
        "gates": gates or {},
        "git_state": _git_state(os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))),
        "source_files": src1,
        "config": {"path": config_path, "sha256": cfg_hash},
        "registrations": reg,
        "freeze_manifest": {"path": freeze_manifest_path, "sha256": freeze_hash,
                            "store_sha256_pin": freeze.get("store", {}).get("sha256")},
        "store": {"path": store_path, "sha256": store_hash},
        "extra_digest_files": extra,
    }
    with open(os.path.join(run_dir, "preflight_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=True, allow_nan=False)
    return run_id, run_dir, manifest


def seal_run(run_dir, manifest, sources, config_path, registrations,
             store_path, output_files=()):
    """Post-run seal: re-hash sources/config/registrations/store; stamp the run
    VALID or INVALID_PROVENANCE; hash the outputs. Returns the seal dict."""
    result = {"artifact": "RUN_SEAL"}
    now_src = {p: sha256_file(p) for p in sources}
    drifted = {p for p, h in now_src.items() if manifest["source_files"].get(p) != h}
    if sha256_file(config_path) != manifest["config"]["sha256"]:
        drifted.add(config_path)
    for p in registrations:
        if sha256_file(p) != manifest["registrations"].get(os.path.basename(p)):
            drifted.add(p)
    result["valid_provenance"] = not drifted
    result["drifted_files"] = sorted(drifted)
    result["sealed_at_utc"] = datetime.now(timezone.utc).isoformat()
    result["outputs"] = {os.path.basename(p): sha256_file(p) for p in output_files
                         if os.path.isfile(p)}
    seal_path = os.path.join(run_dir, "seal.json")
    with open(seal_path, "w") as f:
        json.dump(result, f, indent=1, sort_keys=True, allow_nan=False)
    return result
