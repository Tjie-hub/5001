"""Rule Card CLI (D-055). Never imported by production.

    python -m research.rulecard.cli validate <CARD.yaml>
    python -m research.rulecard.cli dry      <CARD.yaml>
    python -m research.rulecard.cli power    <CARD.yaml>   # noise floor; never calls signal()
    python -m research.rulecard.cli freeze   <CARD.yaml> --owner "Owner, 2026-09-24, D-055"
    python -m research.rulecard.cli run      <CARD.yaml> [--resume-after-crash]
"""
from __future__ import annotations

import argparse
import json
import sys

from research.rulecard import runner
from research.rulecard.card import CardError


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="research.rulecard.cli")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("validate", "dry", "power", "run", "freeze"):
        p = sub.add_parser(name)
        p.add_argument("card")
        if name == "freeze":
            p.add_argument("--owner", required=True)
        if name == "run":
            p.add_argument("--resume-after-crash", action="store_true")
            p.add_argument("--ledger", default=None)
    a = ap.parse_args(argv)
    try:
        if a.cmd == "validate":
            out = runner.validate(a.card)
        elif a.cmd == "dry":
            out = runner.dry(a.card)
        elif a.cmd == "power":
            out = runner.power(a.card)
        elif a.cmd == "freeze":
            out = runner.freeze(a.card, a.owner)
        else:
            full = runner.run(a.card, a.ledger, a.resume_after_crash)
            out = {"verdict": full["verdict"]["verdict"], "checks":
                   {c["code"]: c["status"] for c in full["checks"]}}
    except (CardError, runner.RefusedError) as e:
        print(str(e), file=sys.stderr)
        return 2
    print(json.dumps(out, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
