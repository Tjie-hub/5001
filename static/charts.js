/* static/charts.js — multi-pane lightweight-charts viewer
   Depends on global LightweightCharts (loaded in workspace.html). */
(function () {
  const LC = window.LightweightCharts;
  const ALL_INDS = ['vp', 'fvg', 'sr', 'vwap', 'vwma', 'patterns'];
  const state = { panes: 4, focused: 0, inds: new Set(['vwap']), charts: [] };

  function el(tag, cls, html) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }

  async function fetchJSON(url, opts) {
    const r = await fetch(url, opts);
    if (!r.ok) throw new Error(url + ' -> ' + r.status);
    return r.json();
  }

  async function loadCandles(ticker, tf) {
    if (tf === '1h') {
      const j = await fetchJSON(`/api/ticker/${ticker}/ohlcv?tf=1h`);
      return (j.candles || []).map(c => ({
        time: c.time, open: c.open, high: c.high, low: c.low, close: c.close }));
    }
    const freq = tf === 'W' ? 'W' : tf === 'M' ? 'ME' : 'D';
    const j = await fetchJSON(`/api/ticker/${ticker}/ohlcv/${freq}?limit=300`);
    return (j.bars || []).map(b => ({
      time: b.date, open: b.open, high: b.high, low: b.low, close: b.close }));
  }

  function syncTV(symbol) {
    fetch('/api/chart/tv/sync', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol })
    }).catch(() => {});
  }

  async function renderPane(paneEl, i) {
    const ticker = paneEl.querySelector('input').value.trim().toUpperCase();
    const tf = paneEl.querySelector('select').value;
    const chartHost = paneEl.querySelector('.cv-chart');
    const statEl = paneEl.querySelector('.cv-stat');
    chartHost.innerHTML = '';
    statEl.textContent = '';
    statEl.style.color = '';
    if (!ticker) return;

    const chart = LC.createChart(chartHost, {
      layout: { background: { color: '#0f162e' }, textColor: '#97a3c0' },
      grid: { vertLines: { visible: false }, horzLines: { color: '#151f3a' } },
      rightPriceScale: { borderColor: '#1b2547' },
      timeScale: { borderColor: '#1b2547' },
      autoSize: true,
    });
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#10b981', downColor: '#ef4444',
      wickUpColor: '#10b981', wickDownColor: '#ef4444', borderVisible: false });
    let candles = [];
    try { candles = await loadCandles(ticker, tf); } catch (e) { statEl.textContent = 'no data'; return; }
    candleSeries.setData(candles);

    // overlays
    try {
      const inds = [...state.inds].filter(x => ALL_INDS.includes(x));
      if (inds.length) {
        const ov = await fetchJSON(`/api/chart/${ticker}/indicators?tf=${tf}&inds=${inds.join(',')}`);
        applyOverlays(chart, candleSeries, candles, ov);
      }
    } catch (e) { /* overlays are best-effort */ }

    // delta sub-pane stat
    if (tf === '1h' || tf === 'D') {
      try {
        const date = candles.length ? String(candles[candles.length - 1].time).slice(0, 10) : '';
        if (date) {
          const d = await fetchJSON(`/api/chart/${ticker}/delta?date=${date}&parts=stats`);
          if (d.stats && d.stats.note) {
            statEl.textContent = d.stats.note;
          } else if (d.stats) {
            const sign = d.stats.total_delta >= 0 ? '+' : '';
            statEl.textContent = `Δ ${sign}${d.stats.total_delta}`;
            statEl.style.color = d.stats.total_delta >= 0 ? '#10b981' : '#ef4444';
          }
        }
      } catch (e) { /* delta optional */ }
    }
    chart.timeScale().fitContent();
    state.charts[i] = chart;
  }

  function applyOverlays(chart, candleSeries, candles, ov) {
    if (ov.vwap && ov.vwap.length) {
      const s = chart.addLineSeries({ color: '#f59e0b', lineWidth: 1 });
      s.setData(ov.vwap.map(p => ({ time: p.date, value: p.value })));
    }
    if (ov.vwma && ov.vwma.length) {
      const s = chart.addLineSeries({ color: '#3b82f6', lineWidth: 1 });
      s.setData(ov.vwma.map(p => ({ time: p.date, value: p.value })));
    }
    if (ov.sr) {
      (ov.sr.resistance || []).forEach(p =>
        candleSeries.createPriceLine({ price: p, color: '#ef4444', lineStyle: 2, lineWidth: 1 }));
      (ov.sr.support || []).forEach(p =>
        candleSeries.createPriceLine({ price: p, color: '#10b981', lineStyle: 2, lineWidth: 1 }));
    }
    if (ov.vp && ov.vp.poc != null) {
      candleSeries.createPriceLine({ price: ov.vp.poc, color: '#818cf8', lineWidth: 2, title: 'POC' });
      candleSeries.createPriceLine({ price: ov.vp.vah, color: '#6366f1', lineStyle: 1, title: 'VAH' });
      candleSeries.createPriceLine({ price: ov.vp.val, color: '#6366f1', lineStyle: 1, title: 'VAL' });
    }
    if (ov.patterns && ov.patterns.length) {
      const marks = ov.patterns.map(p => ({
        time: p.date,
        position: p.dir === 'bear' ? 'aboveBar' : 'belowBar',
        color: p.dir === 'bear' ? '#ef4444' : p.dir === 'bull' ? '#10b981' : '#97a3c0',
        shape: p.dir === 'bear' ? 'arrowDown' : 'arrowUp',
        text: p.pattern.replace(/_/g, ' ')
      }));
      candleSeries.setMarkers(marks);
    }
    if (ov.fvg && ov.fvg.length) {
      ov.fvg.slice(-12).forEach(g => {
        candleSeries.createPriceLine({
          price: (g.top + g.bottom) / 2,
          color: g.type === 'bull' ? 'rgba(16,185,129,0.5)' : 'rgba(239,68,68,0.5)',
          lineStyle: 3, lineWidth: 1, title: 'FVG' });
      });
    }
  }

  function renderAll() {
    document.querySelectorAll('.cv-pane').forEach((p, i) => renderPane(p, i));
  }

  function buildPane(i) {
    const pane = el('div', 'cv-pane' + (i === state.focused ? ' focused' : ''));
    pane.dataset.idx = i;
    const head = el('div', 'cv-pane-head');
    const inp = el('input'); inp.value = i === 0 ? 'BBCA' : '';
    inp.placeholder = 'ticker';
    const sel = el('select');
    ['1h', 'D', 'W', 'M'].forEach(t => {
      const o = el('option', null, t); o.value = t; if (t === 'D') o.selected = true; sel.appendChild(o);
    });
    const stat = el('span', 'cv-stat');
    head.append(inp, sel, stat);
    const chart = el('div', 'cv-chart');
    pane.append(head, chart);
    pane.addEventListener('click', () => {
      state.focused = i;
      document.querySelectorAll('.cv-pane').forEach(x => x.classList.remove('focused'));
      pane.classList.add('focused');
    });
    const reload = () => { renderPane(pane, i); if (inp.value.trim()) syncTV(inp.value.trim().toUpperCase()); };
    inp.addEventListener('change', reload);
    sel.addEventListener('change', () => renderPane(pane, i));
    return pane;
  }

  function buildGrid() {
    const grid = document.getElementById('cv-grid');
    if (!grid) return;
    grid.innerHTML = '';
    grid.dataset.panes = state.panes;
    for (let i = 0; i < state.panes; i++) grid.appendChild(buildPane(i));
    renderAll();
  }

  function buildToolbar() {
    const tb = document.getElementById('cv-toolbar');
    if (!tb) return;
    tb.innerHTML = '';
    [1, 2, 4, 6].forEach(n => {
      const b = el('button', 'cv-layout-btn' + (n === state.panes ? ' active' : ''), n + '');
      b.addEventListener('click', () => {
        state.panes = n; localStorage.setItem('cv_panes', n);
        tb.querySelectorAll('.cv-layout-btn').forEach(x => x.classList.remove('active'));
        b.classList.add('active'); buildGrid();
      });
      tb.appendChild(b);
    });
    ALL_INDS.forEach(ind => {
      const c = el('button', 'cv-ind-chip' + (state.inds.has(ind) ? ' on' : ''), ind.toUpperCase());
      c.addEventListener('click', () => {
        if (state.inds.has(ind)) state.inds.delete(ind); else state.inds.add(ind);
        c.classList.toggle('on'); renderAll();
      });
      tb.appendChild(c);
    });
    const dot = el('span', 'cv-tv-dot'); dot.id = 'cv-tv-dot';
    const lbl = el('span', null, 'TV'); lbl.style.fontSize = '11px'; lbl.style.color = '#97a3c0';
    tb.append(dot, lbl);
    fetch('/api/chart/tv/status').then(r => r.json()).then(j => {
      if (j.available) dot.classList.add('live');
    }).catch(() => {});
  }

  window.ChartViewer = {
    init() {
      const saved = parseInt(localStorage.getItem('cv_panes') || '4', 10);
      state.panes = [1, 2, 4, 6].includes(saved) ? saved : 4;
      buildToolbar();
      buildGrid();
    },
    // called by workspace when a signal row is clicked
    loadTicker(ticker) {
      const grid = document.getElementById('cv-grid');
      if (!grid) return;
      const pane = grid.children[state.focused] || grid.children[0];
      if (!pane) return;
      pane.querySelector('input').value = ticker.toUpperCase();
      renderPane(pane, state.focused);
      syncTV(ticker.toUpperCase());
    }
  };
})();
