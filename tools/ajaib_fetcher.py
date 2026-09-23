#!/usr/bin/env python3
"""
Ajaib Terminal Fetcher (CDP)
============================
Fetch market data from the Ajaib Terminal desktop app (Tauri/WebView2) by
calling fetch() inside the live page over the Chrome DevTools Protocol.

Why CDP: Ajaib has no public API. The Terminal app talks to a local Tauri
sidecar (http://127.0.0.1:<ephemeral-port>/v1/...) which forwards to the
backend behind Cloudflare. Direct calls (curl/python) are CF-fingerprint-
blocked, but requests made *from inside the page context* — carrying the
app's own recorded `Authorization: jwt ...` + device headers — pass.

How it works
------------
1. A recorder is injected into the page (fetch + XHR hooks) that captures
   every 127.0.0.1 request the app itself makes, with its full header set.
2. The newest captured authenticated header set (the jwt is short-lived and
   rotates) is kept INSIDE the page (`window.__ajaibAuth`); the token never
   travels to this process or any output.
3. Data fetches run in the page via Runtime.callFunctionOn with the path as
   a structured argument value. On 401 the page clicks the Portfolio nav to
   trigger a fresh authenticated request and retries once.

Prerequisites
-------------
The app must run with WebView2 remote debugging enabled:

    set WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=9222
    "C:\\Users\\tjies\\AppData\\Local\\Ajaib Terminal\\app.exe"

or just use the built-in launcher (restarts the app with the env var):

    python tools/ajaib_fetcher.py launch

Security posture (deliberate):
  - GET ONLY. No POST surface exists in this tool; order placement is
    unreachable by construction.
  - Hosts: 127.0.0.1 only (CDP discovery: /json paths; data fetches: the
    loopback sidecar base, re-validated on every use).
  - No dynamic JavaScript: every script is a module-level constant; CLI
    values travel as CDP argument VALUES, never interpolated code.
  - Endpoint URLs: module-level constant templates filled only with
    regex-whitelisted values via str.format.
  - Every output write goes through pathlib with a basename-only filename
    (alnum + underscore, fullmatch-validated), a realpath-normalized output
    directory with no dot segments, and an explicit parent-containment
    check before .open(). No API-supplied string ever reaches the fs.

Usage
-----
    python tools/ajaib_fetcher.py status
    python tools/ajaib_fetcher.py candles BBCA [--resolution 1D] [--countback 500]
    python tools/ajaib_fetcher.py broker-flow BBCA [--period D1] [--brokers XL,BK]
    python tools/ajaib_fetcher.py broker-summary BBCA --start 2026-09-18 --end 2026-09-18
    python tools/ajaib_fetcher.py broker-dist BBCA [--date 2026-09-18]
    python tools/ajaib_fetcher.py orderbook BBCA
    python tools/ajaib_fetcher.py bestquote BBCA
    python tools/ajaib_fetcher.py order-queue BBCA 6225
    python tools/ajaib_fetcher.py running-trades BBCA
    python tools/ajaib_fetcher.py insider BBCA
    python tools/ajaib_fetcher.py foreign-domestic
    python tools/ajaib_fetcher.py snapshot BBCA     # candles 1D+1H + flow + book
    python tools/ajaib_fetcher.py raw "/v1/stock/data/trading-day/time/"

Common flags: --cdp-port 9222 | --out data/ajaib_raw | --print (stdout only)

Output: one JSON file per call under --out, wrapped as
    {"endpoint": ..., "fetched_at_wib": ..., "status": ..., "data": ...}

Rate limit: 1.0 s between page fetches (snapshot loops).
"""

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

from websockets.asyncio.client import connect as ws_connect

# === CONFIG ===
CDP_PORT = int(os.environ.get("AJAIB_CDP_PORT", "9222"))
APP_PATH = r"C:\Users\tjies\AppData\Local\Ajaib Terminal\app.exe"
DEFAULT_OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "data", "ajaib_raw")
RATE_LIMIT_S = 1.0
WIB = timezone(timedelta(hours=7))

# === INPUT WHITELISTS (anything failing these never reaches JS/URL/fs) ===
RE_TICKER = re.compile(r"^[A-Z]{2,6}$")
RE_RESOLUTION = re.compile(r"^\d{1,3}[MHDW]?$")
RE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RE_BROKERS = re.compile(r"^[A-Za-z0-9]{2,4}(,[A-Za-z0-9]{2,4})*$")
RE_PRICE = re.compile(r"^\d+(\.\d+)?$")
RE_PERIOD = re.compile(r"^[A-Za-z0-9]{1,4}$")
# raw passthrough: /v1/ only, no %-encoding, no dot segments, no whitespace
RE_RAW_PATH = re.compile(r"^/v1/[A-Za-z0-9/_.?&=,:-]{0,400}$")
# output dir: path characters only; dot segments rejected separately
RE_OUT_DIR = re.compile(r"^[A-Za-z0-9 _\-./\\:]{1,300}$")
# generated filenames: alnum + underscore + .json only
RE_FILE_NAME = re.compile(r"^[A-Za-z0-9_]+\.json$")

# === CDP + ENDPOINT URL TEMPLATES (constants; filled via str.format only) ===
TPL_CDP_JSON = "http://127.0.0.1:{port}/json"

TPL_CANDLES = "/v1/stock/detail/{code}/candlestick/?resolution={res}&countback={cb}"
TPL_BROKER_FLOW = ("/v1/stock/data/stock/{code}/broker-flow/"
                   "?period={per}&include_price=true&broker_codes={brokers}")
TPL_BROKER_SUMMARY = ("/v1/stock/data/stock/{code}/broker-summary/"
                      "?start_date={start}&end_date={end}&net=true")
TPL_BROKER_DIST = ("/v1/stock/data/broker/distribution?stock_code={code}"
                   "&market_type=&distribution_type={dtype}&date={date}"
                   "&investor_type=")
TPL_ORDERBOOK = "/v1/stock/data/orderbook?code={code}"
TPL_BESTQUOTE = "/v1/stock/bestquote/?code={code}&extended=true"
TPL_ORDER_QUEUE = ("/v1/stock/data/order-queue/{code}/{price}"
                   "?from_time=00:00:00&to_time=23:59:59&sort=ASC"
                   "&status=OPEN,PARTIAL")
TPL_RUNNING_TRADES = ("/v1/stock/detail/{code}/running_trades/"
                      "?direction=DESC&last_timestamp={ts}&page=1&page_size=40")
TPL_INSIDER = "/v1/stock/insiders/?page=1&page_size=10&ticker_code={code}"
TPL_FOREIGN_DOMESTIC = "/v1/stock/detail/foreign-domestic-activity-ihsg/?range=DAY&type=RG"
TPL_TRADING_DAY_TIME = "/v1/stock/data/trading-day/time/"

SNAPSHOT_PARTS = [
    ("candles_1d", "/v1/stock/detail/{c}/candlestick/?resolution=1D&countback=500"),
    ("candles_1h", "/v1/stock/detail/{c}/candlestick/?resolution=1H&countback=500"),
    ("bestquote", "/v1/stock/bestquote/?code={c}&extended=true"),
    ("orderbook", "/v1/stock/data/orderbook?code={c}"),
    ("broker_flow", "/v1/stock/data/stock/{c}/broker-flow/?period=D1&include_price=true"),
    ("running_trades", "/v1/stock/detail/{c}/running_trades/?direction=DESC&last_timestamp={ts}&page=1&page_size=40"),
]

# === PAGE SCRIPTS (module constants — never built dynamically) ===

# Recorder: captures every 127.0.0.1 request (fetch + XHR) with its headers.
# The app's axios client injects a fresh short-lived `Authorization: jwt ...`
# plus device headers on each authenticated call; we record those.
JS_RECORDER = (
    "(function(){\n"
    "  if (window.__recInstalled) return;\n"
    "  window.__recInstalled = true;\n"
    "  window.__cap = [];\n"
    "  const capture = function(url, h){\n"
    "    if (url && String(url).indexOf('127.0.0.1') > -1) {\n"
    "      window.__cap.push({url: String(url), h: h});\n"
    "    }\n"
    "  };\n"
    "  const of = window.fetch;\n"
    "  window.fetch = function(input, init){\n"
    "    try {\n"
    "      let url = '';\n"
    "      const h = {};\n"
    "      if (typeof input === 'string') { url = input; }\n"
    "      else if (input && input.url) {\n"
    "        url = input.url;\n"
    "        if (input.headers && input.headers.forEach) {\n"
    "          input.headers.forEach(function(v,k){ h[k]=v; });\n"
    "        }\n"
    "      }\n"
    "      if (init && init.headers) {\n"
    "        if (init.headers.forEach) { init.headers.forEach(function(v,k){ h[k]=v; }); }\n"
    "        else { Object.assign(h, init.headers); }\n"
    "      }\n"
    "      capture(url, h);\n"
    "    } catch(e) {}\n"
    "    return of.apply(this, arguments);\n"
    "  };\n"
    "  const op = XMLHttpRequest.prototype.open;\n"
    "  const sr = XMLHttpRequest.prototype.setRequestHeader;\n"
    "  const sd = XMLHttpRequest.prototype.send;\n"
    "  XMLHttpRequest.prototype.open = function(m, u){\n"
    "    this.__u = u; this.__h = {}; return op.apply(this, arguments);\n"
    "  };\n"
    "  XMLHttpRequest.prototype.setRequestHeader = function(k, v){\n"
    "    try { if (this.__h) this.__h[k] = v; } catch(e) {}\n"
    "    return sr.apply(this, arguments);\n"
    "  };\n"
    "  XMLHttpRequest.prototype.send = function(){\n"
    "    try { capture(this.__u, this.__h); } catch(e) {}\n"
    "    return sd.apply(this, arguments);\n"
    "  };\n"
    "})()"
)

# Auth prep: pick the newest recorded authenticated request, remember its
# header set in the page (the jwt token never leaves the page context), and
# optionally trigger a fresh authenticated request by clicking the Portfolio
# nav link (SPA navigation fires account endpoints). Used as a
# callFunctionOn function declaration with a structured args value.
JS_PREP_DECL = (
    "async function __ajaibPrep(args){\n"
    "  const clickNav = function(){\n"
    "    const here = location.pathname || '';\n"
    "    let want = 'portfolio';\n"
    "    if (here.indexOf('portfolio') > -1) want = 'market';\n"
    "    for (const el of document.querySelectorAll('a')) {\n"
    "      const href = el.getAttribute('href') || '';\n"
    "      if (href.indexOf(want) > -1) { el.click(); return want; }\n"
    "    }\n"
    "    return null;\n"
    "  };\n"
    "  const findAuth = function(){\n"
    "    let best = null;\n"
    "    for (const c of (window.__cap || [])) {\n"
    "      if (c.h && c.h['Authorization']) best = c;\n"
    "    }\n"
    "    return best;\n"
    "  };\n"
    "  if (args.trigger) {\n"
    "    const before = (window.__cap || []).length;\n"
    "    const clicked = clickNav();\n"
    "    await new Promise(function(r){ setTimeout(r, args.waitMs || 2500); });\n"
    "    const grew = (window.__cap || []).length > before;\n"
    "    if (!clicked || !grew) {\n"
    "      return JSON.stringify({ok: false, reason: 'nav click fired no requests',\n"
    "        clicked: clicked});\n"
    "    }\n"
    "  }\n"
    "  const best = findAuth();\n"
    "  if (!best) return JSON.stringify({ok: false, reason: 'no authed capture'});\n"
    "  let cut = best.url.indexOf('/v1/');\n"
    "  const cut3 = best.url.indexOf('/v3/');\n"
    "  if (cut === -1 || (cut3 > -1 && cut3 < cut)) cut = cut3;\n"
    "  if (cut === -1) return JSON.stringify({ok: false, reason: 'bad capture url'});\n"
    "  window.__ajaibAuth = best.h;\n"
    "  window.__ajaibBase = best.url.slice(0, cut);\n"
    "  return JSON.stringify({ok: true, base: window.__ajaibBase,\n"
    "    captured: (window.__cap || []).length});\n"
    "}"
)

# Data fetch. Runs in the page with the recorded auth headers; on 401 it
# triggers one fresh capture (nav click) and retries. Args travel as a
# structured CDP callFunctionOn argument VALUE, not interpolated code.
JS_FETCH_DECL = (
    "async function __ajaibFetch(args){\n"
    "  const doFetch = async function(){\n"
    "    const ctrl = new AbortController();\n"
    "    const t = setTimeout(function(){ ctrl.abort(); }, 15000);\n"
    "    try {\n"
    "      const r = await fetch(window.__ajaibBase + args.path,\n"
    "          {headers: window.__ajaibAuth, credentials: 'omit',\n"
    "           signal: ctrl.signal});\n"
    "      const text = await r.text();\n"
    "      let body = text;\n"
    "      try { body = JSON.parse(text); } catch (e) {}\n"
    "      return {status: r.status, body: body};\n"
    "    } finally { clearTimeout(t); }\n"
    "  };\n"
    "  let res = await doFetch();\n"
    "  if (res.status === 401) {\n"
    "    const here = location.pathname || '';\n"
    "    let want = 'portfolio';\n"
    "    if (here.indexOf('portfolio') > -1) want = 'market';\n"
    "    let a = null;\n"
    "    for (const el of document.querySelectorAll('a')) {\n"
    "      const href = el.getAttribute('href') || '';\n"
    "      if (href.indexOf(want) > -1) { a = el; break; }\n"
    "    }\n"
    "    if (a) a.click();\n"
    "    await new Promise(function(r){ setTimeout(r, 3000); });\n"
    "    let best = null;\n"
    "    for (const c of (window.__cap || [])) {\n"
    "      if (c.h && c.h['Authorization']) best = c;\n"
    "    }\n"
    "    if (best) {\n"
    "      let cut = best.url.indexOf('/v1/');\n"
    "      const cut3 = best.url.indexOf('/v3/');\n"
    "      if (cut === -1 || (cut3 > -1 && cut3 < cut)) cut = cut3;\n"
    "      if (cut > -1) {\n"
    "        window.__ajaibAuth = best.h;\n"
    "        window.__ajaibBase = best.url.slice(0, cut);\n"
    "        res = await doFetch();\n"
    "      }\n"
    "    }\n"
    "  }\n"
    "  return JSON.stringify(res);\n"
    "}"
)

JS_WINDOW = "window"


def require(pattern: re.Pattern, value: str, what: str) -> str:
    if not pattern.match(value):
        raise SystemExit(f"invalid {what}: {value!r}")
    return value


# ---------------------------------------------------------------- CDP plumbing

def http_json(url: str, timeout: float = 5.0):
    """GET a CDP discovery URL. Hard-restricted to http://127.0.0.1:<port>/json*"""
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1"
            or not parsed.port or not (1 <= parsed.port <= 65535)
            or parsed.username or parsed.password
            or not parsed.path.startswith("/json")):
        raise ValueError(f"refusing non-CDP URL: {url!r}")
    with urllib.request.urlopen(parsed.geturl(), timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def cdp_json_url(cdp_port: int) -> str:
    """The only CDP discovery URL this tool ever uses."""
    return TPL_CDP_JSON.format(port=int(cdp_port))


def find_page_target(cdp_port: int):
    """Return the webSocketDebuggerUrl of the tauri.localhost page target."""
    targets = http_json(cdp_json_url(cdp_port))
    pages = [t for t in targets
             if t.get("type") == "page" and "tauri.localhost" in (t.get("url") or "")]
    if not pages:
        raise RuntimeError(
            f"No tauri.localhost page target on CDP {cdp_port}. "
            f"Targets: {[t.get('url') for t in targets]}")
    return pages[0]["webSocketDebuggerUrl"]


class CDP:
    """Minimal CDP client: constant scripts + structured-argument calls."""

    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self._id = 0

    async def __aenter__(self):
        self._ws = await ws_connect(self.ws_url, max_size=64 * 1024 * 1024)
        return self

    async def __aexit__(self, *exc):
        await self._ws.close()

    async def _call(self, method: str, params: dict, timeout: float = 30.0):
        self._id += 1
        msg = {"id": self._id, "method": method, "params": params}
        await self._ws.send(json.dumps(msg))
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"CDP {method} timed out after {timeout}s")
            raw = await asyncio.wait_for(self._ws.recv(), timeout=remaining)
            data = json.loads(raw)
            if data.get("id") != self._id:
                continue  # page events (console, network, ...) — skip
            details = (data.get("result", {}).get("exceptionDetails")
                       or data.get("error"))
            if details:
                exc_obj = (details.get("exception", {}) if isinstance(details, dict)
                           else {})
                text = (exc_obj.get("description") or details.get("text")
                        or json.dumps(details)[:400])
                raise RuntimeError(f"Page JS error: {text}")
            return data["result"]

    async def evaluate(self, expression: str, timeout: float = 30.0):
        """Evaluate a constant script; returns the raw value."""
        res = await self._call("Runtime.evaluate",
                               {"expression": expression, "returnByValue": True,
                                "awaitPromise": True, "userGesture": True},
                               timeout=timeout)
        return res.get("result", {}).get("value")

    async def add_init_script(self, source: str):
        await self._call("Page.addScriptToEvaluateOnNewDocument", {"source": source})

    async def reload(self):
        await self._call("Page.reload", {})

    async def window_object_id(self) -> str:
        res = await self._call("Runtime.evaluate",
                               {"expression": JS_WINDOW, "returnByValue": False})
        oid = res.get("result", {}).get("objectId")
        if not oid:
            raise RuntimeError("could not obtain window objectId")
        return oid

    async def call_function(self, func_decl: str, args_value,
                            timeout: float = 30.0):
        oid = await self.window_object_id()
        params = {"objectId": oid, "functionDeclaration": func_decl,
                  "arguments": [{"value": args_value}],
                  "awaitPromise": True, "returnByValue": True,
                  "userGesture": True}
        res = await self._call("Runtime.callFunctionOn", params, timeout=timeout)
        return res.get("result", {}).get("value")


def checked_sidecar_base(base: str) -> str:
    """Only loopback http URLs may be used as fetch targets."""
    parsed = urllib.parse.urlsplit(base)
    if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1"
            or not parsed.port or not (1024 <= parsed.port <= 65535)
            or parsed.path not in ("", "/")):
        raise RuntimeError(f"refusing unexpected sidecar base: {base!r}")
    return base.rstrip("/")


async def ensure_auth(cdp: CDP) -> str:
    """Install the recorder, capture a fresh authenticated header set, and
    return the validated sidecar base URL. Token stays inside the page."""
    await cdp.add_init_script(JS_RECORDER)  # future documents (after reload)
    await cdp.evaluate(JS_RECORDER)         # current document, right now
    val = await cdp.call_function(JS_PREP_DECL,
                                  {"trigger": True, "waitMs": 2500})
    prep = json.loads(val) if val else {}
    if not prep.get("ok"):
        # Fallback: reload the SPA. Startup traffic (pin/auth + config) is
        # then captured by the init-script recorder automatically.
        await cdp.reload()
        await asyncio.sleep(12)
        val = await cdp.call_function(JS_PREP_DECL, {"trigger": False})
        prep = json.loads(val) if val else {}
    if not prep.get("ok"):
        raise RuntimeError(
            "no authenticated request captured (is the app logged in?): "
            + json.dumps(prep))
    return checked_sidecar_base(prep["base"])


async def page_fetch(cdp: CDP, path: str) -> dict:
    """GET path inside the page context with the recorded auth headers."""
    val = await cdp.call_function(JS_FETCH_DECL, {"path": path}, timeout=25.0)
    return json.loads(val)


# ---------------------------------------------------------------------- output

def prepare_out_dir(out_dir: str) -> str:
    """Validate and create the output directory; returns its realpath."""
    require(RE_OUT_DIR, out_dir, "output directory")
    segments = os.path.normpath(out_dir).replace("\\", "/").split("/")
    if ".." in segments or "." in segments:
        raise SystemExit(f"output directory must not contain dot segments: {out_dir!r}")
    resolved = os.path.realpath(os.path.abspath(out_dir))
    os.makedirs(resolved, exist_ok=True)
    return resolved


def output_target(resolved_dir: str, parts: list) -> Path:
    """pathlib target under resolved_dir; basename-safe, containment-checked."""
    cleaned = [re.sub(r"[^A-Za-z0-9_]", "", str(p)) for p in parts]
    name = os.path.basename("_".join([c for c in cleaned if c]) + ".json")
    if not RE_FILE_NAME.fullmatch(name) or name == ".json":
        raise RuntimeError(f"generated filename failed validation: {name!r}")
    base = Path(resolved_dir)
    target = base / name
    if target.parent != base:
        raise RuntimeError(f"output escaped output dir: {name!r}")
    return target


def save_result(out_dir: str, kind: str, ident: str, endpoint: str,
                resp: dict, do_print: bool) -> str:
    rec = {"endpoint": endpoint,
           "fetched_at_wib": datetime.now(WIB).isoformat(timespec="seconds"),
           "status": resp.get("status"), "data": resp.get("body")}
    if do_print:
        print(json.dumps(rec, ensure_ascii=False, indent=2)[:20000])
        return "(stdout)"
    resolved_dir = prepare_out_dir(out_dir)
    stamp = datetime.now(WIB).strftime("%Y%m%d_%H%M%S")
    target = output_target(resolved_dir, ["ajaib", kind, ident, stamp])
    with target.open("w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)
    print(f"[ok] {target}  (HTTP {rec['status']}, {target.stat().st_size} bytes)")
    return str(target)


# ----------------------------------------------------------------------- commands

def build_path(args) -> tuple[str, str, str]:
    """Return (kind, ident, path) from a constant template + whitelisted values."""
    a = args
    code = require(RE_TICKER, a.code.upper(), "ticker")
    if a.cmd == "candles":
        return ("candles", code, TPL_CANDLES.format(
            code=code, res=require(RE_RESOLUTION, a.resolution, "resolution"),
            cb=str(int(a.countback))))
    if a.cmd == "broker-flow":
        return ("broker_flow", code, TPL_BROKER_FLOW.format(
            code=code, per=require(RE_PERIOD, a.period, "period"),
            brokers=(require(RE_BROKERS, a.brokers, "brokers") if a.brokers else "")))
    if a.cmd == "broker-summary":
        return ("broker_summary", code, TPL_BROKER_SUMMARY.format(
            code=code, start=require(RE_DATE, a.start, "start date"),
            end=require(RE_DATE, a.end, "end date")))
    if a.cmd == "broker-dist":
        today = datetime.now(WIB).strftime("%Y-%m-%d")
        return ("broker_dist", code, TPL_BROKER_DIST.format(
            code=code, dtype=a.type,
            date=require(RE_DATE, a.date or today, "date")))
    if a.cmd == "orderbook":
        return ("orderbook", code, TPL_ORDERBOOK.format(code=code))
    if a.cmd == "bestquote":
        return ("bestquote", code, TPL_BESTQUOTE.format(code=code))
    if a.cmd == "order-queue":
        return ("order_queue", code + "_" + re.sub(r"[^0-9]", "", str(a.price)),
                TPL_ORDER_QUEUE.format(
                    code=code, price=require(RE_PRICE, str(a.price), "price")))
    if a.cmd == "running-trades":
        ts = str(int(time.time() * 1000))
        return ("running_trades", code, TPL_RUNNING_TRADES.format(code=code, ts=ts))
    if a.cmd == "insider":
        return ("insider", code, TPL_INSIDER.format(code=code))
    if a.cmd == "foreign-domestic":
        return ("foreign_domestic", "IHSG", TPL_FOREIGN_DOMESTIC)
    if a.cmd == "raw":
        path = a.path.strip()
        if ".." in path or "%" in path or not RE_RAW_PATH.match(path):
            raise SystemExit("raw path must stay under /v1/ with safe characters")
        return ("raw", "RAW", path)
    raise SystemExit(f"unhandled command {a.cmd}")


async def cmd_async(args) -> int:
    cdp = int(args.cdp_port)
    ws_url = find_page_target(cdp)

    async with CDP(ws_url) as session:
        base = await ensure_auth(session)

        if args.cmd == "status":
            print(f"sidecar: {base}")
            resp = await page_fetch(session, TPL_TRADING_DAY_TIME)
            print(f"session probe HTTP {resp.get('status')}: "
                  f"{json.dumps(resp.get('body'), ensure_ascii=False)[:300]}")
            return 0 if resp.get("status") == 200 else 1

        if args.cmd == "snapshot":
            code = require(RE_TICKER, args.code.upper(), "ticker")
            bundle = {}
            for kind, tpl in SNAPSHOT_PARTS:
                path = tpl.format(c=code, ts=str(int(time.time() * 1000)))
                resp = await page_fetch(session, path)
                bundle[kind] = {"endpoint": path, "status": resp.get("status"),
                                "data": resp.get("body")}
                print(f"  {kind}: HTTP {resp.get('status')}")
                await asyncio.sleep(RATE_LIMIT_S)
            resolved_dir = prepare_out_dir(args.out)
            stamp = datetime.now(WIB).strftime("%Y%m%d_%H%M%S")
            target = output_target(resolved_dir, ["ajaib", "snapshot", code, stamp])
            with target.open("w", encoding="utf-8") as f:
                json.dump({"code": code,
                           "fetched_at_wib": datetime.now(WIB).isoformat(timespec="seconds"),
                           "parts": bundle}, f, ensure_ascii=False, indent=2)
            print(f"[ok] {target}")
            return 0

        kind, ident, path = build_path(args)
        resp = await page_fetch(session, path)
        save_result(args.out, kind, ident, path, resp, args.print)
        return 0 if resp.get("status") == 200 else 2


def cmd_launch(args) -> int:
    """Restart Ajaib Terminal with WebView2 remote debugging enabled."""
    port = int(args.cdp_port)
    if not (1024 <= port <= 65535):
        raise SystemExit(f"CDP port out of range: {port}")
    cdp_url = cdp_json_url(port)
    try:
        http_json(cdp_url, timeout=2.0)
        print(f"CDP already up on {port}. Nothing to do.")
        return 0
    except Exception:
        pass
    print("Killing existing Ajaib Terminal (session persists on disk)...")
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Get-Process app -ErrorAction SilentlyContinue | "
                    "? { $_.Path -like '*Ajaib*' } | Stop-Process -Force"],
                   check=False, timeout=20)
    time.sleep(2)
    env = dict(os.environ,
               WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=f"--remote-debugging-port={port}")
    print(f"Launching {APP_PATH} with CDP on {port}...")
    subprocess.Popen([APP_PATH], env=env,
                     creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
    for _ in range(30):
        time.sleep(2)
        try:
            http_json(cdp_url, timeout=2.0)
            print(f"CDP is up on {port}.")
            return 0
        except Exception:
            continue
    print("CDP did not come up within 60 s.", file=sys.stderr)
    return 1


def main():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--cdp-port", type=int, default=CDP_PORT)
    common.add_argument("--out", default=DEFAULT_OUT)
    common.add_argument("--print", dest="print", action="store_true")
    ap = argparse.ArgumentParser(
        description="Ajaib Terminal market-data fetcher (CDP, GET-only)",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__,
        parents=[common])
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name):
        return sub.add_parser(name, parents=[common])

    add("status")
    add("launch")
    p = add("candles")
    p.add_argument("code")
    p.add_argument("--resolution", default="1D")
    p.add_argument("--countback", type=int, default=500)
    p = add("broker-flow")
    p.add_argument("code")
    p.add_argument("--period", default="D1")
    p.add_argument("--brokers", default=None, help="comma-separated, e.g. XL,BK")
    p = add("broker-summary")
    p.add_argument("code")
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p = add("broker-dist")
    p.add_argument("code")
    p.add_argument("--date", default=None)
    p.add_argument("--type", dest="type", default="VALUE", choices=["VALUE", "VOLUME"])
    p = add("orderbook"); p.add_argument("code")
    p = add("bestquote"); p.add_argument("code")
    p = add("order-queue"); p.add_argument("code"); p.add_argument("price")
    p = add("running-trades"); p.add_argument("code")
    p = add("insider"); p.add_argument("code")
    add("foreign-domestic")
    p = add("snapshot"); p.add_argument("code")
    p = add("raw"); p.add_argument("path")

    args = ap.parse_args()
    if args.cmd == "launch":
        sys.exit(cmd_launch(args))
    try:
        sys.exit(asyncio.run(cmd_async(args)))
    except RuntimeError as e:
        print(f"[fail] {e}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"[fail] CDP unreachable on {args.cdp_port}: {e}\n"
              f"       Run: python tools/ajaib_fetcher.py launch", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
