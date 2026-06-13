// static/format.js — shared value/number formatting (UMD: browser + node)
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.IDXFormat = factory();
}(typeof self !== 'undefined' ? self : this, function () {
  function fmtSigned(v) {
    if (v == null || isNaN(v)) return '—';
    var s = v >= 0 ? '+' : '-';
    var a = Math.abs(v);
    if (a >= 1e12) return s + (a / 1e12).toFixed(2) + 'T';
    if (a >= 1e9)  return s + (a / 1e9).toFixed(1) + 'B';
    if (a >= 1e6)  return s + (a / 1e6).toFixed(1) + 'M';
    if (a >= 1e3)  return s + (a / 1e3).toFixed(0) + 'K';
    return s + a.toFixed(0);
  }
  return { fmtSigned: fmtSigned };
}));
