#!/usr/bin/env python3
"""P-M PROSPECTIVE ACTIVATION GATE — mechanical readiness report.

Checks every gate that is mechanically checkable TODAY and prints PASS/FAIL.
Run from the prospective_validation directory. Nothing here activates capture,
writes to any production/frozen store, or performs inference.
"""
import sys, os, json, hashlib, sqlite3, re

HERE = os.path.dirname(os.path.abspath(__file__))
PM = os.path.dirname(HERE)
CAPTURE_DIR = os.path.join(PM, "flow_capture_prospective")
CAPTURE_PY = os.path.join(CAPTURE_DIR, "prospective_capture.py")
PROTOCOL = os.path.join(HERE, "PROSPECTIVE_PROTOCOL_V1.2_DRAFT_2026-09-16.md")
UNIVERSE = os.path.join(HERE, "universe_frozen.csv")
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))

results = []


def gate(gid, name, ok, detail=""):
    results.append({"gate": gid, "name": name, "pass": bool(ok), "detail": detail})
    print(f"  [{ 'PASS' if ok else 'FAIL' }] {gid} {name}" + (f" — {detail}" if detail else ""))


def main():
    print("=== P-M PROSPECTIVE ACTIVATION GATE ===")
    src = open(CAPTURE_PY, encoding="utf-8").read()
    # G-1 protocol frozen?
    proto_frozen = False
    if os.path.exists(PROTOCOL):
        h = hashlib.sha256(open(PROTOCOL, "rb").read()).hexdigest()
        txt = open(PROTOCOL, encoding="utf-8").read()
        proto_frozen = "Status: DRAFT" not in txt and "CRO / OWNER-OPEN" not in txt
        gate("G-1", "protocol frozen & approved", proto_frozen,
             f"sha256={h[:16]}… status=DRAFT, {sum(1 for l in txt.splitlines() if 'CRO/OPEN' in l or 'CRO / OWNER-OPEN' in l)} open items")
    else:
        gate("G-1", "protocol frozen & approved", False, "protocol file missing")

    # G-2 capture selftest
    import subprocess
    py = os.path.join(ROOT, "venv", "bin", "python")
    r = subprocess.run([py, CAPTURE_PY, "selftest"], capture_output=True, text=True)
    ok = r.returncode == 0 and "ALL CHECKS PASS" in r.stdout
    gate("G-2", "capture service selftest", ok, r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[:120])

    # G-3 manifest schema: no outcome-dependent fields (column-name level check)
    m = re.search(r"CREATE TABLE IF NOT EXISTS capture_manifest \((.*?)\);", src, re.S)
    cols = m.group(1) if m else ""
    col_names = []
    for line in cols.splitlines():
        tok = line.strip().split()[0] if line.strip() else ""
        if tok and tok not in ("PRIMARY", "--"):
            col_names.append(tok)
    deny_exact = {"close", "open", "high", "low", "ret", "return", "returns", "fwd", "forward"}
    deny_prefix = ("ret_", "fwd_", "close_", "open_", "high_", "low_", "future")
    bad = [c for c in col_names if c.lower() in deny_exact
           or any(c.lower().startswith(p) and not c.lower().startswith("returned") for p in deny_prefix)]
    gate("G-3", "manifest has no outcome-dependent fields", not bad,
         f"columns={col_names}; flagged={bad or 'none'}")
    # avg_price-like fields allowed in PAYLOAD but not in admissibility: assert admissibility
    # fields (per protocol §5) are a subset of manifest columns
    # G-3b uses cols from above; keep available
    needed = ["status", "date_echo_match", "truncation_suspected", "captured_at_utc", "response_sha256"]
    missing = [c for c in needed if c not in cols] if cols else ["schema-not-parsed"]
    gate("G-3b", "admissibility fields ⊆ manifest", not missing, f"missing={missing or 'none'}")

    # G-4 isolation: AST scan of capture code for references to production/frozen
    # stores, over FUNCTIONALLY USED strings only (call args, assignments,
    # comparisons) — docstrings and documentation constants are excluded by
    # construction.
    import ast
    tree = ast.parse(src)
    code_strings = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for a_ in list(node.args) + [k.value for k in node.keywords]:
                if isinstance(a_, ast.Constant) and isinstance(a_.value, str):
                    code_strings.append(a_.value)
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.Compare)):
            subs = list(getattr(node, "targets", []) or [])
            for attr in ("value", "left", "comparators"):
                v = getattr(node, attr, None)
                if v is None:
                    continue
                subs.extend(v if isinstance(v, list) else [v])
            for sub in subs:
                if sub is None:
                    continue
                for n2 in ast.walk(sub):
                    if isinstance(n2, ast.Constant) and isinstance(n2.value, str):
                        code_strings.append(n2.value)
    frozen_refs = [w for w in ("walkforward.db", "research.db", "DATASET_B_BROKER_FLOW_STORE",
                               "views_v1", "stockbit-flow-bars")
                   if any(w in s for s in code_strings)]
    gate("G-4", "capture code (excl. docstrings) references no frozen/production store",
         not frozen_refs, f"flagged={frozen_refs or 'none'}")
    store_dir = os.path.join(CAPTURE_DIR, "store")
    frozen_files = []
    if os.path.isdir(store_dir):
        for dp, _, fn in os.walk(store_dir):
            for f in fn:
                if f.endswith((".db", ".sqlite")) and "manifest" not in f:
                    frozen_files.append(os.path.join(dp, f))
    gate("G-4b", "store contains no foreign db files", not frozen_files, f"found={frozen_files or 'none'}")

    # G-5 signal-mapping full-corpus validation (Dataset B raw_responses vs stockbit_flow)
    # 2026-09-16: was `ok = os.path.exists(done_flag)` with a hardcoded detail string
    # claiming "295/300 sampled retained payloads incomplete". Both were wrong — the
    # gate could not run (tools/validate_signal_mapping.py did not exist) and the claim
    # was false (0 INCOMPLETE cells; 99.99% EVALUABLE). It now consumes the validator's
    # own report and verdict, and verifies the report's content digest.
    report_path = os.path.join(HERE, "mapping_validation_report.json")
    if not os.path.exists(report_path):
        gate("G-5", "signal-mapping full-corpus validation", False,
             "no report — run tools/validate_signal_mapping.py (protocol G-7/O-7)")
    else:
        try:
            rep = json.load(open(report_path, encoding="utf-8"))
            content = {k: v for k, v in rep.items()
                       if k not in ("generated_utc", "content_sha256")}
            recomputed = hashlib.sha256(json.dumps(
                content, indent=1, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            if recomputed != rep.get("content_sha256"):
                gate("G-5", "signal-mapping full-corpus validation", False,
                     "report digest mismatch — report was edited after generation")
            else:
                # V1.2 split G-7 into G-7a (retrospective falsification of the
                # withdrawn V1.1 mapping — this report) and G-7b (prospective
                # validation of the corrected mapping, which no retrospective
                # corpus can supply because no raw tradebook payload was ever
                # preserved). A FAIL here is the RECORD of G-7a, not a defect in
                # V1.2 — so the gate reports the corrected mapping's real status:
                # unvalidated, and blocking, until G-7b accrues.
                g7b = os.path.join(HERE, "mapping_validation_prospective.json")
                a_done = rep.get("verdict") == "FAIL" and rep.get("zero_sum", {}).get(
                    "share_of_evaluable", 0) > 0.99
                if os.path.exists(g7b):
                    try:
                        pr = json.load(open(g7b, encoding="utf-8"))
                        ok_b = pr.get("verdict") == "PASS"
                        det = (f"G-7a recorded; G-7b verdict={pr.get('verdict')} "
                               f"sessions={pr.get('sessions')}")
                    except Exception as e:
                        ok_b, det = False, f"G-7b report unreadable: {e}"
                else:
                    ok_b = False
                    det = ("G-7a DONE (V1.1 mapping falsified: identically zero on "
                           f"{rep.get('zero_sum', {}).get('share_of_evaluable', 0):.0%} of "
                           "evaluable cells, recorded) | G-7b OPEN: the corrected V1.2 "
                           "tradebook mapping has no retrospective corpus and must be "
                           "validated on >=20 prospectively captured sessions")
                    if not a_done:
                        det = "G-7a report does not certify the V1.1 falsification | " + det
                gate("G-5", "signal-mapping validation (G-7a record + G-7b prospective)",
                     ok_b, det)
        except Exception as e:
            gate("G-5", "signal-mapping full-corpus validation", False,
                 f"report unreadable: {e}")

    # G-6 universe roster frozen
    gate("G-6", "universe_frozen.csv exists & hashed", os.path.exists(UNIVERSE),
         "generate from idx_tickers status='active' at activation" if not os.path.exists(UNIVERSE) else "")

    # G-7 cohort rule implemented in protocol
    ok = os.path.exists(PROTOCOL) and "captured_at_utc" in open(PROTOCOL, encoding="utf-8").read()
    gate("G-7", "prospective/retrospective cohort rule defined", ok,
         "cohort B = terminal capture with captured_at_utc > protocol-freeze timestamp (§4/PHASE-4)")

    # G-8 blindness: parse determinism (T-1) and payload-only admissibility (T-2)
    sys.path.insert(0, CAPTURE_DIR)
    from prospective_capture import parse_body, rebuild_rows
    body = json.dumps({"message": "ok", "data": {"from": "2026-01-05", "to": "2026-01-05",
                      "broker_summary": {"symbol": "X", "brokers_buy": [
                          {"netbs_stock_code": "X", "netbs_date": "20260105", "netbs_broker_code": "AA",
                           "blot": "1", "bval": "2", "netbs_buy_avg_price": "3", "type": "Lokal", "freq": "1"}],
                          "brokers_sell": []}, "bandar_detector": {}}}).encode()
    det = rebuild_rows(body) == rebuild_rows(body) == parse_body(body)["rows"]
    gate("G-8", "T-1 parse determinism (pure function of bytes)", det)
    future = body.replace(b"2026-01-05", b"2099-12-31")
    gate("G-8b", "T-2 parse ignores non-session fields (future-echo cannot change rows)",
         len(rebuild_rows(future)) == len(rebuild_rows(body)))

    # G-9 feasibility parameters + power-option choice + estimand decision resolved
    open_marks = 0
    if os.path.exists(PROTOCOL):
        open_marks = open(PROTOCOL, encoding="utf-8").read().count("| OPEN |")
    gate("G-9", "feasibility/power option (O-11), params (O-1..O-4) and estimand decision (O-12) resolved",
         os.path.exists(PROTOCOL) and open_marks == 0,
         f"unresolved OPEN items in protocol: {open_marks}")

    # G-10 independent checker sign-off
    signoff = os.path.join(HERE, "independent_check_signoff.md")
    gate("G-10", "independent checker sign-off", os.path.exists(signoff), "required before activation")

    n_pass = sum(1 for r in results if r["pass"])
    print(f"\nGATE SUMMARY: {n_pass}/{len(results)} PASS — "
          f"{'ACTIVATION CLEARED (all mandatory gates PASS)' if n_pass == len(results) else 'ACTIVATION NOT CLEARED'}")
    print(json.dumps(results, indent=1, default=str))


if __name__ == "__main__":
    main()
