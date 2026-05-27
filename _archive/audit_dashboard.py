"""Playwright audit of the main IDX Strategy Suite dashboard (/).

Walks every tab, captures console errors, network failures, perf timings,
unused-resource hints, and a screenshot per tab. Emits an upgrade report.

Run:
    python3 scripts/audit_dashboard.py
Output:
    out/dashboard_audit.md
    out/dashboard_audit_<tab>.png
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from playwright.sync_api import ConsoleMessage, Page, Request, Response, sync_playwright

BASE = "http://127.0.0.1:5001"
TABS = [
    ("monitor", "Monitor"),
    ("closed", "Closed Today"),
    ("scanner", "Scanner"),
    ("backtest", "Backtest"),
    ("intraday", "Intraday"),
    ("paper", "Paper Trades"),
    ("brokerflow", "Broker Flow"),
    ("sector", "Sector Rotation"),
    ("calendar", "Calendar"),
]
OUT = Path("out")
OUT.mkdir(exist_ok=True)


def fmt_kb(n: int) -> str:
    return f"{n/1024:.1f} KB" if n < 1024 * 1024 else f"{n/1024/1024:.2f} MB"


def main() -> int:
    console_log: list[str] = []
    console_errors: list[str] = []
    page_errors: list[str] = []
    failed_requests: list[tuple[str, str]] = []
    requests_seen: list[dict] = []
    nav_timings: dict = {}

    def on_console(msg: ConsoleMessage) -> None:
        line = f"[{msg.type}] {msg.text}"
        console_log.append(line)
        if msg.type == "error":
            console_errors.append(line)

    def on_request_failed(req: Request) -> None:
        failed_requests.append((req.url, req.failure or "unknown"))

    def on_response(resp: Response) -> None:
        try:
            size = int(resp.headers.get("content-length", "0") or 0)
        except ValueError:
            size = 0
        requests_seen.append({
            "url": resp.url,
            "status": resp.status,
            "ctype": resp.headers.get("content-type", "")[:40],
            "size": size,
        })

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.on("console", on_console)
        page.on("pageerror", lambda exc: page_errors.append(f"[pageerror] {exc}"))
        page.on("requestfailed", on_request_failed)
        page.on("response", on_response)

        t0 = time.perf_counter()
        resp = page.goto(BASE, wait_until="networkidle", timeout=30_000)
        t_load = (time.perf_counter() - t0) * 1000

        # navigation timing
        try:
            nav_timings = page.evaluate("""() => {
                const n = performance.getEntriesByType('navigation')[0];
                if (!n) return null;
                return {
                    domContentLoaded: Math.round(n.domContentLoadedEventEnd - n.startTime),
                    loadEvent: Math.round(n.loadEventEnd - n.startTime),
                    transferSize: n.transferSize,
                    encodedBodySize: n.encodedBodySize,
                    decodedBodySize: n.decodedBodySize,
                };
            }""") or {}
        except Exception:
            nav_timings = {}

        page.screenshot(path=str(OUT / "dashboard_audit_landing.png"), full_page=False)

        tab_results: list[dict] = []
        for slug, label in TABS:
            t_start = time.perf_counter()
            pre_errors = len(console_errors)
            pre_failed = len(failed_requests)
            try:
                page.click(f'button.tab[data-tab="{slug}"]', timeout=5000)
                page.wait_for_timeout(800)  # allow async fetches
                # Try to wait for any pending network to settle (best-effort)
                try:
                    page.wait_for_load_state("networkidle", timeout=4000)
                except Exception:
                    pass
                visible = page.locator(f"#panel-{slug}").is_visible()
                # capture a panel-only screenshot (clip below tabs area)
                page.screenshot(path=str(OUT / f"dashboard_audit_{slug}.png"), clip={"x": 0, "y": 0, "width": 1440, "height": 900})
                tab_results.append({
                    "slug": slug,
                    "label": label,
                    "visible": visible,
                    "ms": int((time.perf_counter() - t_start) * 1000),
                    "new_errors": len(console_errors) - pre_errors,
                    "new_failed": len(failed_requests) - pre_failed,
                })
            except Exception as e:
                tab_results.append({"slug": slug, "label": label, "visible": False, "ms": -1, "error": str(e)[:200]})

        # Layout sanity probes (run on landing)
        page.click('button.tab[data-tab="monitor"]', timeout=2000)
        page.wait_for_timeout(200)
        layout = page.evaluate("""() => {
            const vp = { w: window.innerWidth, h: window.innerHeight, dpr: window.devicePixelRatio };
            const doc = { sw: document.documentElement.scrollWidth, sh: document.documentElement.scrollHeight };
            const meta = document.querySelector('meta[name=viewport]')?.content || null;
            const scripts = Array.from(document.querySelectorAll('script[src]')).map(s => s.src);
            const styles = Array.from(document.querySelectorAll('link[rel=stylesheet]')).map(s => s.href);
            const inlineScriptBytes = Array.from(document.querySelectorAll('script:not([src])')).reduce((n,s)=>n+(s.textContent||'').length, 0);
            const inlineStyleBytes = Array.from(document.querySelectorAll('style')).reduce((n,s)=>n+(s.textContent||'').length, 0);
            const focusable = document.querySelectorAll('button, [tabindex], input, select, textarea, a').length;
            const buttonsWithoutAria = Array.from(document.querySelectorAll('button')).filter(b => !b.textContent.trim() && !b.getAttribute('aria-label')).length;
            const imgsNoAlt = Array.from(document.querySelectorAll('img')).filter(i => !i.alt).length;
            return { vp, doc, meta, scripts, styles, inlineScriptBytes, inlineStyleBytes, focusable, buttonsWithoutAria, imgsNoAlt };
        }""")

        # JS heap (Chrome-only, optional)
        try:
            heap = page.evaluate("() => performance.memory ? { usedJSHeap: performance.memory.usedJSHeapSize, totalJSHeap: performance.memory.totalJSHeapSize } : null")
        except Exception:
            heap = None

        browser.close()

    # ── Build report ────────────────────────────────────────────────────────
    lines: list[str] = []
    lines.append("# Dashboard Audit — IDX Strategy Suite (`/`)")
    lines.append("")
    lines.append(f"**URL:** `{BASE}/`  ")
    lines.append(f"**Run:** {time.strftime('%Y-%m-%d %H:%M:%S')}  ")
    lines.append(f"**HTTP:** {resp.status if resp else 'n/a'}  ")
    lines.append(f"**Total goto→networkidle:** {t_load:.0f} ms")
    lines.append("")

    # Performance
    lines.append("## Performance")
    lines.append("")
    if nav_timings:
        lines.append(f"- DOMContentLoaded: **{nav_timings.get('domContentLoaded','?')} ms**")
        lines.append(f"- load event: **{nav_timings.get('loadEvent','?')} ms**")
        lines.append(f"- Transferred (HTML doc only): {fmt_kb(nav_timings.get('transferSize') or 0)}")
        lines.append(f"- HTML decoded size: {fmt_kb(nav_timings.get('decodedBodySize') or 0)}")
    total_bytes = sum(r['size'] for r in requests_seen)
    lines.append(f"- Total requests captured: **{len(requests_seen)}** (~{fmt_kb(total_bytes)} content-length where reported)")
    if heap:
        lines.append(f"- JS heap used: {fmt_kb(heap['usedJSHeap'])} / {fmt_kb(heap['totalJSHeap'])}")
    lines.append("")
    lines.append(f"- Inline `<script>` bytes: **{layout['inlineScriptBytes']:,}**")
    lines.append(f"- Inline `<style>` bytes: **{layout['inlineStyleBytes']:,}**")
    lines.append(f"- External scripts: {len(layout['scripts'])} — {', '.join(s.split('/')[-1] for s in layout['scripts']) or '(none)'}")
    lines.append(f"- External stylesheets: {len(layout['styles'])}")
    lines.append("")

    # Tab walk
    lines.append("## Tab walk (9 tabs)")
    lines.append("")
    lines.append("| Tab | Visible | Time (ms) | New console errors | New network failures |")
    lines.append("|---|:---:|---:|---:|---:|")
    for t in tab_results:
        if "error" in t:
            lines.append(f"| {t['label']} | ❌ click fail | — | — | — |")
            continue
        lines.append(f"| {t['label']} | {'✅' if t['visible'] else '❌'} | {t['ms']} | {t['new_errors']} | {t['new_failed']} |")
    lines.append("")

    # Errors
    lines.append("## Console / page errors")
    lines.append("")
    lines.append(f"- Total console messages: {len(console_log)}")
    lines.append(f"- **Console errors: {len(console_errors)}**")
    lines.append(f"- **Page errors: {len(page_errors)}**")
    if console_errors[:15]:
        lines.append("")
        lines.append("```")
        lines.extend(console_errors[:15])
        lines.append("```")
    if page_errors[:10]:
        lines.append("")
        lines.append("**Page errors:**")
        lines.append("```")
        lines.extend(page_errors[:10])
        lines.append("```")
    lines.append("")

    # Network failures
    lines.append("## Network failures")
    lines.append("")
    if not failed_requests:
        lines.append("- None ✅")
    else:
        lines.append(f"- **{len(failed_requests)} failed requests:**")
        lines.append("")
        for url, reason in failed_requests[:25]:
            lines.append(f"  - `{url}` — {reason}")
    lines.append("")

    # Status code distribution
    statuses: dict[int, int] = {}
    for r in requests_seen:
        statuses[r['status']] = statuses.get(r['status'], 0) + 1
    lines.append("## HTTP status distribution")
    lines.append("")
    for code in sorted(statuses):
        marker = " ⚠️" if code >= 400 else ""
        lines.append(f"- {code}: {statuses[code]}{marker}")
    bad = [r for r in requests_seen if r['status'] >= 400]
    if bad:
        lines.append("")
        lines.append("**Non-2xx responses:**")
        for r in bad[:15]:
            lines.append(f"- `{r['status']} {r['url']}`")
    lines.append("")

    # Layout / a11y / responsive flags
    lines.append("## Layout / a11y signals")
    lines.append("")
    lines.append(f"- Viewport meta: `{layout['meta']}`")
    lines.append(f"- Window: {layout['vp']['w']}×{layout['vp']['h']} @{layout['vp']['dpr']}x  | Document: {layout['doc']['sw']}×{layout['doc']['sh']}")
    lines.append(f"- Focusable elements: {layout['focusable']}")
    lines.append(f"- Buttons with no text and no aria-label: {layout['buttonsWithoutAria']}")
    lines.append(f"- `<img>` without alt: {layout['imgsNoAlt']}")
    lines.append("")

    # Upgrade recommendations (derived from probes)
    lines.append("## Upgrade recommendations")
    lines.append("")
    rec: list[str] = []
    if layout['meta'] and "width=1440" in layout['meta']:
        rec.append("**Responsive viewport** — `meta viewport` is hard-pinned to `width=1440`. Mobile/tablet/4K-laptop users get a broken layout. Replace with `width=device-width, initial-scale=1` and let CSS handle wide breakpoints.")
    if layout['inlineScriptBytes'] > 80_000 or layout['inlineStyleBytes'] > 40_000:
        rec.append(f"**Split the monolith** — `backtest_multi.html` ships ~{layout['inlineScriptBytes']:,}B inline JS + ~{layout['inlineStyleBytes']:,}B inline CSS in one file. Extract to `/static/dashboard.js` + `/static/dashboard.css` so the browser can cache them across reloads and you can lint/typecheck.")
    if console_errors:
        rec.append(f"**Fix {len(console_errors)} console error(s)** before adding features — visible above. Each one is a silent UI regression for users.")
    if bad:
        rec.append(f"**Fix {len(bad)} non-2xx HTTP response(s)** — surface listed above. Some panels are likely loading stale state because of these.")
    if failed_requests:
        rec.append(f"**{len(failed_requests)} request(s) outright failed** — listed above. Often CORS or missing endpoint.")
    if nav_timings.get("loadEvent", 0) > 2000:
        rec.append(f"**Cold load is {nav_timings['loadEvent']} ms** — over 2 s feels sluggish. Likely chart.js (~200KB) blocking parse. Move it to `defer` or load on-demand when the Backtest tab opens.")
    if layout['imgsNoAlt']:
        rec.append(f"**{layout['imgsNoAlt']} `<img>` without `alt`** — accessibility + SEO. Add descriptive alts (or `alt=\"\"` if purely decorative).")
    if layout['buttonsWithoutAria']:
        rec.append(f"**{layout['buttonsWithoutAria']} icon-only buttons missing aria-label** — screen readers see them as blank.")
    # Always-on suggestions
    rec.append("**Add a `/healthz`-style smoke endpoint** the audit/Playwright can hit cheaply to know the scheduler + DB are alive without rendering the full dashboard.")
    rec.append("**Wire this audit into a `npm run audit` / `make audit` target** alongside `smoketest_dive.py` so regressions on either page are caught in one command.")
    for i, r in enumerate(rec, 1):
        lines.append(f"{i}. {r}")
    lines.append("")

    out_path = OUT / "dashboard_audit.md"
    out_path.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nReport: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
