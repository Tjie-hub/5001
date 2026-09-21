# BANDAR FILTER — ADVERSARIAL CHALLENGE RESULT

**Date:** 2026-09-15 · Challenge object: "bandar buyer-share ≥ ~0.55–0.60 ⇒ veto"
**Method:** 9 declared attacks (`bandar_filter_challenge.py` → `cache/bandar_filter_challenge.json`).
Definitions fixed in advance: heavy = share ≥ θ; control = share < 0.45; suspension-clean base;
no post-hoc thresholds or combinations.

## FINAL DECISION: **C — ARTIFACT / DEAD. Bandar family CLOSED.**

The proposed filter is **a vendor-coverage selection artifact, not bandar information.**

### What was killed, by attack

1. **Threshold surface:** heavy-cell h5 is only −0.14..−0.20% at every θ; spreads vs buyer-light run
   −6..−43bp with sign flips (2/4 negative at most θ; 4/4 only at θ=0.65 with trivial magnitude;
   reverted to 2/4 at 0.70/0.75, where h20 turns **positive** +0.41/+0.43%). No monotonic plateau.
2. **Coverage-selection (decisive):** uncovered names h5 **+0.33%** vs covered +0.13% (low-share) and
   −0.20% (high-share). FM on the full base: the **coverage flag itself** carries β = **−0.57%,
   t = −4.26**; buyer-share controlling for coverage collapses to **β = +0.06%, t = +0.66**. The
   signal was "names the vendor covers underperform," not "broker-breadth buying is bad."
3. **Price-condition:** spreads grow with move size (−48bp h5 at ≥+3%, −132bp at ≥+5%) — but this is
   coverage×momentum (covered names that ran hard underperform), not bandar information.
4. **Flow-control ladder:** β −0.43% (no controls) → −0.52% (platform flow) → **−0.06%, t = −0.50
   with a liquidity control**. The residual is liquidity/small-cap selection.
5. **Label consistency:** buyer-share contrast exists within label classes (label adds nothing);
   the Acc-label's FM (−0.67%, t=−6.13) controlling buyer-share shows both are proxies of the same
   covered-junk selection. Terminology enforced: this is **broker-breadth buyer share on the
   vendor-defined bandar dataset** — it does not measure "bandar accumulation."
6. **PIT:** 74.7% rows evening-stamped (post-close, safe), 24.4% intraday-stamped (revisable),
   0.9% pre-open-stamped (cannot contain same-day data). **Historical PIT not establishable** —
   and moot given attack 2.
7. **Size/liquidity:** heavy-vs-light spread is inconsistent across tiers (ADV-top −31bp, ADV-mid
   −57bp, ADV-bottom **+11bp** — sign reverses). Not a liquid-name phenomenon; not stable anywhere.
8. **Alternatives:** on the covered base, the **coverage flag alone is as strong a veto as
   buyer-share** (β −0.47%, t=−4.79 vs −0.41%, t=−5.15). The filter does not beat its own
   selection instrument; the platform-divergence veto from the adversarial pass is informationally
   distinct (23.5% overlap, both survive mutual controls — but that survivor belongs to the platform
   flow family, not bandar).
9. **False discovery:** no thresholds or combinations beyond the declared set were examined.

### Survived / killed / unknown / further research?

- **Survived:** nothing as bandar information. (Platform-outflow-into-strength remains the one
  avoidance candidate from earlier — its home is the flow family, unaffected by this closure.)
- **Killed:** the buyer-share veto (coverage artifact); bandar entry constructions (prior pass);
  label-based constructions (proxy the same artifact).
- **Unknown:** why the vendor covers what it covers (selection mechanism unknowable from repo data);
  historical PIT of the vendor table.
- **Further bandar research:** **not justified.** The only detectable signal in the table is
  "covered ⇒ worse," which is a data-availability artifact confounded with small-cap junk. Family
  closed.

No registration. No execution. No registry change.
