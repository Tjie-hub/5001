# Research Protocol

> **If you are new here, this is the document you follow. Start at §2.**

**Version:** 1.0 · **Status:** Canonical (candidate — inherits an unsigned L1; see §0.4) · **Layer:** L2 — Research Architecture (procedural face)
**Owner:** Chief Research Officer · **Last Updated:** 2026-07-15 · **Supersedes:** — (initial version). **Does NOT supersede** [[RESEARCH_OPERATING_MODEL]] or [[MARKET_INEFFICIENCY_RESEARCH_PIPELINE]] — see §0.2.
**Realized in v3:** partial — `research/knowledge` (registration), `research/gatekeeper` (S7–S8), `failure_registry` (S10-negative), research/production fence. **S1–S2 and S9 have no realization.**
**Scientific basis:** [[01_SCIENTIFIC_FOUNDATION]] — the whole document. This protocol is that document made executable by one person on one Monday morning.
**Governance:** [[RESEARCH_OS_MASTER_ROADMAP]] · [[DECISION_LOG]] **D-021**

---

## 0. About this document

### 0.1 The question this layer answers

> *"If a researcher joins tomorrow, what do they follow to produce research consistent with the Scientific Foundation?"*

**They follow this document.** Everything else in the Institutional Research Protocol is invoked *from* here at the point it is needed:

| Document | Invoked at |
|---|---|
| **This protocol** | **Entry point. Read first.** |
| [[EXPERIMENT_STANDARD]] | S6 — when you run an experiment |
| [[REPLICATION_STANDARD]] | S9 — when you replicate, or when someone replicates you |
| [[PEER_REVIEW_STANDARD]] | S9 — when you review. **Inert at N=1 — see §7** |
| [[RESEARCH_QUALITY_STANDARD]] | Continuously — what "good" means here |
| [[RESEARCH_PROGRAM_PLAYBOOK]] | When you start, review, or terminate a Program |

### 0.2 Specification vs procedure — why this is not a duplicate

The corpus already specifies *what must be true*. It has never specified *what you do*.

> **Rule PR-1 (justified by D-021):** **A specification states what must be true. A protocol states what you do, in what order, and what to do when you cannot.** Where a specification exists, this protocol **cites and sequences** it. It never restates it.

| Owned elsewhere — cited, never restated | Owned here |
|---|---|
| The ten stages S1–S10 ([[MARKET_INEFFICIENCY_RESEARCH_PIPELINE]]) | **The order you actually work in, and where it differs from the diagram** (§4) |
| The four gates G1–G4 ([[RESEARCH_OPERATING_MODEL]] §6) | **What you bring to a gate and what happens when it refuses you** |
| The five roles ([[RESEARCH_OPERATING_MODEL]] §5) | **Which hat you are wearing, and what to do when you are wearing all five** (§7) |
| The twelve states ([[HYPOTHESIS_LIFECYCLE]]) | **What to type, and when** |
| The rules R1–R20, the tiers E0–E7 ([[01_SCIENTIFIC_FOUNDATION]]) | **The six you must know by heart on day one** (§3) |

### 0.3 How to read this

**Do not read the corpus front to back.** It is ~5,000 lines and reading it linearly will teach you nothing you can act on. §2 is a reading order that gets you productive in a day and correct in a week.

### 0.4 Baseline inheritance (binding)

Authored against [[01_SCIENTIFIC_FOUNDATION]] v1.0 — **certified-ready but NOT FROZEN**; one open condition, an external adversarial signature ([[DECISION_LOG]] **D-018/D-019**). If review alters the rules this protocol sequences, the affected steps are **void pending re-derivation, not grandfathered** (§0.4 of L1).

---

## 1. What this institution is, in six sentences

Read this even if you read nothing else.

1. **We study a real, rule-bound, adversarial, time-varying market** — not a distribution (**P1**).
2. **An inefficiency is a claim about a mechanism, never about a dataset.** A pattern is evidence for or against such a claim; it is never the claim (**P2**).
3. **Nothing here is ever proven.** Knowledge is what has been attacked competently and has not yet broken (**P3**).
4. **The scarce resource is not data or compute. It is our ability to believe our own conclusions** (**P4**). Every rule below exists to protect that. A rule that does not, is bureaucracy and should be deleted.
5. **We attack our own claims before the market does**, and we keep our failures as carefully as our successes (**R12**).
6. **We are not trying to be right. We are trying to be correctable** (§1.5).

---

## 2. Your first week

### Day 1 — read, in this order

| # | Read | Why | Time |
|---|---|---|---|
| 1 | **This document, §1–§6** | The protocol | 30 min |
| 2 | [[01_SCIENTIFIC_FOUNDATION]] **§1, §2, §5** | Worldview, epistemology, **how a claim is killed**. Skip §0 and §13–§16 for now | 90 min |
| 3 | [[01_SCIENTIFIC_FOUNDATION]] **§10 (LIM1–LIM8)** | **What we cannot know.** Read this before anything that makes you optimistic | 20 min |
| 4 | [[MARKET_INEFFICIENCY_TAXONOMY]] **§5** | What the institution currently believes: **nothing.** Zero validated inefficiencies | 10 min |
| 5 | [[RESEARCH_QUALITY_STANDARD]] | What "good" means here — **it is not what you expect** | 30 min |

**Do not read on day 1:** the object schema, the evidence model's promotion tables, the program standard. You will need them at the moment you need them, and §4 tells you when.

### Day 2–5 — do this

1. **Read the Failure Library end to end.** Every entry. It is the most valuable document in the institution and it is short. It tells you what has already been tried and how it died.
2. **Read [[DECISION_LOG]] §4 (rationale debt) and [[KNOWLEDGE_CORPUS_DELIVERY]] §5 (gaps).** These are the institution's open wounds, written down. An institution that hides them from a new hire is lying to itself first.
3. **Replicate one existing result** ([[REPLICATION_STANDARD]]). Not to check it — **to discover what our specifications actually fail to say.** You are the only person who will ever read them without already knowing the answer, and that window closes in about two weeks. **This is the highest-value thing you will do all year and it is available only now** (**LIM5**).
4. **Do not propose a hypothesis in week 1.** You do not yet know what has been tried.

### The one thing to internalize

> **You will find a pattern in the data in your first month. It will be exciting. It will be statistically significant.**
>
> **It is worth nothing.** It is **E0** — *"guaranteed obtainable by search; discriminates nothing."* Per **R10** it is not weak evidence, it is a **category error**.
>
> **What you do:** record an Observation (§5.1), and stop. Not "stop for now." Stop. The path from there to a claim runs through **§4**, and it does not shorten because the pattern is strong.

---

## 3. The six rules you must know by heart

Everything else you can look up. These six you must have internalized, because **each is violated by a move that feels correct at the moment you make it.**

| # | Rule | The move it prevents | Why you will want to make it |
|---|---|---|---|
| **1** | **R5 — criteria before evidence** | Choosing a threshold after seeing the result | The result is *right there*. The threshold looks arbitrary. **§2.3: criteria chosen after the data are seen are not criteria; they are descriptions.** |
| **2** | **R7.3 — no retro-fitted mechanism** | Finding a pattern, then writing the economics | You *can* explain it. That is the problem — per **§7.3** you could have explained the opposite just as well. It constrains nothing, so it **cannot be wrong** |
| **3** | **R7.5 — never narrow the family** | Reporting the survivor of 40 tests as one test | The other 39 "weren't real attempts." **They were. The denominator is part of the claim** |
| **4** | **R15 — no rescue** | Adding a filter you discovered from the failure | The filter genuinely explains the failure. **§5.4: rescuing looks identical to surviving — and it destroys the institution invisibly** |
| **5** | **R6 — custody is enforced, not requested** | "Just a quick look" at out-of-sample data | It is one glance. **§2.4: every unlogged glance silently converts OOS into in-sample while leaving its appearance unchanged** |
| **6** | **R2 — the test must have been able to fail** | Reporting an underpowered result as "suggestive" | It feels like weak evidence. **It is no evidence.** An error of kind, not degree |

> **Rule PR-2:** If you catch yourself about to do any of the six, **stop and write it down in the Failure Library or the Decision Log.** The temptation is data about the institution. Per §5.3 the distribution of how we nearly went wrong is the most useful thing we can learn about ourselves — and it is invisible unless recorded at the moment it happens.

### 3.1 Why these are enforced by structure, not by your discipline

You are honest. That is not sufficient, and the corpus says so plainly:

> **R6:** *"A prohibition that relies on a researcher's discipline is a statement of intent, not a control."*

**The reason is not that you might cheat. It is that a rescued claim and a survived claim are indistinguishable by inspection** (§5.4, §7.3). Nobody — including you, including a reviewer, including the CRO — can tell them apart afterward by looking at the result. So the rules live in the state machine ([[HYPOTHESIS_LIFECYCLE]] §5), where the move is **unexpressible** rather than merely forbidden.

If you find yourself able to make one of the six moves, **that is a defect in the system, not a permission.** Report it.

---

## 4. The working order

The pipeline diagram ([[MARKET_INEFFICIENCY_RESEARCH_PIPELINE]] §1) shows S1→S10 as a straight line. **It is not one.** Here is what you actually do.

```
                    ┌─────────────────────────────────────┐
                    │  S1 LITERATURE  ←── the only source  │
                    │  (blind mechanisms)                  │
                    └──────────────┬──────────────────────┘
                                   │
   ┌──────────────┐                ▼
   │ OBSERVATION  │      ┌──────────────────┐
   │   (E0)       │─────▶│ S2 MECHANISM     │  ◀── MOST WORK DIES HERE (F1)
   │  free, any   │prompt│  authored BLIND   │      cost: zero
   │  amount      │ only └────────┬─────────┘
   └──────────────┘               │
                                  ▼
                        ┌───────────────────┐
                        │ S3 REGISTRATION   │  ◀── G1. THE ONE-WAY DOOR
                        │  all six of §5.2  │      after this: FROZEN
                        └────────┬──────────┘
                                 │
                     ┌───────────┴───────────┐
                     ▼                       ▼
              ┌────────────┐         ┌──────────────┐
              │ S4 DATA    │         │ S5 FEATURES  │  G2
              └─────┬──────┘         └──────┬───────┘
                    └───────────┬───────────┘
                                ▼
                      ┌───────────────────┐
                      │ S6 EXPERIMENT     │  ◀── OOS opens ONCE. Logged.
                      │  [[EXPERIMENT_STANDARD]] │
                      └────────┬──────────┘
                               ▼
                  ┌─────────────────────────┐
                  │ S7 STATS  →  S8 COST    │  G3 · gatekeeper
                  └────────────┬────────────┘
                               ▼
                      ┌───────────────────┐
                      │ S9 PEER REVIEW    │  G4 ◀── ██ BLOCKED AT N=1 ██
                      │ [[PEER_REVIEW_STANDARD]] │      see §7
                      └────────┬──────────┘
                               ▼
                ┌──────────────┴──────────────┐
                ▼                             ▼
        ┌───────────────┐            ┌─────────────────┐
        │ S10 KNOWLEDGE │            │ FAILURE LIBRARY │
        │  (unreachable │            │  ◀── the usual  │
        │   at N=1)     │            │      outcome    │
        └───────────────┘            └─────────────────┘
                                              │
                                              ▼
                                     NEW hypothesis, new
                                     registration, counted
                                     afresh (R15). NEVER a
                                     retry of the old one.
```

### 4.1 Four things the diagram gets wrong

**(a) Observation is not a stage, and it has no path forward.** You will spend much of your time observing. It is free and unlimited in Discovery (§2.4). But **there is no arrow from Observation to Hypothesis except "prompts"** — you cannot promote an observation into a claim ([[HYPOTHESIS_LIFECYCLE]] **OS-9**). The path runs through S2, and S2 must be authored **blind**.

**(b) S1 is not optional and it is not a formality.** Per [[LITERATURE_RESEARCH_STANDARD]] §0.1, literature is **the institution's only structurally-guaranteed source of mechanisms authored blind to our data.** A mechanism you author yourself, after looking at our data, is a **counterfeit** — and per §7.3 it is indistinguishable from a genuine one by inspection. **Skipping S1 does not save time; it invalidates everything downstream.**

**(c) Most of your work should die at S2, and that is the system working.** Per §5.3, **F1 is the privileged death**: it consumes no data, no out-of-sample custody, no multiplicity budget. *"An institution that routinely kills claims at F1 is operating efficiently; one whose failures cluster at F2–F4 is spending its scarcest resources to learn things it could have reasoned out."*

**(d) S3 is a door, not a step.** Before G1: refine freely, unlimited, no record needed. After G1: **frozen**. There is no path back ([[HYPOTHESIS_LIFECYCLE]] **HL-2**). Take the time before it; you will not get another chance.

### 4.2 The economics of your day

| Where a claim dies | What it costs | Where you want to be |
|---|---|---|
| **S2 (F1)** — the economics don't work | **Nothing** | **Here. Most of the time.** |
| **S3 (G1 refusal)** — not falsifiable | Nothing | Fine |
| S6 (F2) — the prediction failed | **One OOS window, spent forever** | Sometimes; that is what it is for |
| S7 (F3) — the family ate it | An OOS window + a family slot | Avoidable by counting first |
| S8 (F4) — cost ate it | An OOS window | **Often avoidable by estimating cost at S2** |

> **Rule PR-3 (justified by §5.3, P4):** **Before touching data, estimate the effect size your mechanism predicts and compare it to friction.** If the predicted effect is smaller than the cost of capturing it, the claim is **F4 and dies at S2 for free**. Discovering that at S8 costs an out-of-sample window — a **non-renewable resource** (**R6**) — to learn something arithmetic would have told you in ten minutes.

---

## 5. Procedures

### 5.1 You found something interesting

```
1. STOP. Do not investigate further along this path.
2. Record an Observation (O11).           ← claim: NONE. Structural.
3. Note the custody state you were in.    ← Discovery? Then it is E0. Always.
4. Note how many things you looked at.    ← the family datum. Write it now;
                                             you will not remember later.
5. Ask: is there a mechanism in the LITERATURE that predicts this?
     ├── YES → S1/S2. The mechanism is blind. Proceed.
     └── NO  → Can I author one WITHOUT reference to what I just saw?
              ├── Honestly yes → author it, record `blind_to`, S2.
              └── No / unsure  → STOP. It is a counterfeit (R7.3).
                                 The Observation stands. The claim does not.
```

**Step 5's second branch is the one that matters, and you will not like it.** The honest answer is usually "no" — you have seen the result, so you cannot un-see it. **That is not a failure of your integrity; it is §7.3 operating as designed.** The correct response is to leave the Observation on the record and let a *different* mechanism, from a *different* source, arrive at it later — or never.

### 5.2 You want to register a hypothesis

Bring all six (**§5.2**). Any missing ⇒ **G1 refuses**. Not defers — refuses.

```
[ ] 1. MECHANISM       → M-class sub-class + named constraint + named
                          participant class (R9). Not "behavioral."
[ ] 2. DIRECTION       → sign-specified. "Related to" is not a prediction.
[ ] 3. NULL            → what the world looks like if the mechanism is absent,
                          as a measurable proposition. Not "no effect."
[ ] 4. SCOPE           → universe, horizon, regime, period.
[ ] 5. EX-ANTE CRITERION → including EFFECT SIZE, not significance alone.
                          An effect smaller than its cost is a
                          *confirmed irrelevance* (§5.5).
[ ] 6. FAMILY          → the denominator. Declared now. Never narrowed (R7.5).

[ ] + REFUTATION CONDITION, in ONE sentence (R14):
      "What would we see, in the data we are about to touch,
       if this mechanism were not real?"
      More than one sentence ⇒ it is not a hypothesis. It is an intention.

[ ] + POWER / MDE (R2): could this test have failed?
      If no ⇒ DO NOT RUN IT. It will produce no evidence either way.

[ ] + PERSISTENCE (R16.2): why has nobody already taken this?
      Must cite one of §6.3's seven barriers. No barrier ⇒
      default presumption is THE EFFECT DOES NOT EXIST (R17).
```

> **The last two kill more good-looking hypotheses than everything else combined, and both are free.**

### 5.3 Your hypothesis failed

**This is the normal outcome. It is a first-class institutional product** (**R12**).

```
1. Record a Failure Entry (O8). MANDATORY. Immutable. Never deleted.
2. Attribute to EXACTLY ONE mode F1–F9.
3. DEFEND the attribution (R1 — Duhem-Quine):
   why the mechanism, and not the data / cost model / regime / test?
   A bare "the test failed" is not knowledge.
4. Record which assumptions (A1–A8) proved false.
5. STOP.
```

**Then read this list and do none of it** (**R15**):

- ✗ re-run with adjusted parameters and report the survivor
- ✗ narrow the universe or period until it passes
- ✗ add a filter you discovered from the failure
- ✗ re-label it "needs more data"
- ✗ split it into variants until one survives

> **The only legitimate response:** record the failure and — *if the failure taught a **new** mechanism* — register a **new** hypothesis, with a **new** pre-registration, **counted afresh in the family**. It is N+1. **Never a retry of the Nth.**

**The distinction is exact and it is the most abused boundary in this field:** *learning from failure* is registering a new risked claim. *Rescuing a failure* is editing the old claim until the evidence stops disagreeing.

### 5.4 Your hypothesis passed

**Be more suspicious than when it failed.** A failure is cheap and honest. A pass is expensive and is where every incentive in your body starts pulling in one direction.

```
1. Is the ex-ante criterion met VERBATIM, as frozen at G1?
   Read it from the frozen object. Do not re-derive it.
   Near-miss ⇒ MISS. (R7.4 — moving the criterion deletes the test.)
2. Does it survive friction under the cost model REGISTERED EX ANTE? (F4)
3. Write the SEVERITY argument (R3/EV-3) — in prose, not a p-value:
   "what would have had to be true for this test to have caught the
    error, and was the test in fact capable of that?"
4. Compute the family denominator — the REAL one, including every
   variant, re-run, and dead sibling. (P0's edge died here.)
5. → S9 Peer Review.  ██ At N=1, you stop here. See §7. ██
```

### 5.5 You cannot reproduce something

**It is void. Not pending, not weak — void** (**R19**, **F6**).

Per §8.5, this will sometimes void a result you believe is true, for a reason that feels incidental — a lost seed, an unrecorded environment. **That is the rule working.** An exception granted for a result we like replaces R19 with *"reproducibility is required except when inconvenient."*

**And note where the pressure will come from: the evidence that the claim is true.** That is precisely why the exception is unavailable in advance rather than declined in the moment.

---

## 6. When you disagree with a rule

**You are encouraged to. This is a critical-rationalist institution; a rule immune from criticism is not a rule we should have.**

```
1. Find the RULE (R<n>) and the PROPOSITION (P<n>) that justifies it.
   Every rule cites one. If it cites none, that is a finding — report it.
2. Attack the PROPOSITION, not the rule.
   Every proposition carries a DEFEATER: the observation or argument
   that would refute it (§0.4). Show the defeater holds.
3. If the proposition falls, the rule is VOID — not grandfathered (§0.4).
4. Record it in [[DECISION_LOG]].
```

> **Rule PR-4 (justified by P4):** The test for any rule — existing or proposed — is **P4**: *"if the proposed rule does not measurably reduce the probability that the institution believes something false, it fails P4"* and should be removed. **Apply this to this protocol.** If a step here is ceremony, delete it and record why.

**What is not an argument against a rule:** that it is slow, that it is inconvenient, that you are confident, that the claim is probably true, or that a lot of work is riding on it (**R13** — sunk research cost is not evidence).

---

## 7. ██ The staffing question — read this before you believe you can finish ██

### 7.1 Where you will stop

**At N=1 — one researcher — you cannot complete the pipeline.** Not because of a backlog. **Structurally.**

- **S9/G4 requires adversarial review by someone who is not the author.**
- **LIM6:** adversarial review is *structurally compromised at this scale*.
- **LIM8:** self-certification is *epistemically indistinguishable from genuine certification* — so you cannot even tell whether you did it properly.
- **EV-9:** a single-researcher claim caps at confidence **C2**. **T9 requires C3.**

> **Therefore: at N=1 the institution cannot promote any hypothesis to Accepted Knowledge.** It can do everything else — observe, source literature, author mechanisms, register, experiment, validate, cost, and **record failures**. It cannot *accept*.

**This is the same wall the corpus's own foundation stands at.** [[PHASE_A_FREEZE_CERTIFICATE]] v2.1 is blocked on one condition — an external signature (**D-019**). **The pipeline you are being onboarded into, and the document that would certify it, are stopped by the identical constraint.**

### 7.2 Why the bar is not lowered to meet you

The obvious fix is to weaken G4 to something one person can discharge. Per **ADR-L1-007** — *declare the single-researcher review deficit; do not absorb it* — the institution refuses:

> **Weakening G4 would not make the institution able to accept knowledge. It would make it unable to tell whether it should.**

So we operate at **C2 with the ceiling visible on every claim**, rather than at an apparent C3 with the ceiling hidden. Per **LIM8** the two are indistinguishable from the outside — which is exactly why the choice must be recorded rather than felt.

### 7.3 What changes when you arrive

**This is the part that makes your arrival more than a hire.**

| N | What is reachable | What unlocks |
|---|---|---|
| **N=1** | **C2 ceiling.** Everything except acceptance. Failures, mechanisms, refutations — **all fully available and all valuable** | — |
| **N=2** | **C3 reachable → T9 reachable → G-4 CLOSES** | **One person can adversarially review the other.** [[PEER_REVIEW_STANDARD]] activates. **Accepted Knowledge becomes possible for the first time** |
| **N≥3** | Role separation per [[RESEARCH_OPERATING_MODEL]] §5 becomes real | **ADR-L1-002 mandates revisiting the epistemology itself** at ≥3 researchers |

> **Rule PR-5 (justified by LIM6, EV-9, ADR-L1-007):** **[[PEER_REVIEW_STANDARD]] is inert at N=1 and activates at N=2.** It is written and it is not executable today. It is the document that **closes G-4** — the institution's binding constraint — and **the arrival of a second researcher is the event that closes it.** Not a process improvement. Not a tool. A person.
>
> **At N=1, do not perform peer review on your own work and record it as peer review.** Per **LIM8** the record would be indistinguishable from a genuine one, and that indistinguishability is precisely the harm — it destroys the institution's ability to know its own epistemic state. **If you are alone: mark the claim C2, state that G4 is unmet, and move on.** That is the honest terminal state, and it is not a failure.

### 7.4 What you should therefore do at N=1

**Everything that is not acceptance — and there is a great deal of it, most of it more valuable than acceptance would be right now:**

1. **Kill claims at S2 (F1).** Free, and per §5.3 the most efficient thing the institution can do.
2. **Build the Failure Library.** It is the denominator every future claim inherits, and per §4.4 an empty one *"silently biases every DSR the institution ever computes."*
3. **Source mechanisms from literature** — the only blind supply (§7.3).
4. **Populate [[MARKET_INEFFICIENCY_TAXONOMY]] and [[ECONOMIC_MECHANISM_TAXONOMY]].** Eleven of twelve entries are RM0/RM1.
5. **Take claims to C2 and stop there, honestly labelled.**

> **A year of competent refutations at N=1 is not a wasted year.** Per **R12** and §4.4, it maps a boundary of efficiency — *"the substantive scientific object of study"* — and it builds the denominator. Per **PG-11**, a Program that competently refutes everything in its scope **has succeeded.**

---

## 8. Quick reference

| You are about to… | Follow | Rule that will bite you |
|---|---|---|
| Look at data freely | §2.4 Discovery. Unlimited | — |
| Get excited | **§5.1** | **R7.3** |
| Author a mechanism | S2 · [[ECONOMIC_MECHANISM_TAXONOMY]] | **R9, §7.3 blindness** |
| Register | **§5.2** · G1 | **R14, R2, R16.2** |
| Touch OOS | [[EXPERIMENT_STANDARD]] | **R6 — once, logged** |
| Interpret a pass | **§5.4** | **R7.4, R7.5, R3** |
| Interpret a fail | **§5.3** | **R15** |
| Re-run anything | **You are probably violating R15.** Re-read §5.3 | **R15, R7.5** |
| Review | [[PEER_REVIEW_STANDARD]] | **§7 — inert at N=1** |
| Replicate | [[REPLICATION_STANDARD]] | **LIM5** |
| Start a Program | [[RESEARCH_PROGRAM_PLAYBOOK]] | **PG-3 — family is append-only** |
| Judge your own work | [[RESEARCH_QUALITY_STANDARD]] | **LIM8** |
| Disagree | **§6** | **P4** |

---

## 9. Traceability

| This document | Extends | Never restates |
|---|---|---|
| §4 working order | [[MARKET_INEFFICIENCY_RESEARCH_PIPELINE]] S1–S10 | The stage definitions |
| §5.2 registration | [[01_SCIENTIFIC_FOUNDATION]] §5.2 (six elements), R14 | The six elements' definitions |
| §5.3 failure | **R15**, §5.3 (F1–F9), R1 | R15 — quoted once, deliberately |
| §5.4 pass | R7.4, R7.5, R3, EV-3 | The severity criterion |
| §3 the six rules | R2, R5, R6, R7.3, R7.5, R15 | Their justifications |
| §6 disagreement | §0.4 (defeaters), **P4** | The propositions |
| **§7 staffing** | **LIM6, LIM8, ADR-L1-007, EV-9** · [[KNOWLEDGE_CORPUS_DELIVERY]] §5.1 (G-4) | LIM6/LIM8 |
| PR-1 spec vs procedure | **D-021** | — |

**Invokes:** [[EXPERIMENT_STANDARD]] · [[REPLICATION_STANDARD]] · [[PEER_REVIEW_STANDARD]] · [[RESEARCH_QUALITY_STANDARD]] · [[RESEARCH_PROGRAM_PLAYBOOK]].
**Sequences:** [[RESEARCH_OPERATING_MODEL]] (roles, gates) · [[MARKET_INEFFICIENCY_RESEARCH_PIPELINE]] (stages) · [[HYPOTHESIS_LIFECYCLE]] (states) · [[EVIDENCE_MODEL]] (tiers).
