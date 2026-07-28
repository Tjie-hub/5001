# Economic Mechanism Taxonomy

**Version:** 1.0 · **Status:** Canonical (candidate — inherits an unsigned L1; see §0.3) · **Layer:** L1 — Scientific Foundation
**Owner:** Chief Research Scientist · **Last Updated:** 2026-07-15 · **Supersedes:** — (initial version)
**Realized in v3:** none. Program P0's `gate_config` family scoping consumes mechanism identity but does not implement this taxonomy.
**Scientific basis:** [[01_SCIENTIFIC_FOUNDATION]] §3.4 (mechanism classes M1–M6 — **closed set**), §3.3 (causal order, R8), §7 (mechanism primacy, R18), §5.3 (falsification modes F1–F9), §3.1 (entities that exist)
**Governance:** [[RESEARCH_OS_MASTER_ROADMAP]] §2 (L1), [[DECISION_LOG]] **D-020**

---

## 0. Authority and scope

### 0.1 The subordination rule

[[01_SCIENTIFIC_FOUNDATION]] §3.4 declares six mechanism classes **M1–M6** and states: *"The taxonomy is a closed set at the class level and open at the instance level: a proposed mechanism that fits no class is either a novel class — requiring an amendment to this document and CRO approval — or is not a mechanism."*

This document operates in the space L1 left open. It **sub-divides** each class into named mechanisms and specifies each to the depth R9 demands. It does not add a class, remove a class, or re-define a class.

> **Rule M-1 (justified by §3.4, D-020):** Every sub-class here is numbered `M<class>.<n>` and inherits its parent's definition unaltered. A proposed mechanism that fits no sub-class but fits a class is a **new sub-class** — an amendment to *this* document. A proposed mechanism that fits no class is **not a mechanism** and cannot be admitted by adding a sub-class here. The numbering is the guardrail: there is no `M7.x`, and this document has no authority to create one.

### 0.2 Generic by construction

This taxonomy is **market-independent**. Sub-classes describe causal structures available in any order-driven market. Venue-specific instantiation lives in [[MARKET_INEFFICIENCY_TAXONOMY]], which is IDX-grounded. Any example appearing here is illustrative and carries no evidential weight (E0 — [[01_SCIENTIFIC_FOUNDATION]] §4.2).

The separation is load-bearing rather than tidy-minded: a mechanism is a *causal structure*, and the same structure appearing in two venues is one mechanism observed twice, not two mechanisms. Collapsing the two documents would make every venue-specific finding look like a new mechanism, which is how a taxonomy silently becomes a list of results.

### 0.3 Baseline inheritance (binding)

Authored against [[01_SCIENTIFIC_FOUNDATION]] v1.0 — **certified-ready, NOT FROZEN**; one open condition (independent adversarial sign-off, [[DECISION_LOG]] **D-018/D-019**). If review alters M1–M6, every sub-class beneath the altered class is void pending reclassification, not grandfathered.

---

## 1. The sub-class schema

Eight mandatory fields. Each discharges a specific L1 requirement; a sub-class missing any field is not specified, and R9 refuses it at registration.

| Field | Discharges |
|---|---|
| **Definition** | §3.4 — the structural claim |
| **Economic intuition** | P2 — why a constraint produces deviation |
| **Institutional participants** | **R9** — a class without a named participant class is not a classification |
| **Expected market conditions** | §5.2.4 — scope; a claim without scope is unfalsifiable everywhere |
| **Causal chain** | **R8** — stated at design/constraint level, tested at measurement level |
| **Expected observable consequences** | R8 — evidence flows upward |
| **Competing explanations** | §4.3, R3 — a test that cannot discriminate has zero severity |
| **Falsification criteria** | **R14** — the observation that refutes it, statable in one sentence (§5.1) |

> **Rule M-2 (justified by R8):** The *Causal chain* field must begin at a **constraint on a participant class** and terminate at an **observable**. A chain that begins at an observable is not a causal chain; it is a correlation with arrows drawn on it. This is the single most common counterfeit and it is not detectable by inspecting the conclusion — only by inspecting where the chain starts.

> **Rule M-3 (justified by §7.3, R18):** The *Competing explanations* field is not a literature courtesy. Per §7.3, a competent economist can supply a plausible mechanism for **any** result including its opposite; the mechanism requirement does its work **only** if the mechanism is authored blind to the result. Enumerating rivals *in advance* is what converts a mechanism from an unfalsifiable story into a risked claim. A sub-class with an empty rivals field is one whose author has not yet tried to be wrong.

---

## 2. M1 · Inventory / risk-bearing

**Parent (L1 §3.4):** liquidity suppliers hold undesired inventory under risk limits; compensation is demanded for absorbing imbalance.

**What unifies the sub-classes:** the deviation is *payment for bearing risk*, and it **reverts** as the risk is transferred. Reversion is M1's signature and its discriminating prediction against M2.

---

### M1.1 · Inventory-imbalance mean reversion

| | |
|---|---|
| **Definition** | A liquidity supplier absorbing one-sided flow accumulates inventory away from target and adjusts quotes to attract offsetting flow, displacing price temporarily. |
| **Economic intuition** | The supplier is not forecasting; the supplier is *paying to be relieved*. Price moves not because value changed but because the supplier's willingness to hold changed. |
| **Institutional participants** | Designated market makers, opportunistic liquidity providers, principal desks — any agent quoting two-sided under an inventory limit. |
| **Expected market conditions** | Any continuous-auction session. Magnitude rises with imbalance size relative to depth, and with supplier risk aversion (volatility). Absent where suppliers can lay off instantly. |
| **Causal chain** | Inventory limit binds on supplier *(constraint)* → supplier skews quotes to attract offsetting flow *(behavior)* → skewed quotes shift the executable price *(flow→price)* → transient displacement *(price formation)* → **mean reversion at inventory-clearing horizon** *(observable)*. |
| **Expected observable consequences** | Price displacement correlated with signed imbalance, **reverting** at a horizon matching plausible inventory clearing; magnitude inverse to depth; symmetric in sign. |
| **Competing explanations** | **M2.1 (adverse selection)** — predicts the same displacement but **without** reversion. **M4.2 (forced deleveraging)** — same one-sided flow, different cause. **M5.4 (overreaction)** — same reversion, no supplier involved. |
| **Falsification criteria** | *"If M1.1 were false, displacement conditional on imbalance would not revert."* Refuted by: displacement that is permanent (→ M2.1); reversion uncorrelated with depth; reversion present where no supplier bears inventory. |

---

### M1.2 · Risk-limit liquidity withdrawal

| | |
|---|---|
| **Definition** | When a supplier's risk limit binds, the supplier withdraws rather than re-prices, removing depth discontinuously and amplifying the price impact of subsequent flow. |
| **Economic intuition** | A binding limit is not a steeper supply curve — it is the *absence* of a supply curve. The mechanism predicts a **discontinuity**, not a slope change, and that is what makes it separable from M1.1. |
| **Institutional participants** | Suppliers under hard risk mandates; conditional-liquidity participants with no quoting obligation. |
| **Expected market conditions** | Stress and high-volatility states; concentrated in venues without affirmative quoting obligations. Absent in calm. |
| **Causal chain** | Volatility rises → risk limit binds *(constraint)* → supplier exits rather than widening *(behavior)* → depth vanishes discontinuously *(flow)* → identical flow now produces larger impact *(price formation)* → **state-dependent impact function** *(observable)*. |
| **Expected observable consequences** | Impact-per-unit-flow rising discontinuously with a stress proxy; depth collapse preceding rather than following price moves; hysteresis in re-entry. |
| **Competing explanations** | **M2.3 (quote fade)** — also withdraws, but on *toxicity* not *risk limits*; the two are near-inseparable in observation. **M4.2** — a demand-side story for the same event. **M6.4 (halt dynamics)** — venue rules, not supplier choice. |
| **Falsification criteria** | *"If M1.2 were false, impact-per-unit-flow would not jump at any stress threshold."* Refuted by: smooth impact scaling; withdrawal that follows rather than precedes price moves. |

---

### M1.3 · Capital-commitment premium

| | |
|---|---|
| **Definition** | Immediacy at size commands a premium reflecting the supplier's cost of committing balance-sheet capital, distinct from the compensation for directional inventory risk. |
| **Economic intuition** | Two costs are being conflated across the field: the *risk* of holding and the *capital* consumed by holding. Under a binding capital constraint the second exists even if the first is hedged — which is why this is a sub-class rather than a facet of M1.1. |
| **Institutional participants** | Balance-sheet-constrained intermediaries; block liquidity providers. |
| **Expected market conditions** | Where trade size is large relative to normal flow; where intermediary capital is scarce. **Predicts a time-varying premium tracking intermediary capital**, not asset volatility — the discriminating prediction. |
| **Causal chain** | Capital constraint binds on intermediary *(constraint)* → intermediary prices immediacy above expected inventory cost *(behavior)* → block executes away from mid *(flow→price)* → **premium scales with size and with intermediary capital scarcity** *(observable)*. |
| **Expected observable consequences** | Concave/convex premium in trade size; premium co-moving with intermediary balance-sheet proxies **independently of volatility**. |
| **Competing explanations** | **M1.1** — inventory risk, which co-moves with volatility rather than with capital. **M2.1** — large trades are informative, so the premium may be adverse selection. **M3.3** — impact convexity without any capital story. |
| **Falsification criteria** | *"If M1.3 were false, the size premium would track volatility alone and be invariant to intermediary capital."* Refuted by that invariance. |

---

## 3. M2 · Information asymmetry

**Parent (L1 §3.4):** some participants know more; others must quote anyway; an adverse-selection premium is embedded in price.

**What unifies the sub-classes:** the deviation is **permanent**. Information, once traded on, does not revert. Permanence is M2's signature and the discriminating prediction against M1 — and per [[MARKET_INEFFICIENCY_TAXONOMY]] §4, separating them is the central identification problem of D2.

---

### M2.1 · Adverse-selection spread component

| | |
|---|---|
| **Definition** | A supplier who cannot distinguish informed from uninformed counterparties embeds an expected-loss premium in every quote, so that transaction prices move permanently in the direction of executed flow. |
| **Economic intuition** | The supplier loses to the informed and must recover it from the uninformed. The spread is not a fee for a service; it is a **cross-subsidy priced under uncertainty about who is on the other side**. |
| **Institutional participants** | Suppliers (uninformed by role) versus informed traders (fundamental, order-flow, or latency-informed). |
| **Expected market conditions** | Any market with heterogeneous information. Rises around information events and in names with concentrated informed participation. **Never zero** — a genuinely symmetric-information market has no supplier. |
| **Causal chain** | Informed participants exist and are unidentifiable *(constraint)* → supplier widens quotes to cover expected loss *(behavior)* → informed trade selectively against stale quotes *(flow)* → price incorporates the information *(price formation)* → **permanent, non-reverting component of price change conditional on signed flow** *(observable)*. |
| **Expected observable consequences** | Permanent component of price impact; widening around information events; permanence varying by participant-class proxy. |
| **Competing explanations** | **M1.1** — same displacement, but reverting. **M5.4** — extrapolative flow that *looks* informed ex post because it moved price. **M4.1** — mandated flow is uninformed yet moves price permanently if the demand curve slopes, which mimics M2.1's signature exactly. |
| **Falsification criteria** | *"If M2.1 were false, the price change conditional on signed flow would fully revert."* Refuted by full reversion (→ M1.1); by permanence uncorrelated with any information proxy; by permanence identical for flow known to be uninformed. |

---

### M2.2 · Informed-flow price-discovery lead

| | |
|---|---|
| **Definition** | Where an identifiable participant class systematically holds superior information, that class's net flow leads price discovery, and prices deviate from post-discovery value during the interval before the information is fully incorporated. |
| **Economic intuition** | Information does not enter price instantaneously; it enters *through trades*. If some class trades on it first, its flow is a leading indicator of where price is going — **not because the flow causes it, but because both are consequences of the information**. Getting that direction wrong is a category error, and it is the most common one in flow research. |
| **Institutional participants** | The informed class must be **named** (R9): foreign institutions, corporate insiders, specialist desks. "Smart money" is not a participant class. |
| **Expected market conditions** | Where an informational advantage plausibly exists *and is observable to us at the fidelity claimed* (**A3**, **LIM1**). Absent where classification is unavailable. |
| **Causal chain** | Class C holds superior information *(constraint on others)* → C trades directionally *(behavior)* → C's net flow precedes the price adjustment *(flow)* → price converges to informed value *(price formation)* → **lead–lag between classified net flow and subsequent return** *(observable)*. |
| **Expected observable consequences** | Predictive relation from classified net flow to subsequent return; **absence of reversion**; strengthening around information events. |
| **Competing explanations** | **M1.1** — the same lead–lag arises mechanically from inventory with no information. **M5.1 (attention)** — the "informed" class may simply be faster, not better-informed. **Reverse causation** — the class may be *following* price. **Classification artifact** — the proxy may label flow *by* its outcome, which is **F7 look-ahead** wearing a participant label and is the dominant failure mode here. |
| **Falsification criteria** | *"If M2.2 were false, class C's net flow would carry no information about subsequent return beyond what price itself carries."* Refuted by: no incremental predictive content; reversion (→ M1.1); the relation vanishing under strictly point-in-time classification. |

---

### M2.3 · Toxicity-driven quote fade

| | |
|---|---|
| **Definition** | Suppliers estimate flow toxicity in real time and withdraw when it rises, so that available liquidity is systematically least present exactly when it is most demanded. |
| **Economic intuition** | Suppliers cannot identify informed counterparties individually but *can* estimate the population rate. The response is conditional withdrawal — which means **displayed liquidity is a biased estimate of executable liquidity**, and biased in the direction that hurts. |
| **Institutional participants** | Suppliers running toxicity estimation; latency-advantaged participants. |
| **Expected market conditions** | Elevated where flow is unusually one-sided or fast. |
| **Causal chain** | Supplier estimates toxicity is rising *(constraint: expected loss)* → supplier cancels/withdraws *(behavior)* → depth falls conditional on toxicity *(flow)* → impact rises for the toxic flow *(price formation)* → **realized impact exceeding depth-implied impact, conditionally** *(observable)*. |
| **Expected observable consequences** | Systematic gap between ex-ante displayed depth and ex-post realized impact; gap widening with toxicity proxies; cancellation rates rising before impact. |
| **Competing explanations** | **M1.2** — withdrawal on risk limits rather than toxicity; **near-inseparable without cancellation data**, which the institution does not hold (L3 microstructure = Future/Institutional, [[RESEARCH_OS_MASTER_ROADMAP]] §3 P5). **M6.4** — venue-mandated withdrawal. |
| **Falsification criteria** | *"If M2.3 were false, realized impact would match depth-implied impact regardless of toxicity."* Refuted by that match. **Practically:** this sub-class is currently **untestable at our data fidelity** — a fact recorded here rather than discovered at G1. |

---

## 4. M3 · Liquidity / price-impact compensation

**Parent (L1 §3.4):** trading is costly and costs scale with size; illiquid assets are discounted for expected impact.

**What unifies the sub-classes:** the deviation is compensation for a **cost**, not for a risk or an information gap. **M3 carries a permanent category hazard**: compensation for a real cost is a *fair price*, not an inefficiency. Every M3 sub-class is one step from **F1** (mechanistic incoherence — there is no deviation, only a price), and that is the first thing any M3 claim must survive.

---

### M3.1 · Illiquidity level premium

| | |
|---|---|
| **Definition** | Assets that are persistently costly to trade are priced at a discount, so expected returns are higher by an amount related to expected transaction cost. |
| **Economic intuition** | An investor with an uncertain horizon must be paid to accept the possibility of exiting into a thin book. |
| **Institutional participants** | Any horizon-uncertain investor; **absent** for a genuinely infinite-horizon holder — which is the sub-class's sharpest testable implication and rarely tested. |
| **Expected market conditions** | Cross-sectional and persistent. Larger where arbitrage capital is scarce (§6.4). |
| **Causal chain** | Trading costs are real and horizon is uncertain *(constraint)* → investors discount costly-to-exit assets *(behavior)* → persistent valuation gap *(price formation)* → **cross-sectional return dispersion related to cost proxies** *(observable)*. |
| **Expected observable consequences** | Return dispersion related to realized-cost proxies; relation surviving controls for risk; **weakening as measured cost falls**. |
| **Competing explanations** | **Risk compensation** — illiquid assets may simply be riskier; the premium is then fair and there is no inefficiency (**F1**). **M3.2** — the premium may be for *liquidity risk*, not level. **Omitted variable** — illiquidity proxies load on size, age, and coverage. |
| **Falsification criteria** | *"If M3.1 were false, the return–cost relation would vanish net of realistic friction."* Refuted by **F4**. **Note:** refutation by F4 is the *expected and correct* outcome if the premium is fair. Gross-of-cost confirmation is uninformative by construction. |

---

### M3.2 · Liquidity-risk premium

| | |
|---|---|
| **Definition** | Beyond the level of illiquidity, its *variation* is priced: assets whose liquidity deteriorates when aggregate liquidity deteriorates command additional compensation. |
| **Economic intuition** | An asset that becomes untradeable exactly when you need to trade is worse than one that is merely expensive to trade always. The *covariance* is the priced object — which makes this a distinct claim from M3.1, testable only with a time series of a market-wide state. |
| **Institutional participants** | Investors facing state-contingent liquidation needs — leveraged holders, funds facing redemption (linking to M4.2). |
| **Expected market conditions** | Requires an identifiable aggregate liquidity state. **Rests on A5** (regimes are constructs, never measurements) — the corpus's self-declared weakest assumption. |
| **Causal chain** | Aggregate liquidity is time-varying and liquidation need is state-contingent *(constraint)* → investors demand compensation for liquidity covariance *(behavior)* → assets with high covariance are discounted *(price formation)* → **return dispersion related to liquidity beta, incremental to level** *(observable)*. |
| **Expected observable consequences** | Liquidity-beta-related dispersion incremental to M3.1; concentration in stress; commonality in liquidity across assets. |
| **Competing explanations** | **M3.1** — level and covariance are strongly collinear, so incremental content is the whole test. **M1.2** — supplier withdrawal *generates* liquidity commonality without any pricing story. **F5** — the entire relation may be a crisis-regime artifact. |
| **Falsification criteria** | *"If M3.2 were false, liquidity beta would carry no return information incremental to liquidity level."* Refuted by no incremental content — the likeliest outcome, and the reason this sub-class must be tested *against* M3.1 rather than against zero. |

---

### M3.3 · Impact-convexity compensation

| | |
|---|---|
| **Definition** | Because impact is non-linear in size, participants who must transact large fractions of available liquidity face disproportionate cost, and prices deviate around such episodes by more than proportional to the flow. |
| **Economic intuition** | Impact convexity means the *marginal* trade is more expensive than the average. Where a participant cannot split (M4), the convexity is fully borne and fully expressed in price. |
| **Institutional participants** | Size-constrained-to-trade participants: index replicators, forced sellers, block seekers. |
| **Expected market conditions** | Where trade size is large relative to depth — i.e. **precisely where our data is thinnest and our sample smallest** (LIM4). |
| **Causal chain** | Impact is convex in size *(constraint of the mechanism, D1/D2)* → a participant unable to split bears the convexity *(behavior)* → price displaces super-proportionally *(price formation)* → **non-linear impact–size relation, with overshoot and partial reversion** *(observable)*. |
| **Expected observable consequences** | Measured convexity in impact; overshoot–reversion around large episodes; magnitude scaling with size/depth. |
| **Competing explanations** | **M1.3** — capital-commitment premium produces the same size dependence. **M2.1** — large trades are informative, so convexity may be information, not cost. **M4.2** — forced flow is large *and* uninformed. |
| **Falsification criteria** | *"If M3.3 were false, impact would be linear in size."* Refuted by measured linearity; by convexity fully explained by information content (→ M2.1). |

---

## 5. M4 · Mandated / price-insensitive flow

**Parent (L1 §3.4):** participants who must trade regardless of price; the demand curve is not flat.

**What unifies the sub-classes:** the trader is **not expressing a view**. This is the taxonomy's strongest origination family, because the constraint is *documentary* — a prospectus, a margin agreement, a regulation — and therefore not conjectural. **The weakness is symmetric and must be stated:** the constraint binds the *causers*, never the *correctors*, so M4 origination is cheap while M4 persistence is expensive. Per R16 that reverses the usual difficulty and makes M4 claims easier to author and harder to defend.

---

### M4.1 · Benchmark-replication flow

| | |
|---|---|
| **Definition** | Managers mandated to replicate a benchmark transact its composition changes irrespective of price, and the resulting demand displaces price against a downward-sloping supply curve. |
| **Economic intuition** | The manager's objective is **tracking error, not return**. Paying a worse price is not a failure by the manager's own metric — which is exactly why the behavior does not self-correct. |
| **Institutional participants** | Index funds, ETFs, benchmark-constrained mandates. |
| **Expected market conditions** | Around benchmark composition events. Magnitude scales with mandated demand relative to float and liquidity. |
| **Causal chain** | Replication mandate binds *(constraint, documentary)* → manager transacts at the effective date regardless of price *(behavior)* → concentrated one-sided demand *(flow)* → displacement against a sloping curve *(price formation)* → **abnormal return in the event window with post-event reversal** *(observable)*. |
| **Expected observable consequences** | Event-window abnormal return; post-event partial reversal; scaling with mandated demand/liquidity. |
| **Competing explanations** | **Information** — inclusion may *signal* quality, in which case the move is permanent and correct (→ M2.1), and the two are distinguished only by the reversal. **M5.1** — inclusion is an attention event. **Anticipation** — if arbitrageurs front-run, the effect migrates to the announcement, so a null at the effective date does **not** refute the mechanism. That last point matters: a naive test looks in the wrong window and calls it a refutation. |
| **Falsification criteria** | *"If M4.1 were false, mandated demand would produce no price displacement — the supply curve would be flat."* Refuted by no displacement **in any window** (announcement through effective); by displacement that does not revert (→ information). |

---

### M4.2 · Forced deleveraging

| | |
|---|---|
| **Definition** | Participants facing margin calls or redemptions liquidate irrespective of price, producing displacement exceeding the initiating shock's information content, reverting once forced supply is exhausted. |
| **Economic intuition** | The seller has no choice and no view. The information content of the sale is *about the seller*, not about the asset — which is precisely what makes the displacement excessive and reversible. |
| **Institutional participants** | Leveraged holders under margin agreements; funds facing redemption; anyone with a hard stop mandated by risk policy. |
| **Expected market conditions** | Stress states only. **Episodic and clustered** — which means conventional sampling assumptions fail, not merely strain. |
| **Causal chain** | Leverage constraint binds after an adverse move *(constraint)* → holder must liquidate regardless of price *(behavior)* → one-sided supply into thinning depth *(flow, interacting with M1.2)* → overshoot *(price formation)* → **overshoot–reversion conditional on stress proxies** *(observable)*. |
| **Expected observable consequences** | Displacement exceeding shock information content; reversion after forced supply exhausts; concentration in leverage proxies. |
| **Competing explanations** | **Information** — the shock may simply be that bad, and the "overshoot" the correct price. **M1.2** — supplier withdrawal produces identical observables from the supply side. **M5.4** — panic overreaction with no leverage. **F5** — regime artifact. |
| **Falsification criteria** | *"If M4.2 were false, stress-state displacement would not revert."* Refuted by non-reversion; by displacement uncorrelated with leverage proxies. |

---

### M4.3 · Mandate-driven exclusion

| | |
|---|---|
| **Definition** | Where a class of participants is prohibited from holding a class of assets, the excluded assets are priced by a smaller, differently-constrained population, producing a persistent valuation gap. |
| **Economic intuition** | Price is set by the *marginal eligible* participant. Shrink the eligible set and the marginal participant changes — so the gap is not a mispricing being corrected, it is **the equilibrium of a different market**. |
| **Institutional participants** | Mandate-constrained institutions; the residual eligible population. |
| **Expected market conditions** | Persistent while the mandate persists. |
| **Causal chain** | Mandate prohibits holding *(constraint, documentary)* → eligible population shrinks *(behavior)* → the marginal holder's constraints differ *(flow)* → persistent gap *(price formation)* → **cross-sectional differential related to exclusion status** *(observable)*. |
| **Expected observable consequences** | Persistent differential across the exclusion boundary; discontinuity at the threshold; the gap responding to mandate changes rather than to capital flows. |
| **Competing explanations** | **Risk** — excluded assets may be genuinely different (**F1**: two assets, not one deviation). **M3.1** — excluded assets are typically illiquid. **Selection** — the exclusion criterion may itself correlate with fundamentals, which is the hardest rival to exclude. |
| **Falsification criteria** | *"If M4.3 were false, the differential would be explained by the assets' own properties rather than by eligibility."* Refuted by the differential vanishing under controls; by no discontinuity at the boundary. |

---

### M4.4 · Fund-flow-driven trading

| | |
|---|---|
| **Definition** | Managers receiving or losing capital transact their existing portfolio pro-rata irrespective of price views, transmitting flow shocks into holdings on a basis unrelated to those holdings' value. |
| **Economic intuition** | The trade is caused by *someone else's* subscription decision. The asset is bought because it is held, not because it is attractive — a mechanism whose defining feature is that price and value are causally decoupled at the point of trade. |
| **Institutional participants** | Open-end funds and their holdings. |
| **Expected market conditions** | Where fund ownership is concentrated and flows are volatile. |
| **Causal chain** | Fund receives/loses capital *(constraint: mandate to stay invested)* → manager scales the portfolio pro-rata *(behavior)* → correlated flow across unrelated holdings *(flow)* → co-movement unrelated to fundamentals *(price formation)* → **excess co-movement among commonly-held assets** *(observable)*. |
| **Expected observable consequences** | Co-movement among co-held assets beyond fundamental correlation; return related to estimated flow pressure; reversion at a horizon matching flow persistence. |
| **Competing explanations** | **Fundamental correlation** — co-held assets are often genuinely similar, which is the reason they are co-held; this rival is the whole test. **M2.2** — fund flows may be informed. **Reverse causation** — flows may *follow* returns, which is well-documented and mimics the observable exactly. |
| **Falsification criteria** | *"If M4.4 were false, co-movement among co-held assets would be fully explained by fundamental similarity."* Refuted by that explanation sufficing; by flows demonstrably following rather than leading returns. |

---

## 6. M5 · Behavioral / attention

**Parent (L1 §3.4):** bounded rationality, salience, anchoring, disposition; systematic mispricing where the bias is unarbitraged.

**Two warnings that apply to every sub-class here, and that L1 states plainly.**

> **R9 (L1 §3.4):** *"M5 · Behavioral without a named bias, a named participant class, and a reason that bias is unarbitraged is not a classification."* M5 is the class most often used as a label for "we found something and it isn't rational." That use is prohibited.

> **§6.4 (L1):** deviation is *a priori* **least** likely where capital is abundant and the mechanism is most studied. M5 is the most studied class in finance. **Per §6.4 and P4, M5 sub-classes carry an elevated prior against them** — not because behavioral effects are unreal, but because ours is not the institution that will find the ones everyone has looked for.

---

### M5.1 · Limited attention / salience

| | |
|---|---|
| **Definition** | Public information that is not salient is incorporated with delay, so price adjustment speed relates to the information's presentation rather than its content. |
| **Economic intuition** | Attention is scarce. Information that must be *sought* is incorporated more slowly than information that arrives. |
| **Institutional participants** | **Must be named (R9).** Retail participants; coverage-constrained institutions. "The market is inattentive" is not a participant class and is refused at G1. |
| **Expected market conditions** | Low-coverage instruments; information released off-cycle. **Predicts its own decay** as processing cost falls — see falsification. |
| **Causal chain** | Attention is scarce and processing is costly *(constraint)* → participants process salient information first *(behavior)* → non-salient information enters price via delayed trading *(flow)* → gradual adjustment *(price formation)* → **drift related to salience proxies** *(observable)*. |
| **Expected observable consequences** | Delayed adjustment with delay related to salience; drift concentrated in low-coverage names; **monotonic attenuation over the sample**. |
| **Competing explanations** | **M3.1** — low-coverage names are illiquid, so slow adjustment may be cost, not attention. **M2.2** — slow adjustment may be gradual information arrival, which is efficient. **F3** — the behavioral family denominator is effectively unbounded (**LIM3**: the denominator is estimable, not knowable). |
| **Falsification criteria** | *"If M5.1 were false, adjustment speed would relate to information content, not to its presentation."* **Also refuted by stability:** a stable attention effect over a long sample contradicts the mechanism, since the constraint (processing cost) demonstrably fell over any such sample. Confirmation of the effect and refutation of the mechanism arrive in the same result — an unusually sharp test, and one that must be pre-specified to be usable. |

---

### M5.2 · Anchoring and underreaction

| | |
|---|---|
| **Definition** | Participants updating insufficiently from a salient reference point cause price to adjust partially to news, with the remainder arriving as drift. |
| **Economic intuition** | The reference point is sticky; belief revision is incomplete; the residual adjustment leaks out over time. |
| **Institutional participants** | Must be named (R9). |
| **Expected market conditions** | Following discrete, quantifiable news against an available anchor. |
| **Causal chain** | A salient anchor exists and updating is insufficient *(constraint)* → participants under-revise *(behavior)* → flow adjusts partially *(flow)* → partial price adjustment *(price formation)* → **post-event drift in the news direction** *(observable)*. |
| **Expected observable consequences** | Drift in the surprise direction; magnitude related to anchor salience; drift terminating at full adjustment. |
| **Competing explanations** | **Risk** — drift may be compensation for post-event uncertainty. **M3.1** — drift may be slow adjustment through friction. **M5.1** — attention predicts the same drift from a different constraint; **the two are not separable by the drift alone**, only by what predicts its magnitude. **F3** — post-event drift is the single most-searched effect in the literature. |
| **Falsification criteria** | *"If M5.2 were false, adjustment would be complete at the event and no drift would follow."* Refuted by complete adjustment; by drift unrelated to any anchor measure. |

---

### M5.3 · Disposition effect

| | |
|---|---|
| **Definition** | Holders whose propensity to sell depends on unrealized gain/loss rather than forward value make the supply curve reference-dependent, impeding adjustment in a direction predicted by aggregate holding basis. |
| **Economic intuition** | Realizing a loss is psychologically distinct from holding one. Supply therefore depends on *purchase history*, which is not a forward-looking variable and has no place in an efficient supply curve. |
| **Institutional participants** | Must be named (R9). Typically high-retail-participation names. |
| **Expected market conditions** | Where holding basis is dispersed and estimable. **The barrier that sustains the mechanism (basis is unobservable) is the same barrier that blocks its measurement** — a structural problem, not a data gap. |
| **Causal chain** | Preferences are reference-dependent *(constraint)* → holders sell winners and hold losers *(behavior)* → supply depends on basis *(flow)* → asymmetric adjustment *(price formation)* → **adjustment asymmetry related to basis proxies** *(observable)*. |
| **Expected observable consequences** | Asymmetric adjustment conditional on estimated aggregate basis; volume asymmetry around the basis. |
| **Competing explanations** | **Mechanical volume effects** — basis proxies are constructed from price and volume history, so they correlate with momentum and turnover by construction. This is not a rival to control for; it is a **near-tautology risk**, and it kills most designs at **F1**. **M5.2** — anchoring predicts similar asymmetry. |
| **Falsification criteria** | *"If M5.3 were false, adjustment asymmetry would be unrelated to aggregate holding basis once volume history is controlled."* Refuted by that control eliminating the effect. |

---

### M5.4 · Extrapolative overreaction

| | |
|---|---|
| **Definition** | Participants extrapolating recent outcomes push price beyond the level justified by information, producing displacement that subsequently reverses. |
| **Economic intuition** | Recent returns are treated as evidence about future returns. The resulting flow is self-reinforcing until it exhausts. |
| **Institutional participants** | Must be named (R9). |
| **Expected market conditions** | After sustained directional moves; where feedback traders are a material share. |
| **Causal chain** | Participants extrapolate *(constraint: bounded rationality)* → they buy strength / sell weakness *(behavior)* → self-reinforcing flow *(flow)* → overshoot *(price formation)* → **long-horizon reversal after extended moves** *(observable)*. |
| **Expected observable consequences** | Long-horizon reversal following extended moves; reversal magnitude related to prior move extremity. |
| **Competing explanations** | **M1.1 / M4.2** — both produce overshoot–reversion with no behavioral content whatsoever. **Risk** — the "overshoot" may be a rational response to changed risk. **F3** — reversal is among the most-searched families; **F5** — reversal is strongly regime-dependent. |
| **Falsification criteria** | *"If M5.4 were false, extended moves would not systematically reverse."* Refuted by no reversal; by reversal fully attributable to inventory or forced flow (→ M1.1 / M4.2) — which is the likeliest outcome and is why M5.4 is among the weakest sub-classes here. |

---

## 7. M6 · Market-design artifact

**Parent (L1 §3.4):** venue rules create discontinuities; price paths are constrained by rules, not by value.

**What unifies the sub-classes:** the constraint is **published**. M6 is the only class whose generating constraint is a document anyone can read, which makes origination non-conjectural and makes the barrier **structural** — unarbitrable by any capital quantity. Per [[MARKET_INEFFICIENCY_TAXONOMY]] §5.1 this is the taxonomy's strongest strategic position and the one the field attends to least.

**M6's decay is a step function, not an exponential.** The barrier does not erode through discovery; it ends when the rule ends. Any decay monitor for an M6 mechanism must watch a **rulebook**, not a return series — the only class in this taxonomy for which that is true.

---

### M6.1 · Price-limit binding

| | |
|---|---|
| **Definition** | Where a venue forbids execution beyond a bound, the price path is truncated while the underlying demand is not, so demand is deferred rather than cleared. |
| **Economic intuition** | The rule removes prices from the feasible set. It cannot remove the intent that would have transacted at them — so intent accumulates. |
| **Institutional participants** | All; the constraint is universal and non-negotiable. |
| **Expected market conditions** | When the bound binds — i.e. **in volatility, by construction**, making every price-limit claim regime-correlated a priori (F5 risk is structural, not incidental). |
| **Causal chain** | Venue rule forbids execution beyond bound *(constraint, D1, published)* → intent that would clear beyond it cannot execute *(behavior)* → unexecuted demand persists into the next admissible interval *(flow)* → conditional price path *(price formation)* → **next-interval behavior conditional on the bound having bound** *(observable)*. |
| **Expected observable consequences** | Asymmetric conditional return after band contact; discontinuity in the path at the bound; volume concentration at the bound. |
| **Competing explanations** | **M5.1** — band contact is maximally salient, so attention is a rival for the identical observation. **M5.4** — extreme moves reverse anyway. **M4.2** — the move that hit the band may be forced flow. **Selection** — band contact selects on extreme returns, so any subsequent behavior is conditioned on an extremum. |
| **Falsification criteria** | *"If M6.1 were false, post-contact behavior would be identical to post-extreme-move behavior where no band existed."* Refuted by that identity — which is also the **cleanest available test design**, since the counterfactual is nearly observable in unbanded comparators. |

---

### M6.2 · Auction discontinuity

| | |
|---|---|
| **Definition** | An auction clears a different population of intent under a different rule than continuous trading, so its price deviates from the continuous counterfactual at the same instant. |
| **Economic intuition** | Two matching rules produce two prices. Where a mandate ties participants to *one* of them (M4.1), the tie is what makes the deviation exploitable rather than merely present. |
| **Institutional participants** | Auction-mandated participants; discretionary participants able to choose. |
| **Expected market conditions** | At auction events. Magnitude scales with mandated participation share. |
| **Causal chain** | Venue defines a distinct auction rule *(constraint, D1, published)* → mandated participants must use it *(behavior, M4.1)* → auction population differs from continuous *(flow)* → clearing price differs *(price formation)* → **systematic auction-to-continuous differential** *(observable)*. |
| **Expected observable consequences** | Auction-price deviation from surrounding continuous prices; reversal after; concentration on mandate-heavy dates. |
| **Competing explanations** | **M2.1** — the auction may aggregate information rather than distort, making its price *better*, not worse. **M1.1** — suppliers manage inventory into the auction. **Microstructure noise** — the "deviation" may be a bid–ask artifact of comparing an auction price to a continuous mid. |
| **Falsification criteria** | *"If M6.2 were false, the auction price would be an unbiased estimate of the contemporaneous continuous price."* Refuted by unbiasedness. |

---

### M6.3 · Tick-size constraint

| | |
|---|---|
| **Definition** | A minimum price increment prevents quotes from expressing the price that would obtain under continuous pricing, forcing queue competition to substitute for price competition. |
| **Economic intuition** | When price cannot adjust, something else must. The tick converts price competition into **time priority**, changing who supplies liquidity and at what economics — a different market with the same participants. |
| **Institutional participants** | Liquidity suppliers; queue-priority-advantaged participants. |
| **Expected market conditions** | Where the tick is large relative to the natural spread — i.e. low-priced instruments, and at tick-regime boundaries. |
| **Causal chain** | Tick rule sets a minimum increment *(constraint, D1, published)* → suppliers cannot undercut on price *(behavior)* → competition moves to queue position *(flow)* → spread is rule-bound rather than economics-bound *(price formation)* → **spread clustering at the tick; discontinuity at regime boundaries** *(observable)*. |
| **Expected observable consequences** | Spread pinned at the tick in constrained names; depth and queue behavior changing discontinuously at tick-regime boundaries; execution economics differing across the boundary. |
| **Competing explanations** | **M3.1** — tick-constrained names are typically also low-priced and illiquid, and these are near-collinear. **M1.1** — spread may reflect inventory rather than the tick. **Selection** — tick regimes are assigned *by price*, so any cross-regime comparison compares different assets. That last rival is severe: the regime boundary is not random assignment. |
| **Falsification criteria** | *"If M6.3 were false, spreads would be unaffected by the tick regime — no clustering at the minimum, no discontinuity at boundaries."* Refuted by absence of clustering. |

---

### M6.4 · Halt and resumption dynamics

| | |
|---|---|
| **Definition** | A trading halt suspends the price-formation mechanism while information continues to accumulate, so resumption prices are formed by a discontinuous re-aggregation of intent built up during the suspension. |
| **Economic intuition** | The halt does not pause the world; it pauses the mechanism. Resumption is therefore not a continuation — it is a **new price-formation event** on an accumulated book. |
| **Institutional participants** | All; halt-eligible instruments only. |
| **Expected market conditions** | Around halts — rare, clustered, and triggered by extremes, so **LIM4** (short history caps what is testable) binds hardest here of any sub-class. |
| **Causal chain** | Venue halts trading on a rule trigger *(constraint, D1, published)* → intent accumulates unexecutable *(behavior)* → resumption aggregates it at once *(flow)* → discontinuous re-formation *(price formation)* → **resumption behavior conditional on halt cause and duration** *(observable)*. |
| **Expected observable consequences** | Resumption-price behavior conditional on halt characteristics; volume concentration at resumption; adjustment path differing from unhalted comparators. |
| **Competing explanations** | **M4.2** — halts trigger on the moves forced selling causes. **M5.1** — a halt is maximally salient. **Selection** — halts are triggered by extremes, so post-halt behavior is conditioned on an extremum. **Sample** — halts are so rare that **R2 likely refuses the test**: an underpowered test is not weak evidence, it is no evidence. |
| **Falsification criteria** | *"If M6.4 were false, resumption behavior would match unhalted instruments experiencing equivalent moves."* Refuted by that match. |

---

### M6.5 · Access segmentation

| | |
|---|---|
| **Definition** | Where venue or regulatory rules partition who may hold or trade an instrument, the price is set by the eligible sub-population's constraints rather than the full population's. |
| **Economic intuition** | Price is set by the marginal *eligible* participant. A rule that changes who is eligible changes the price — not by mispricing it, but by **changing which market it is**. |
| **Institutional participants** | The eligible population; the excluded population; the rule-maker. |
| **Expected market conditions** | Persistent while the rule stands. |
| **Causal chain** | Rule restricts eligibility *(constraint, D1, published)* → the excluded cannot express demand *(behavior)* → eligible flow alone sets price *(flow)* → persistent differential *(price formation)* → **cross-partition differential for equivalent claims** *(observable)*. |
| **Expected observable consequences** | Persistent differential across the partition; discontinuity at the binding threshold; response to rule changes rather than to capital flows. |
| **Competing explanations** | **F1 is the leading rival and it is strong**: the two sides of the partition may be genuinely different claims with different rights and liquidity, in which case there is **no deviation, only two assets**. **M3.1** — restricted classes are typically illiquid. **M4.3** — the mandate-side account of the same partition, differing only in whether the constraint is venue rule or investor mandate. |
| **Falsification criteria** | *"If M6.5 were false, the differential would be fully explained by the instruments' differing rights and liquidity."* Refuted by that explanation sufficing. |

---

## 8. Cross-class structure

### 8.1 The reversion–permanence axis

The taxonomy's most useful single discriminator, and the one that carries every D2 test:

| Prediction | Classes | Why |
|---|---|---|
| **Reverts** | M1 (all), M3.3, M4.2, M4.4, M5.4 | The displacement is compensation or pressure; once relieved, price returns |
| **Permanent** | M2 (all), M4.1-if-informational | The displacement is information; information does not un-arrive |
| **Persistent-static** | M3.1, M3.2, M4.3, M6.3, M6.5 | Not a displacement at all — a *level* difference in equilibrium |
| **Rule-conditional** | M6.1, M6.2, M6.4 | The path is constrained; behavior is conditional on the rule binding |

> **Rule M-4 (justified by R8, R3):** A hypothesis must state which cell of this table its mechanism occupies **before testing**, and its test must be capable of distinguishing that cell from the adjacent ones. A test that measures displacement without measuring its persistence has not tested any mechanism — it has measured a correlation. This rule is the operational content of the I5/I7 identification problem ([[MARKET_INEFFICIENCY_TAXONOMY]] §4).

### 8.2 Barrier strength by class

Per **R17**, absent a barrier the default presumption is that the effect does not exist. Classes differ systematically in barrier quality, and this is the taxonomy's principal strategic output:

| Class | Barrier | Erodes with | Strength |
|---|---|---|---|
| **M6** | Structural (published rule) | **Rule change only** — no capital quantity removes it | **Strongest** |
| **M4** | Constraint (documentary mandate) | Correctors' capital — mandate binds causers only | Moderate |
| **M2** | Structural (real informational disadvantage) | Nothing — removing it dissolves the asymmetry | Strong, but often **F1**: fair compensation |
| **M1** | Risk-bearing | Liquidity-provision capital | Weak, and often **F1** |
| **M3** | Cost | **Nothing** — knowing about illiquidity does not create liquidity | Strong, but **F1 hazard is maximal** |
| **M5** | Information / attention | **Processing cost — falls monotonically** | **Weakest** |

**Two conclusions this table forces, both uncomfortable and both correct:**

1. **M6 is the institution's strongest class and M5 is its weakest** — the inverse of the field's attention allocation. This is not a preference; it follows from R17 plus §6.4, and it means the literature's centre of mass is where our prior should be lowest.
2. **M2 and M3 have the strongest barriers *and* the highest F1 risk.** A barrier that is strong because the compensation is *fair* is a barrier around a non-inefficiency. For these classes the persistence question is easy and the **origination question is the hard one** — the reverse of §6.3's usual asymmetry. Getting this backwards produces claims that survive every persistence check and are still not inefficiencies.

---

## 9. Amendment

- **Adding a sub-class:** all eight fields; parent class named; rivals enumerated (Rule M-3); causal chain starting at a constraint (Rule M-2); reversion–permanence cell declared (Rule M-4). CRO approval.
- **Adding a class (M7+):** **not possible here.** Amends [[01_SCIENTIFIC_FOUNDATION]] §3.4 with CRO approval. Rule M-1 exists precisely to make the sub-class route unavailable as a back door — the failure mode being that a mechanism fitting nothing gets admitted as `M5.9` because M5 is vague enough to absorb anything.
- **Retiring a sub-class:** prohibited. A falsified sub-class is annotated with its falsification and retained (**R12**, §4.4). A retired sub-class is a fact about the market.

---

## 10. Traceability

| This document | Extends | Never restates |
|---|---|---|
| Sub-classes M1.1–M6.5 | [[01_SCIENTIFIC_FOUNDATION]] §3.4 (M1–M6) | The six class definitions |
| Causal-chain field | §3.3 (causal order, R8) | R8 itself |
| Competing-explanations field | §7.3 (asymmetric constraint), §4.3 | The retro-fit argument |
| Falsification-criteria field | §5.1 (counterfactual interview), §5.3 (F1–F9) | The mode definitions |
| Rules M-1…M-4 | R8, R9, R18, §3.4, §7.3 | — (new, subordinate) |
| §8.2 barrier strength | §6.3 (barriers), R17, §6.4 | The barrier list |

**Upstream:** [[MARKET_INEFFICIENCY_TAXONOMY]] (its entries cite the classes this document sub-divides). **Downstream:** [[RESEARCH_OBJECT_SCHEMA]] (the Economic Mechanism object's `classification` resolves to a sub-class here) · [[HYPOTHESIS_LIFECYCLE]] (G1 admissibility requires a sub-class) · [[LITERATURE_RESEARCH_STANDARD]] (extraction targets sub-classes, §5).
