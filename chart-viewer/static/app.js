/* Multi-pane charting frontend — vanilla JS + lightweight-charts (v4). */
const LWC = window.LightweightCharts;

/* Indicator chips. `bottom: true` => own stacked price scale at the chart base. */
const INDICATORS = [
  { key: "SMA20",  label: "SMA20" },
  { key: "SMA50",  label: "SMA50" },
  { key: "SMA200", label: "SMA200" },
  { key: "EMA",    label: "EMA" },
  { key: "BB",     label: "BB" },
  { key: "VWAP",   label: "VWAP" },
  { key: "VP",     label: "VP" },
  { key: "FVG",    label: "FVG" },
  { key: "VOL",    label: "Vol",  bottom: true },
  { key: "RSI",    label: "RSI",  bottom: true },
  { key: "MACD",   label: "MACD", bottom: true },
];
const BOTTOM_ORDER = ["VOL", "RSI", "MACD"];

/* Seed panes (cycled to fill whatever pane count is selected). */
const SEEDS = [
  { sym: "BBCA", mkt: "IDX",    tf: "1d", on: ["SMA20", "SMA50", "VOL"] },
  { sym: "AAPL", mkt: "US",     tf: "1d", on: ["SMA50", "SMA200", "VOL"] },
  { sym: "BTC-USD", mkt: "Crypto", tf: "1d", on: ["EMA", "RSI"] },
  { sym: "BBRI", mkt: "IDX",    tf: "1d", on: ["BB", "VWAP"] },
  { sym: "TLKM", mkt: "IDX",    tf: "1d", on: ["MACD", "VOL"] },
  { sym: "NVDA", mkt: "US",     tf: "1d", on: ["SMA20", "VOL"] },
  { sym: "ETH-USD", mkt: "Crypto", tf: "1d", on: ["RSI"] },
  { sym: "ASII", mkt: "IDX",    tf: "1d", on: ["VP", "VOL"] },
];

const CHART_OPTS = {
  layout: { background: { color: "#0e1116" }, textColor: "#9aa4b2", fontSize: 11 },
  grid: { vertLines: { color: "#1b212c" }, horzLines: { color: "#1b212c" } },
  rightPriceScale: { borderColor: "#2a3140" },
  timeScale: { borderColor: "#2a3140", timeVisible: true, secondsVisible: false },
  crosshair: { mode: LWC.CrosshairMode.Normal },
};

const grid = document.getElementById("grid");
const tpl = document.getElementById("paneTpl");
let panes = [];

/* ---------------- pane lifecycle ---------------- */
function buildPanes(n) {
  panes.forEach((p) => { p.ro.disconnect(); p.chart.remove(); });
  panes = [];
  grid.innerHTML = "";
  grid.dataset.panes = n;

  for (let i = 0; i < n; i++) {
    const seed = SEEDS[i % SEEDS.length];
    const node = tpl.content.firstElementChild.cloneNode(true);
    grid.appendChild(node);

    const symEl = node.querySelector(".sym");
    const mktEl = node.querySelector(".mkt");
    const tfEl = node.querySelector(".tf");
    const indsEl = node.querySelector(".inds");
    const statusEl = node.querySelector(".status");
    const body = node.querySelector(".pane-body");

    symEl.value = seed.sym;
    mktEl.value = seed.mkt;
    tfEl.value = seed.tf;

    const active = new Set(seed.on);
    INDICATORS.forEach((ind) => {
      const b = document.createElement("button");
      b.textContent = ind.label;
      b.dataset.key = ind.key;
      if (active.has(ind.key)) b.classList.add("on");
      indsEl.appendChild(b);
    });

    const chart = LWC.createChart(body, {
      ...CHART_OPTS,
      width: body.clientWidth || 300,
      height: body.clientHeight || 240,
    });
    const candle = chart.addCandlestickSeries({
      upColor: "#26a69a", downColor: "#ef5350", borderVisible: false,
      wickUpColor: "#26a69a", wickDownColor: "#ef5350",
    });

    const pane = {
      node, symEl, mktEl, tfEl, indsEl, statusEl, body,
      chart, candle, active, extra: [], priceLines: [], data: null,
    };

    // Resize the chart with its container.
    const ro = new ResizeObserver(() => {
      chart.applyOptions({ width: body.clientWidth, height: body.clientHeight });
    });
    ro.observe(body);
    pane.ro = ro;

    // Wiring.
    const reload = () => loadPane(pane);
    symEl.addEventListener("change", reload);
    symEl.addEventListener("keydown", (e) => { if (e.key === "Enter") reload(); });
    mktEl.addEventListener("change", reload);
    tfEl.addEventListener("change", reload);
    indsEl.addEventListener("click", (e) => {
      const btn = e.target.closest("button");
      if (!btn) return;
      const key = btn.dataset.key;
      if (active.has(key)) { active.delete(key); btn.classList.remove("on"); }
      else { active.add(key); btn.classList.add("on"); }
      renderIndicators(pane);  // re-render from cached data, no refetch
    });

    panes.push(pane);
    loadPane(pane);
  }
}

/* ---------------- data load ---------------- */
async function loadPane(pane) {
  const symbol = pane.symEl.value.trim();
  const market = pane.mktEl.value;
  const timeframe = pane.tfEl.value;
  if (!symbol) return;

  pane.statusEl.textContent = "loading…";
  pane.statusEl.classList.remove("err");
  const url = `/api/ohlcv?symbol=${encodeURIComponent(symbol)}&market=${market}&timeframe=${timeframe}`;
  try {
    const res = await fetch(url);
    const json = await res.json();
    if (!res.ok) throw new Error(json.error || `HTTP ${res.status}`);
    pane.data = json;
    pane.candle.setData(json.candles);
    renderIndicators(pane);
    pane.chart.timeScale().fitContent();
    const last = json.candles[json.candles.length - 1];
    pane.statusEl.textContent = `${json.symbol} · ${json.bars} bars · ${last ? last.close : "?"}`;
  } catch (err) {
    pane.data = null;
    pane.candle.setData([]);
    renderIndicators(pane);
    pane.statusEl.textContent = err.message;
    pane.statusEl.classList.add("err");
  }
}

/* ---------------- indicator rendering ---------------- */
function clearExtras(pane) {
  pane.extra.forEach((s) => pane.chart.removeSeries(s));
  pane.extra = [];
  pane.priceLines.forEach((pl) => pane.candle.removePriceLine(pl));
  pane.priceLines = [];
  pane.candle.setMarkers([]);
}

function computeLayout(activeBottom) {
  const layout = {};
  const n = activeBottom.length;
  if (n === 0) {
    layout.right = { top: 0.06, bottom: 0.08 };
    return layout;
  }
  layout.right = { top: 0.06, bottom: 0.30 };
  const base = 0.70, region = 0.30, slice = region / n;
  activeBottom.forEach((key, i) => {
    const top = base + i * slice;
    const end = base + (i + 1) * slice;
    layout[key] = { top: top + 0.01, bottom: (1 - end) + 0.01 };
  });
  return layout;
}

function addLine(pane, scaleId, data, opts) {
  const s = pane.chart.addLineSeries({
    priceScaleId: scaleId, lineWidth: 1.5, lastValueVisible: false,
    priceLineVisible: false, crosshairMarkerVisible: false, ...opts,
  });
  s.setData(data || []);
  pane.extra.push(s);
  return s;
}

function renderIndicators(pane) {
  clearExtras(pane);
  const d = pane.data;
  const a = pane.active;

  const activeBottom = BOTTOM_ORDER.filter((k) => a.has(k));
  const layout = computeLayout(activeBottom);
  pane.chart.priceScale("right").applyOptions({ scaleMargins: layout.right });
  if (!d) return;
  const ind = d.indicators;

  // --- price-scale overlays ---
  if (a.has("SMA20"))  addLine(pane, "right", ind.sma20,  { color: "#f0a30a" });
  if (a.has("SMA50"))  addLine(pane, "right", ind.sma50,  { color: "#2196f3" });
  if (a.has("SMA200")) addLine(pane, "right", ind.sma200, { color: "#ab47bc" });
  if (a.has("EMA"))    addLine(pane, "right", ind.ema20,  { color: "#00bcd4" });
  if (a.has("VWAP"))   addLine(pane, "right", ind.vwap,   { color: "#ffd54f", lineStyle: LWC.LineStyle.Dotted });
  if (a.has("BB")) {
    const c = "rgba(130,150,180,0.7)";
    addLine(pane, "right", ind.bb_upper, { color: c });
    addLine(pane, "right", ind.bb_mid,   { color: c, lineStyle: LWC.LineStyle.Dashed });
    addLine(pane, "right", ind.bb_lower, { color: c });
  }

  // --- Volume Profile POC / VAH / VAL as price lines ---
  if (a.has("VP") && ind.volume_profile) {
    const vp = ind.volume_profile;
    pane.priceLines.push(pane.candle.createPriceLine({
      price: vp.poc, color: "#ffb300", lineWidth: 2, title: "POC",
    }));
    [["VAH", vp.vah], ["VAL", vp.val]].forEach(([t, p]) => {
      pane.priceLines.push(pane.candle.createPriceLine({
        price: p, color: "rgba(255,179,0,0.55)", lineWidth: 1,
        lineStyle: LWC.LineStyle.Dashed, title: t,
      }));
    });
  }

  // --- Fair Value Gaps: markers (all) + zone lines (recent few) ---
  if (a.has("FVG") && ind.fvg && ind.fvg.length) {
    const markers = ind.fvg.map((g) => g.type === "bullish"
      ? { time: g.time, position: "belowBar", color: "#26a69a", shape: "arrowUp", text: "FVG" }
      : { time: g.time, position: "aboveBar", color: "#ef5350", shape: "arrowDown", text: "FVG" });
    markers.sort((x, y) => x.time - y.time);
    pane.candle.setMarkers(markers);
    ind.fvg.slice(-6).forEach((g) => {
      const col = g.type === "bullish" ? "rgba(38,166,154,0.5)" : "rgba(239,83,80,0.5)";
      [g.top, g.bottom].forEach((p) => {
        pane.priceLines.push(pane.candle.createPriceLine({
          price: p, color: col, lineWidth: 1, lineStyle: LWC.LineStyle.Dotted,
        }));
      });
    });
  }

  // --- bottom oscillators (own stacked scales) ---
  if (a.has("VOL")) {
    const v = pane.chart.addHistogramSeries({
      priceScaleId: "vol", priceFormat: { type: "volume" }, lastValueVisible: false,
    });
    v.setData(d.volume || []);
    pane.extra.push(v);
    pane.chart.priceScale("vol").applyOptions({ scaleMargins: layout.VOL, borderVisible: false });
  }
  if (a.has("RSI")) {
    const r = addLine(pane, "rsi", ind.rsi, { color: "#b39ddb", lineWidth: 1.5 });
    [70, 30].forEach((lvl) => pane.priceLines.push(r.createPriceLine({
      price: lvl, color: "rgba(150,150,170,0.4)", lineWidth: 1, lineStyle: LWC.LineStyle.Dashed,
    })));
    pane.chart.priceScale("rsi").applyOptions({ scaleMargins: layout.RSI, borderVisible: false });
  }
  if (a.has("MACD")) {
    const h = pane.chart.addHistogramSeries({ priceScaleId: "macd", lastValueVisible: false });
    h.setData(ind.macd.hist || []);
    pane.extra.push(h);
    addLine(pane, "macd", ind.macd.macd,   { color: "#42a5f5", lineWidth: 1 });
    addLine(pane, "macd", ind.macd.signal, { color: "#ff7043", lineWidth: 1 });
    pane.chart.priceScale("macd").applyOptions({ scaleMargins: layout.MACD, borderVisible: false });
  }
}

/* ---------------- market session badges ---------------- */
function parts(tz) {
  const f = new Intl.DateTimeFormat("en-US", {
    timeZone: tz, hour12: false, weekday: "short", hour: "2-digit", minute: "2-digit",
  });
  const o = {};
  f.formatToParts(new Date()).forEach((p) => { o[p.type] = p.value; });
  return { wd: o.weekday, mins: (+o.hour % 24) * 60 + (+o.minute) };
}
function isOpen(mkt) {
  if (mkt === "Crypto") return true;
  const tz = mkt === "IDX" ? "Asia/Jakarta" : "America/New_York";
  const { wd, mins } = parts(tz);
  if (wd === "Sat" || wd === "Sun") return false;
  // IDX 09:00–16:00 WIB; US (NYSE) 09:30–16:00 ET.
  return mkt === "IDX" ? (mins >= 540 && mins < 960) : (mins >= 570 && mins < 960);
}
function updateSessions() {
  document.querySelectorAll("#sessions .badge").forEach((el) => {
    const open = isOpen(el.dataset.mkt);
    el.classList.toggle("open", open);
    el.classList.toggle("closed", !open);
    el.querySelector("i").title = open ? "open" : "closed";
  });
}

/* ---------------- boot ---------------- */
document.getElementById("paneButtons").addEventListener("click", (e) => {
  const btn = e.target.closest("button");
  if (!btn) return;
  document.querySelectorAll("#paneButtons button").forEach((b) => b.classList.remove("active"));
  btn.classList.add("active");
  buildPanes(+btn.dataset.n);
});

updateSessions();
setInterval(updateSessions, 30000);
buildPanes(4);
