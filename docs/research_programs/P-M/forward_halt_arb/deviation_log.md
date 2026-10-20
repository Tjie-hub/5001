# FWD-PM-HALTARB-001 — deviation log

Append-only. Never rewritten. Every entry is dated and states what changed, why, and whether any outcome was
visible at the time.

---

## DEV-001 · 2026-10-20 · the ARB floor follows the exchange rule in force on the session

**Authority.** DECISION_LOG D-107. Owner instruction 2026-10-20: "complete 7% ARB".

**What changed.** `run_recorder.py` `arb_price(prev_close, session)`:
- On sessions 2026-10-19 → 2026-12-31 the floor is 7% below the previous close, rounded up to the tick.
- Other sessions keep 15%. The tick rounding is unchanged.
- The call site passes the event day.

Test: `tests/test_forward_halt_arb.py::test_arb_price_follows_the_7pct_rule_on_its_sessions`; the fixture
expectation moved from 850 to 930 because its dates fall in the 7% window. `SHA256SUMS.txt` is updated for
`run_recorder.py`: `abf6d629…` → `1349121b…` (PROTOCOL.md unchanged).

**Why.**
- BEI cut the ARB to 7% for 2026-10-19 → 2026-12-31: SK Direksi Kep-00157/BEI/10-2026, then Kep-00158 (Rp 11–14
  names fall Rp 1; irrelevant here, since the price floor is Rp 50).
- PROTOCOL §2 defines the touch against "the ARB in force"; 15% was its value when frozen.
- With a fixed 15%, a halt day under the 7% rule would record only names that fell through a floor that no longer
  exists, which is none on the regular boards.

**Was any outcome visible?** No. `ledger.json` holds 0 event days and 0 rows (sha256 `6718a6e4…`). Checking the
rule used only 2026-10-19 lows against previous closes (TOWR 388 → 362, exactly the 7% floor); no forward
return was computed.

**What did NOT change.**
- The halt threshold (IHSG low ≤ −8%), ADV and price floors, H = 5, the contamination void, the exclusion of
  2026-10-16, the outcome fields, and the 20-event-day read gate.
