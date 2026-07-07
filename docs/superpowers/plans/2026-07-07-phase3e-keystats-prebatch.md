# Phase 3E — Keystats Refetch Out of the Scan Loop (item 3.6) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the synchronous Stockbit keystats network refetch out of the per-ticker scan loop into a bounded pre-scan batch pass, so the hot loop's fundamental gate is read-only (no blocking network call interleaved with flow fetch + strategy eval).

**Architecture:** `check_keystats_freshness(ticker, df)` (scanner.py:101) currently, on a *stale + price-shock* ticker, calls `fetch_keystats()` over the network **inside** `scan_momentum_signals`' main `for ticker in tickers` loop (line 310 → 150). Audit H-18. Fix without changing the block/allow policy: add an `allow_refetch` flag — the gate keeps its exact behavior when `True` (default; all existing callers/tests unchanged), and when `False` it makes the *same decision* but returns a block instead of hitting the network. A new `_batch_refresh_stale_keystats(tickers, ohlcv_map, ...)` runs one refetch pass **before** the loop (calling the gate with `allow_refetch=True`), populating the DB; the in-loop call then uses `allow_refetch=False` and reads the freshly-populated rows. Net: identical gating outcomes, but every network call happens in one pre-pass, never mid-scan.

**Tech Stack:** Python 3 stdlib, existing `stockbit_fetcher.fetch_keystats/save_keystats`, `data.db.connect`, pytest + `unittest.mock`.

---

## File Structure

- **Modify** `scheduler/scanner.py` — add `allow_refetch` param to `check_keystats_freshness`; add `_batch_refresh_stale_keystats`; call the batch before the loop and switch the in-loop call to `allow_refetch=False`.
- **Modify** `tests/test_fundamental_refresh.py` — add tests for the `allow_refetch=False` path and the batch pre-pass (existing 7 tests stay untouched and must keep passing).

**Behavior contract for `allow_refetch=False`:** identical to `True` for every case *except* stale+shock — where instead of attempting the network fetch it returns `(False, 'stale_shock:{N}d,not_refreshed')`. (Fresh → OK; stale+no-shock → allow; no_data/db_error/bad_date unchanged.)

---

### Task 1: `allow_refetch` flag on the gate

**Files:**
- Modify: `scheduler/scanner.py:101-164` (`check_keystats_freshness`)
- Test: `tests/test_fundamental_refresh.py`

- [ ] **Step 1: Write the failing tests** (append to `TestCheckKeystatsFreshness`)

```python
    def test_allow_refetch_false_blocks_without_network(self, tmp_path):
        """Stale+shock with allow_refetch=False returns a block and never
        touches the network (the batch pre-pass owns refetching)."""
        old = (date.today() - timedelta(days=45)).isoformat()
        db = _make_keystats_db(tmp_path, old)
        tf = tmp_path / ".stockbit_token"
        tf.write_text("eyJmYWtlLnRva2Vu.payload.sig")
        with patch("stockbit_fetcher.fetch_keystats",
                   side_effect=AssertionError("must not fetch in-loop")):
            ok, reason = check_keystats_freshness(
                "BRPT", _shock_df(), _db_path=db, _token_file=str(tf),
                allow_refetch=False,
            )
        assert ok is False
        assert "stale_shock" in reason
        assert "not_refreshed" in reason

    def test_allow_refetch_false_still_allows_fresh(self, tmp_path):
        db = _make_keystats_db(tmp_path, date.today().isoformat())
        ok, reason = check_keystats_freshness(
            "BRPT", _flat_df(), _db_path=db, allow_refetch=False,
        )
        assert ok is True
        assert reason == "OK"

    def test_allow_refetch_false_stale_no_shock_allows(self, tmp_path):
        old = (date.today() - timedelta(days=45)).isoformat()
        db = _make_keystats_db(tmp_path, old)
        ok, reason = check_keystats_freshness(
            "BRPT", _flat_df(), _db_path=db, allow_refetch=False,
        )
        assert ok is True
        assert reason.startswith("stale:")
```

- [ ] **Step 2: Run to verify failure**

Run: `./venv/bin/python -m pytest tests/test_fundamental_refresh.py -q`
Expected: FAIL — `TypeError: check_keystats_freshness() got an unexpected keyword argument 'allow_refetch'`

- [ ] **Step 3: Add the param** in `scheduler/scanner.py`

Change the signature:

```python
def check_keystats_freshness(ticker: str, df, stale_threshold: int = 30,
                             _db_path: str = None, _token_file: str = None,
                             allow_refetch: bool = True):
```

And guard the refetch block — replace the line `    # Stale + price shock — attempt re-fetch` and the token fetch that follows so that, when `allow_refetch` is False, it short-circuits before any network:

```python
    # Stale + price shock — attempt re-fetch (unless the batch pre-pass owns it)
    if not allow_refetch:
        return False, f'stale_shock:{stale_days}d,not_refreshed'

    token = _load_stockbit_token(_token_file)
```

(Everything else in the function is unchanged.)

- [ ] **Step 4: Run to verify pass (new + all 7 originals)**

Run: `./venv/bin/python -m pytest tests/test_fundamental_refresh.py -q`
Expected: PASS (10 passed)

- [ ] **Step 5: Commit**

```bash
git add scheduler/scanner.py tests/test_fundamental_refresh.py
git commit -m "feat(scan): allow_refetch flag on keystats gate (read-only mode) (Phase 3E)"
```

---

### Task 2: Pre-scan batch pass + read-only in-loop gate

**Files:**
- Modify: `scheduler/scanner.py` (add `_batch_refresh_stale_keystats`; call before loop; switch in-loop call)
- Test: `tests/test_fundamental_refresh.py`

- [ ] **Step 1: Write the failing test** (new class in the same file)

```python
class TestBatchRefreshStaleKeystats:
    def test_batch_refetches_only_stale_shock_tickers(self, tmp_path):
        """The pre-pass fetches for a stale+shock ticker and skips a fresh one."""
        from scheduler.scanner import _batch_refresh_stale_keystats
        old = (date.today() - timedelta(days=45)).isoformat()
        db = _make_keystats_db(tmp_path, old)            # BRPT stale
        # add a fresh ticker row
        with sqlite3.connect(db) as c:
            c.execute("INSERT INTO stockbit_keystats (ticker, fetch_date, pe_ttm, pbv, roe) "
                      "VALUES ('BBCA', ?, 10, 2, 15)", (date.today().isoformat(),))
        tf = tmp_path / ".stockbit_token"
        tf.write_text("eyJmYWtlLnRva2Vu.payload.sig")
        ohlcv = {"BRPT": _shock_df(), "BBCA": _flat_df()}
        stats = {"ticker": "BRPT", "pe_ttm": 8.0, "roe": 12.0, "pbv": 2.0}
        with patch("stockbit_fetcher.fetch_keystats", return_value=stats) as mf, \
             patch("stockbit_fetcher.save_keystats", return_value=None):
            _batch_refresh_stale_keystats(["BRPT", "BBCA"], ohlcv,
                                          _db_path=db, _token_file=str(tf))
        mf.assert_called_once_with("eyJmYWtlLnRva2Vu.payload.sig", "BRPT")

    def test_batch_swallows_errors_per_ticker(self, tmp_path):
        """A fetch error for one ticker must not abort the whole pre-pass."""
        from scheduler.scanner import _batch_refresh_stale_keystats
        old = (date.today() - timedelta(days=45)).isoformat()
        db = _make_keystats_db(tmp_path, old)
        tf = tmp_path / ".stockbit_token"
        tf.write_text("eyJmYWtlLnRva2Vu.payload.sig")
        with patch("stockbit_fetcher.fetch_keystats", side_effect=Exception("timeout")):
            # must not raise
            _batch_refresh_stale_keystats(["BRPT"], {"BRPT": _shock_df()},
                                          _db_path=db, _token_file=str(tf))
```

(Ensure `import sqlite3` is present at the top of the test module — it already imports it; if not, add it.)

- [ ] **Step 2: Run to verify failure**

Run: `./venv/bin/python -m pytest tests/test_fundamental_refresh.py::TestBatchRefreshStaleKeystats -q`
Expected: FAIL — `ImportError: cannot import name '_batch_refresh_stale_keystats'`

- [ ] **Step 3: Implement the batch fn** in `scheduler/scanner.py` (directly after `check_keystats_freshness`)

```python
def _batch_refresh_stale_keystats(tickers, ohlcv_map, _db_path=None,
                                  _token_file=None):
    """Pre-scan pass: refetch keystats for stale+shock tickers up front so the
    per-ticker gate in the scan loop stays read-only (audit item 3.6, H-18).

    Reuses check_keystats_freshness(allow_refetch=True) purely for its refetch
    side effect; per-ticker errors are swallowed so one bad fetch can't abort
    the pass.
    """
    refreshed = 0
    for ticker in tickers:
        try:
            ok, reason = check_keystats_freshness(
                ticker, ohlcv_map.get(ticker), _db_path=_db_path,
                _token_file=_token_file, allow_refetch=True,
            )
            if reason.startswith("refreshed:"):
                refreshed += 1
        except Exception as _e:
            logging.warning(f"[keystats-batch] {ticker} refresh error: {_e}")
    if refreshed:
        logging.info(f"[keystats-batch] refreshed {refreshed} stale+shock tickers pre-scan")
    return refreshed
```

- [ ] **Step 4: Wire it in** `scan_momentum_signals`

Just before the `for ticker in tickers:` loop (scanner.py:303), add — gated on the same fundamental flag so it's a no-op when fundamentals are off:

```python
    if _f_fundamental:
        _batch_refresh_stale_keystats(tickers, ohlcv_map)
```

And change the in-loop call (scanner.py:310) to read-only:

```python
            freshness_ok, fresh_reason = check_keystats_freshness(
                ticker, df, allow_refetch=False)
```

- [ ] **Step 5: Run tests**

Run: `./venv/bin/python -m pytest tests/test_fundamental_refresh.py -q`
Expected: PASS (12 passed)

- [ ] **Step 6: Commit**

```bash
git add scheduler/scanner.py tests/test_fundamental_refresh.py
git commit -m "feat(scan): pre-scan keystats batch; in-loop gate is read-only (Phase 3E, closes 3.6)"
```

---

### Task 3: Full-suite regression + finish

- [ ] **Step 1: Full suite**

Run: `./venv/bin/python -m pytest -q`
Expected: ≥1065 passed + the new tests (≈1070), 3 skipped, no new failures. (Run alongside `tests/agent_firm/` if `test_scheduler_firm_hook.py` is in the selection — known import-order quirk, unrelated.)

- [ ] **Step 2: Finish the branch**

Use **superpowers:finishing-a-development-branch**: push, PR to `master`, wait CI, manual merge, merge master into prod branch `feat/tfb-context-filter`, restart app in a quiet slot. NOTE: this deploy can be batched with the pending Phase 3D heartbeat restart — one restart picks up both.

PR body: closes audit 3.6/H-18; identical gating outcomes, network refetch moved to a single pre-scan pass; `allow_refetch=True` default keeps all existing callers/tests intact.

---

## Self-Review Notes

- **Spec coverage:** 3.6 "move keystats network refetch out of the scan loop into a pre-scan batch" = Task 2 exactly; policy-preserving by construction (`allow_refetch` default True).
- **Placeholder scan:** all code literal; the only judgement call (batch fetches per stale ticker, not deduped/parallelised) is intentional YAGNI — the win is *location*, not concurrency.
- **Type consistency:** `check_keystats_freshness(..., allow_refetch: bool = True)` and `_batch_refresh_stale_keystats(tickers, ohlcv_map, _db_path=None, _token_file=None) -> int` used consistently in impl + tests + call site.
- **Regression safety:** the 7 original `test_fundamental_refresh` tests call with the default → unchanged behavior; the in-loop switch to `allow_refetch=False` is covered by the new block-without-network test.
