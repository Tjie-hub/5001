"""Playwright smoke test for /dive/<TICKER> strategy modularization.

Loads the dive page, exercises each strategy via the dropdown across all 3
timeframes, captures console output, counts markers, and saves screenshots.

Run:
    python3 scripts/smoketest_dive.py
Output:
    out/dive_smoketest.md
    out/dive_smoketest_*.png
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import ConsoleMessage, Page, sync_playwright

BASE = "http://127.0.0.1:5001"
TICKER = "BRPT"
TF_BUTTONS = [("tf-1h", "1H"), ("tf-1d", "1D"), ("tf-1w", "1W")]


def fetch_strategy_keys() -> list[str]:
    """Pull the canonical strategy list from the running server."""
    with urllib.request.urlopen(f"{BASE}/api/strategy/list", timeout=10) as resp:
        data = json.loads(resp.read().decode())
    return [s["key"] for s in data.get("strategies", [])]
OUT = Path("out")
OUT.mkdir(exist_ok=True)


FETCH_COUNTER_SCRIPT = """
window.__ohlcvFetches = 0;
const _origFetch = window.fetch.bind(window);
window.fetch = async function(...args) {
    const url = (typeof args[0] === 'string') ? args[0] : (args[0] && args[0].url) || '';
    const resp = await _origFetch(...args);
    if (url.includes('/ohlcv')) {
        try {
            const cloned = resp.clone();
            cloned.json().finally(() => { window.__ohlcvFetches += 1; });
        } catch(e) {
            window.__ohlcvFetches += 1;
        }
    }
    return resp;
};
"""


def wait_chart_ready(page: Page, timeout_ms: int = 15000) -> None:
    """Wait until initial _rawCandles+_candleSeries are populated."""
    page.wait_for_function(
        "() => Array.isArray(_rawCandles) && _rawCandles.length > 0 && _candleSeries !== null",
        timeout=timeout_ms,
    )


def wait_next_ohlcv(page: Page, prev_count: int, timeout_ms: int = 15000) -> int:
    """Wait until __ohlcvFetches has incremented past prev_count, return new count."""
    page.wait_for_function(
        f"() => (window.__ohlcvFetches || 0) > {prev_count}",
        timeout=timeout_ms,
    )
    # Settle: give setData + setMarkers a beat to apply
    page.wait_for_timeout(300)
    return page.evaluate("() => window.__ohlcvFetches || 0")


def select_strategy(page: Page, key: str) -> dict:
    """Select strategy, wait briefly for run, capture count + active state."""
    page.select_option("#strat-select", key)
    page.wait_for_timeout(150)
    count_text = page.locator("#strat-count").inner_text() if page.locator("#strat-count").is_visible() else "(hidden)"
    active = page.evaluate("() => _activeStrategy")
    return {"key": key, "active": active, "count_text": count_text}


def switch_tf(page: Page, tf_id: str, prev_fetches: int) -> int:
    page.click(f"#{tf_id}")
    return wait_next_ohlcv(page, prev_fetches)


def main() -> int:
    report_lines: list[str] = []
    console_log: list[str] = []
    console_errors: list[str] = []

    try:
        strategies = fetch_strategy_keys()
    except Exception as e:
        print(f"FATAL: could not load /api/strategy/list: {e}", file=sys.stderr)
        return 2
    if not strategies:
        print("FATAL: /api/strategy/list returned 0 strategies", file=sys.stderr)
        return 2

    def on_console(msg: ConsoleMessage) -> None:
        line = f"[{msg.type}] {msg.text}"
        console_log.append(line)
        if msg.type == "error":
            console_errors.append(line)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        ctx.add_init_script(FETCH_COUNTER_SCRIPT)
        page = ctx.new_page()
        page.on("console", on_console)
        page.on("pageerror", lambda exc: console_errors.append(f"[pageerror] {exc}"))

        url = f"{BASE}/dive/{TICKER}"
        report_lines.append(f"# Dive.html Smoke Test — {TICKER}")
        report_lines.append("")
        report_lines.append(f"**URL:** `{url}`  ")
        report_lines.append(f"**Browser:** Chromium headless ({browser.version})  ")
        report_lines.append(f"**Run:** {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")

        resp = page.goto(url, wait_until="domcontentloaded")
        report_lines.append(f"**HTTP:** {resp.status if resp else 'n/a'}  ")

        wait_chart_ready(page)
        page.wait_for_function("() => (window.__ohlcvFetches || 0) >= 1", timeout=15000)
        fetch_count = page.evaluate("() => window.__ohlcvFetches || 0")
        n_candles = page.evaluate("() => _rawCandles.length")
        report_lines.append(f"**Candles loaded (1D default):** {n_candles}")
        report_lines.append("")

        # Dropdown is populated async from /api/strategy/list — wait for options
        page.wait_for_function(
            f"() => document.querySelectorAll('#strat-select option').length >= {len(strategies) + 1}",
            timeout=10000,
        )

        # ── Test 1: Each strategy on default 1D timeframe ───────────────────
        report_lines.append(f"## Test 1 — Each strategy on 1D ({len(strategies)} strategies)")
        report_lines.append("")
        report_lines.append("| Strategy | Active state | Marker count badge |")
        report_lines.append("|---|---|---|")
        t1_results = []
        for strat in strategies:
            r = select_strategy(page, strat)
            # Markers fetched async — give the network call a beat to settle
            page.wait_for_timeout(400)
            r["count_text"] = (
                page.locator("#strat-count").inner_text()
                if page.locator("#strat-count").is_visible()
                else "(hidden)"
            )
            t1_results.append(r)
            report_lines.append(f"| {r['key']} | `{r['active']}` | {r['count_text']} |")
            safe_name = strat.replace(" ", "_").replace("/", "_")
            page.screenshot(path=str(OUT / f"dive_smoketest_1D_{safe_name}.png"), clip={"x": 0, "y": 0, "width": 1440, "height": 600})

        # ── Test 2: Clear via empty option ──────────────────────────────────
        report_lines.append("")
        report_lines.append("## Test 2 — Clear strategy (empty selection)")
        page.select_option("#strat-select", "")
        page.wait_for_timeout(150)
        active = page.evaluate("() => _activeStrategy")
        count_visible = page.locator("#strat-count").is_visible()
        report_lines.append(f"- After empty select → `_activeStrategy='{active}'`, count badge visible: {count_visible}")
        report_lines.append(f"- Expected: empty string + hidden badge")

        # ── Test 3: Auto-rerun on TF switch ─────────────────────────────────
        report_lines.append("")
        report_lines.append("## Test 3 — Auto-rerun on timeframe switch")
        report_lines.append("")
        # Set active strategy first
        tf_strategy = "conservative" if "conservative" in strategies else strategies[0]
        select_strategy(page, tf_strategy)
        page.wait_for_timeout(400)
        report_lines.append(f"Set active strategy: {tf_strategy}")
        report_lines.append("")
        report_lines.append("| TF | Candles | Active after switch | Marker count |")
        report_lines.append("|---|---:|---|---|")
        for tf_id, label in TF_BUTTONS:
            fetch_count = switch_tf(page, tf_id, fetch_count)
            n = page.evaluate("() => _rawCandles.length")
            active = page.evaluate("() => _activeStrategy")
            count = page.locator("#strat-count").inner_text() if page.locator("#strat-count").is_visible() else "(hidden)"
            report_lines.append(f"| {label} | {n} | `{active}` | {count} |")
            page.screenshot(path=str(OUT / f"dive_smoketest_TF_{label}.png"), clip={"x": 0, "y": 0, "width": 1440, "height": 600})

        # ── Console output summary ──────────────────────────────────────────
        report_lines.append("")
        report_lines.append("## Console output")
        report_lines.append("")
        report_lines.append(f"- Total console messages: {len(console_log)}")
        report_lines.append(f"- Errors / page errors: **{len(console_errors)}**")
        strategy_logs = [line for line in console_log if "[Strategy]" in line]
        report_lines.append(f"- `[Strategy]` log lines: {len(strategy_logs)}")
        if strategy_logs:
            report_lines.append("")
            report_lines.append("Strategy log entries:")
            report_lines.append("```")
            report_lines.extend(strategy_logs[:40])
            report_lines.append("```")
        if console_errors:
            report_lines.append("")
            report_lines.append("**Errors:**")
            report_lines.append("```")
            report_lines.extend(console_errors[:20])
            report_lines.append("```")

        # ── Final verdict ────────────────────────────────────────────────────
        report_lines.append("")
        report_lines.append("## Verdict")
        report_lines.append("")
        all_strategies_ran = all(r["active"] == r["key"] for r in t1_results)
        no_errors = len(console_errors) == 0
        verdict = "✅ PASS" if (all_strategies_ran and no_errors) else "❌ FAIL"
        report_lines.append(f"**{verdict}**")
        report_lines.append("")
        report_lines.append(f"- All {len(strategies)} strategies set _activeStrategy correctly: {all_strategies_ran}")
        report_lines.append(f"- Zero console errors: {no_errors}")

        browser.close()

    report = "\n".join(report_lines) + "\n"
    out_path = OUT / "dive_smoketest.md"
    out_path.write_text(report)
    print(report)
    print(f"\nReport: {out_path}")
    return 0 if (all_strategies_ran and no_errors) else 1


if __name__ == "__main__":
    sys.exit(main())
