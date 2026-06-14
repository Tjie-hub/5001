// static/shell.js — unified shell: global state (clock, nav, search, firm-mode)
// Cross-page navigation is full-page (every page extends base.html, so chrome is
// identical and shell.css/shell.js are cached). Workspace hash-tabs ('/#scanner')
// stay client-side and are handled by the workspace itself.
(function () {
  'use strict';

  // ── WIB clock ───────────────────────────────────────────────
  function tickClock() {
    const el = document.getElementById('wib-time');
    if (!el) return;
    const wib = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Jakarta' }));
    const p = n => String(n).padStart(2, '0');
    el.textContent = `${p(wib.getHours())}:${p(wib.getMinutes())}:${p(wib.getSeconds())}`;
  }
  setInterval(tickClock, 1000); tickClock();

  // ── Active nav highlight ────────────────────────────────────
  function syncActiveNav() {
    const path = location.pathname;
    const hash = location.hash;
    document.querySelectorAll('[data-nav]').forEach(a => {
      const href = a.getAttribute('href');
      let active = false;
      if (href.startsWith('/#')) {
        active = (path === '/' && hash === href.slice(1));
      } else {
        active = href === path || (href !== '/' && path.startsWith(href));
      }
      a.classList.toggle('active', active);
    });
  }
  window.addEventListener('hashchange', syncActiveNav);
  syncActiveNav();

  // ── Global ticker search → /dive/<t> ────────────────────────
  const search = document.getElementById('global-search');
  if (search) {
    search.addEventListener('keydown', e => {
      if (e.key === 'Enter' && search.value.trim()) {
        location.href = '/dive/' + search.value.trim().toUpperCase();
      }
    });
    document.addEventListener('keydown', e => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); search.focus(); }
    });
  }

  // ── Global agent firm-mode pill (off / shadow / enforce) ────
  function updateFirmPill(active, enforce) {
    const off = document.getElementById('firm-off');
    const shadow = document.getElementById('firm-shadow');
    const enf = document.getElementById('firm-enforce');
    const pill = document.getElementById('firm-pill');
    if (!off || !pill) return;
    [off, shadow, enf].forEach(b => { b.style.background = '#111'; b.style.color = '#555'; b.style.fontWeight = ''; });
    if (!active) {
      off.style.background = '#1f1f1f'; off.style.color = '#fff'; off.style.fontWeight = '700';
      pill.style.borderColor = '#333';
    } else if (enforce) {
      enf.style.background = '#052e16'; enf.style.color = '#4ade80'; enf.style.fontWeight = '700';
      pill.style.borderColor = '#16a34a';
    } else {
      shadow.style.background = '#2d2200'; shadow.style.color = '#fbbf24'; shadow.style.fontWeight = '700';
      pill.style.borderColor = '#92400e';
    }
  }

  function applyFirmMode(mode) {
    fetch('/api/agent/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode })
    })
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(s => updateFirmPill(s.active, s.enforce))
      .catch(() => { if (typeof showToast === 'function') showToast('Agent firm update failed', 'error'); });
  }

  function setFirmMode(mode) {
    const modal = document.getElementById('enforce-modal');
    if (mode === 'enforce' && modal) {
      modal.style.display = 'flex';
      document.getElementById('enforce-ok').onclick = () => { modal.style.display = 'none'; applyFirmMode('enforce'); };
      document.getElementById('enforce-cancel').onclick = () => { modal.style.display = 'none'; };
      return;
    }
    applyFirmMode(mode);
  }
  window.setFirmMode = setFirmMode;

  if (document.getElementById('firm-pill')) {
    fetch('/api/agent/status').then(r => r.json()).then(s => updateFirmPill(s.active, s.enforce)).catch(() => {});
  }
})();
