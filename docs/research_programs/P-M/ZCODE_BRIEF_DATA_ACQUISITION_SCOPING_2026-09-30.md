# ZCODE BRIEF — P-M data-acquisition scoping (D-c backlog from the 2026-09-29 broad-search handoff)

**Issued:** 2026-09-30, by Claude (planner role, Owner's request) · **Branch:**
`docs/p-m-data-acquisition-scoping` · **Repo:** `D:\IDX` (WSL mirror) ·
**Output dir (the only place you write):** `docs/research_programs/P-M/data_acquisition/`

**Authority:** scoping/feasibility only, same restriction as the broad-search brief before it —
you may not register a hypothesis, open a forward test, consume a family slot, or edit
`DECISION_LOG.md`, `HYPOTHESIS_REGISTRY.md`, `FAILURE_REGISTRY.md`, or any frozen protocol. This
brief produces feasibility memos, not data pipelines — see §2 for why.

**Priority: low.** Nothing here is time-sensitive. Do this after the P0/P1/P3/P4 briefs, or in
whatever idle time you have — it's queued backlog, not active blocking work.

---

## 0. Where this comes from

`docs/research_programs/P-M/broad_search/HANDOFF_BROAD_SEARCH_2026-09-29.md` §1 (D-c) listed five
data-acquisition items in priority order, none started as of today:

1. **Private placements (PMTHMETD)** — the missing half of the `{CF}` corporate-finance-events
   family (rights issues/warrants/tenders are covered; private placements aren't).
2. **Suspension/UMA announcements with PIT dates** — `{TS}` trading-status family; the existing
   `suspension_events` table (3,189 rows) is detector-derived, not sourced from dated disclosures,
   and only covers 2022+.
3. **Lock-up expiry calendar** — `{LC}` listing-lifecycle family's supply-shock event (distinct from
   the IPO date itself, which is already proxied from `ohlcv_long`'s first bar).
4. **Cross-asset series** — TLK ADR (overnight US), USD/IDR, coal/CPO proxies, for the `{X}` family.
5. **`news_mentions` history extension** — currently 2026-04 onward only (~5 months); a forward
   attention recorder proposal, not a screen (underpowered by construction until ~2027-04).

## 1. What "done" looks like for this brief — five short memos, not five data pipelines

For **each** of the five items, write one file under
`docs/research_programs/P-M/data_acquisition/<ITEM>_FEASIBILITY_2026-09-30.md` answering:

- **Source(s) that could plausibly provide this**, ranked by how confident you are they'd work —
  e.g. IDX's own disclosure system (`idx.co.id`), KSEI, a paid vendor Tjie may already have
  Stockbit-adjacent access to, yfinance/other free APIs, or "no known source, would need manual
  entry."
- **What credentials/access this needs that you do or don't currently have** in this environment.
  Check `.env` / `.env.example` for anything already provisioned before assuming there's nothing.
  If a source needs a login or paid subscription you don't have, say so plainly rather than
  attempting a scrape that might violate a site's terms — flag it back to the Owner instead.
  **Do not attempt IDX/KSEI login flows, CAPTCHA bypass, or scraping behind auth you don't already
  have credentials for.** That decision is the Owner's, not yours.
- **If a free/scriptable path exists** (e.g. yfinance for TLK ADR / USD-IDR / coal-CPO — item 4 is
  the one most likely to have one): write a small proof-of-concept fetch script, run it once, and
  report what you actually got (date range, gaps, PIT-ness of the timestamps) — but do not wire it
  into the research pipeline or backfill anything yet. That's a second, separate brief once the
  Owner picks which item(s) to actually pursue.
- **Rough effort estimate** if the Owner decides to pursue it for real (hours, not a guess dressed
  up as precision).

## 2. Why scoping-only, not "just go build it"

Three of these five (items 1–3) likely require point-in-time disclosure data that either doesn't
exist in a free/scriptable form for IDX, or requires manual sourcing/paid access — building a
"backfill pipeline" for a data source that turns out not to exist would waste a work cycle. Item 4
is the one genuinely likely to be quick (public market data). Item 5 isn't actionable until
2027-04 regardless of tooling. Scope first; the Owner picks priority from real feasibility
findings, not from the handoff's a-priori ranking.

## 3. Also queued, lower priority still — do not action, just note

`HANDOFF_BROAD_SEARCH_2026-09-29.md` §1 D-b: a proposed standing guard where the FADE-001/
VOLEX-001/REGIME-002 recorders would censor/flag any holding window spanning a rights/bonus/
reverse-split ex-date (the detection-only version, `scripts/check_issuance_windows.py`, already
shipped in D-064 — this is about going further and actually changing frozen recorder behavior).
Explicitly marked **zero urgency** by the brief that raised it. Leave it exactly where it is; just
confirm in your handoff note that you didn't touch it.

## 4. Deliverables

Five feasibility memos under `docs/research_programs/P-M/data_acquisition/`, one proof-of-concept
script + sample output for whichever item(s) turn out to be free/scriptable (most likely item 4),
and a one-paragraph ranked recommendation for the Owner on which item(s) are worth a real
acquisition brief next.
