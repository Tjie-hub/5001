# engine/health_report.py
"""Daily pre-market health report builder (C8).

Called at 08:45 WIB by the scheduler. Covers:
  - Composite risk score + tier
  - VPIN avg + % above thresholds
  - Market breadth (adv/dec + % above MA20)
  - Foreign flow 5-day net
  - IHSG technicals (death cross, support breaks)
"""

_TIER_EMOJI = {
    'CRITICAL': '🚨', 'RED': '🔴', 'ORANGE': '🟠', 'YELLOW': '🟡', 'GREEN': '🟢',
}


def _fmt_idr(value) -> str:
    """Format IDR amount in billions with sign."""
    if value is None:
        return 'N/A'
    b = value / 1_000_000_000
    sign = '+' if b >= 0 else ''
    return f"{sign}{b:.1f}B"


def build_market_health_report(
    date_str: str,
    risk: dict,
    vpin: dict,
    accdist: dict,
    breadth: dict,
    tech: dict,
    foreign_net_5d,
) -> str:
    """Build Telegram-formatted daily market health report."""
    tier = risk.get('tier', 'GREEN')
    score = risk.get('score', 0.0)
    emoji = _TIER_EMOJI.get(tier, '📊')

    lines = [
        f"{emoji} <b>Market Health Report — {date_str}</b>",
        "",
        f"<b>Risk Score:</b> {score:.1f}/100 — <b>{tier}</b>",
        "",
    ]

    # VPIN
    avg_vpin = vpin.get('avg_vpin')
    vpin_label = vpin.get('label', 'N/A')
    pct_095 = vpin.get('pct_above_095', 0.0)
    pct_08 = vpin.get('pct_above_08', 0.0)
    n_vpin = vpin.get('tickers_with_vpin', 0)
    if avg_vpin is not None:
        lines.append(
            f"<b>VPIN:</b> {avg_vpin:.4f} ({vpin_label}) "
            f"| &gt;0.8: {pct_08:.1f}% | &gt;0.95: {pct_095:.1f}% "
            f"[{n_vpin} tickers]"
        )
    else:
        lines.append("<b>VPIN:</b> N/A (no data)")

    # Breadth
    pct_adv = breadth.get('pct_advancing', 0.0)
    pct_ma20 = breadth.get('pct_above_ma20', 0.0)
    adv = breadth.get('advancers', 0)
    dec = breadth.get('decliners', 0)
    b_label = breadth.get('label', 'N/A')
    lines.append(
        f"<b>Breadth:</b> {pct_adv:.1f}% adv ({adv}↑/{dec}↓) "
        f"| MA20: {pct_ma20:.1f}% above [{b_label}]"
    )

    # AccDist
    dist_pct = accdist.get('dist_pct', 0.0)
    acc_pct = accdist.get('acc_pct', 0.0)
    ad_label = accdist.get('label', 'N/A')
    lines.append(
        f"<b>AccDist:</b> Dist {dist_pct:.1f}% / Acc {acc_pct:.1f}% [{ad_label}]"
    )

    # Foreign flow
    lines.append(f"<b>Foreign 5d:</b> {_fmt_idr(foreign_net_5d)} IDR")

    # IHSG technicals
    close = tech.get('close')
    ma5 = tech.get('ma5')
    ma20 = tech.get('ma20')
    t_label = tech.get('label', 'N/A')
    death_cross = tech.get('death_cross', False)
    lower_high = tech.get('lower_high', False)
    breaks = tech.get('support_breaks') or []

    tech_parts = [f"<b>IHSG:</b> {close:,.0f}" if close else "<b>IHSG:</b> N/A"]
    if ma5:
        tech_parts.append(f"MA5={ma5:,.0f}")
    if ma20:
        tech_parts.append(f"MA20={ma20:,.0f}")
    tech_parts.append(f"[{t_label}]")
    lines.append(" | ".join(tech_parts))

    flags = []
    if death_cross:
        flags.append("Death Cross ❌")
    if lower_high:
        flags.append("Lower High ❌")
    if breaks:
        flags.append(f"Broke {', '.join(breaks)} ❌")
    if flags:
        lines.append(f"⚠️ {' | '.join(flags)}")

    lines.append("")
    lines.append("<i>Pre-market report generated at 08:45 WIB</i>")

    return "\n".join(lines)
