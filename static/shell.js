// static/shell.js — unified shell: global state + History-API router
(function () {
  'use strict';

  // ── WIB clock ───────────────────────────────────────────────
  function tickClock() {
    const el = document.getElementById('wib-time');
    if (!el) return;
    const now = new Date(Date.now() + (7 * 60 + new Date().getTimezoneOffset()) * 60000);
    el.textContent = now.toTimeString().slice(0, 8);
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

  // ── History-API router: progressive enhancement ─────────────
  const MOUNT = 'app-content';
  async function navigate(url, push) {
    const main = document.getElementById(MOUNT);
    if (!main) { location.href = url; return; }
    main.setAttribute('aria-busy', 'true');
    try {
      const res = await fetch(url, { headers: { 'X-Shell-Nav': '1' } });
      if (!res.ok) throw new Error(res.status);
      const html = await res.text();
      const doc = new DOMParser().parseFromString(html, 'text/html');
      const next = doc.getElementById(MOUNT);
      if (!next) throw new Error('no mount in response');
      main.replaceWith(next);
      if (push) history.pushState({ url }, '', url);
      window.scrollTo(0, 0);
      syncActiveNav();
      document.dispatchEvent(new CustomEvent('shell:mounted', { detail: { url } }));
    } catch (e) {
      location.href = url; // graceful fallback to full navigation
    }
  }

  document.addEventListener('click', e => {
    const a = e.target.closest('a[data-nav]');
    if (!a || e.metaKey || e.ctrlKey || e.shiftKey || a.target === '_blank') return;
    const url = a.getAttribute('href');
    if (!url || url.startsWith('http')) return;
    // In-workspace hash tabs (/#scanner) are handled by the workspace itself
    // when already on '/'; only route them when navigating from another page.
    if (url.startsWith('/#') && location.pathname === '/') { syncActiveNav(); return; }
    e.preventDefault();
    navigate(url, true);
  });
  window.addEventListener('popstate', () => navigate(location.pathname + location.hash, false));
  window.addEventListener('hashchange', syncActiveNav);

  // ── Global ticker search → /dive/<t> ────────────────────────
  const search = document.getElementById('global-search');
  if (search) {
    search.addEventListener('keydown', e => {
      if (e.key === 'Enter' && search.value.trim()) {
        navigate('/dive/' + search.value.trim().toUpperCase(), true);
      }
    });
    document.addEventListener('keydown', e => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); search.focus(); }
    });
  }

  syncActiveNav();
  window.__shellNavigate = navigate; // expose for view scripts
})();
