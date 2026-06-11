# Unified Watchlist Panel — Design Spec

**Date:** 2026-06-11
**Status:** Approved (pending spec review)
**Scope:** Dashboard on port 5001 (`templates/watchlist.html` + Flask routes)

## Goal

Replace the dashboard's broken "Signals" panel with a single **unified watchlist**
that merges three existing watchlist sources into one ranked, de-duplicated list,
rewarding cross-source agreement (confluence) without enforcing a strict
intersection.

## Background / Why

- The dashboard's Signals panel is fed by `/api/dashboard/signals` →
  `engine.dashboard.get_signals_dashboard()`, which reads the `agent_decisions`
  table. That table does not exist in the live DB (`init_agent_firm_tables()` is
  only ever called by tests), so the panel is effectively empty/broken. (The
  agent-firm repair is tracked separately and is **out of scope** here.)
- The reversal EOD pre-scan we shipped (`reversal_watchlist`, `/api/screener/reversal`)
  is not surfaced anywhere on the dashboard.
- Two other watchlists exist but are siloed: `watchlist_premover` and
  `regime_watchlist`.

A pure **intersection** ("in all sources") is wrong for these inputs: the sources
have different universes (so the intersection is frequently empty) and conflicting
directions (reversal can be SHORT while the others are LONG-biased). A pure
**union** is too noisy (premover alone carries thousands of rows). The chosen
approach is a **weighted union with a confluence boost**: union as the base,
agreement expressed as a ranking bonus + badge, conflicts flagged not merged.

## Sources & Normalization

One row per source-ticker is pulled, each read in its own `try/except` so a
missing or empty source degrades gracefully (skipped, never fails the panel).

| Source | Table | Selection | Strength (0–100) | Direction |
|---|---|---|---|---|
| Reversal EOD | `reversal_watchlist` | `scan_date = :date` | `conviction` (native 0–100) | `direction` (long/short) |
| Premover | `watchlist_premover` | latest `detected_at`, `score >= 55` | `score` (native 0–100) | long |
| Bear dip-scout | `regime_watchlist` | `status IN ('active','promoted')` | base `50`, `+15` if promoted | long |

- Premover `score >= 55` floor cuts the noise at the door.
- Bear dip-scout has no native 0–100 score; the fixed base keeps it comparable
  without over-weighting it.

## Merge Logic

`build_unified_watchlist(db_path, scan_date) -> list[dict]`

1. Collect normalized rows from all three sources.
2. Group by `ticker`.
3. For each ticker group, produce one merged row:
   - `sources`: list of source tags present (e.g. `["REVERSAL", "PREMOVER"]`).
   - `direction`: the **REVERSAL source's direction when present** (it is the only
     validated, directional, broker-confirmed source); otherwise the direction of
     the highest-strength contributing source.
   - `strength`: the strongest source that **agrees with the chosen direction**,
     **+15 confluence bonus** when ≥2 sources agree on that direction (capped 100).
   - `confluence`: `true` when ≥2 sources agree on the shown direction.
   - `conflict`: `true` when at least one source disagrees on direction (opposite
     of the shown direction). Conflicting rows are **flagged**, not strength-merged.
   - `close`: from the reversal row when present; otherwise from any contributing
     source row that carries a close; else `null` (UI renders `—`). In practice
     `reversal_watchlist` is the reliable close source.
   - `detail`: small dict carrying per-source raw values (conviction/score/status,
     `smart_money`/`verdict` when available) for tooltip/expansion.
4. Sort by `strength` desc, then `ticker` asc for stable ordering.

### Output row shape

```json
{
  "ticker": "BRPT",
  "direction": "short",
  "strength": 74.4,
  "sources": ["REVERSAL"],
  "confluence": false,
  "conflict": false,
  "close": 1760,
  "detail": {
    "reversal": {"conviction": 74.4, "smart_money": "MORNING_TRAP", "verdict": "BEARISH"}
  }
}
```

## API

`GET /api/dashboard/unified-watchlist?date=YYYY-MM-DD` (default: today),
added to `routes/flow.py` alongside the other `/api/dashboard/*` endpoints.

- Success: `{ "date": "...", "count": N, "items": [ ...rows... ] }`
- Error: `{ "error": "...", "date": "...", "count": 0, "items": [] }` with HTTP 500
  (mirrors the existing `api_dashboard_watchlist` error contract).

## Frontend (`templates/watchlist.html`)

**Remove (the broken Signals panel):**
- `renderAgentFeed(...)` function and its DOM container.
- The `/api/dashboard/signals` entry in the `Promise.all(...)` load batch (and its
  destructured `signals` variable).
- The signal-count badges block (the "Signals count badges" section).

**Add (Unified Watchlist panel in that slot):**
- A `renderUnifiedWatchlist(d)` function fetching `/api/dashboard/unified-watchlist`.
- Table columns: **rank · ticker · direction (▲ long / ▼ short) · strength ·
  close · sources (badges) · broker** (broker from `detail.reversal.smart_money`
  when present, else `—`).
- Confluence rows visually highlighted; `conflict` rows show a ⚠ badge.
- Empty state: "No watchlist setups for {date}".

The `/api/dashboard/signals` endpoint, `engine.dashboard.get_signals_dashboard`,
and `agent_decisions` code are left untouched (only the panel is removed).

## Error Handling

- Per-source reads wrapped individually; a thrown source is logged and skipped.
- The builder never raises for missing tables; it returns whatever sources
  succeeded (possibly `[]`).
- The API wraps the builder in try/except and returns the documented error shape.
- The frontend renders the empty state on `count == 0` or on fetch error.

## Testing (`tests/test_unified_watchlist.py`)

DB-backed, following `tests/test_reversal_filter.py` / `tests/test_dashboard_*.py`
patterns (temp sqlite seeded with minimal rows):

1. **Single-source passthrough** — one source populated → rows pass through with
   correct strength/direction, no confluence/conflict.
2. **Confluence boost** — same ticker LONG in premover + bear dip-scout → one row,
   `confluence=true`, strength = max + 15 (capped 100).
3. **Conflict flagging** — same ticker SHORT in reversal, LONG in premover → one
   row, `conflict=true`, direction = higher-strength source's, no strength merge.
4. **Premover floor** — premover row with `score < 55` is excluded.
5. **Dedupe** — a ticker in all three sources yields exactly one row.
6. **Resilience** — a missing/empty source table does not raise; builder returns
   the surviving sources.

## Out of Scope (YAGNI)

- Foreign-flow watch (`/api/dashboard/watchlist` BUY-WATCH/AVOID/WAIT) — different
  bucketing, awkward to fold into a 0–100 rank. Can be added later.
- Agent-firm / `agent_decisions` repair — separate task.
- No new DB tables; reads existing `reversal_watchlist`, `watchlist_premover`,
  `regime_watchlist`.
