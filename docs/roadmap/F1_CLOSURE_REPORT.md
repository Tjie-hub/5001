# F-1 Closure Report — Repository File-Count Correction

**Status:** Canonical governance record · **Version:** 1.0 · **Date:** 2026-07-17
**Authority:** Closes defect F-1 (the sole accepted defect from the Independent ARB Review dated 2026-07-17, outcome **APPROVE WITH MINOR OBSERVATIONS**). Point-in-time record; supersedes the file-count figures previously stated in the two affected documents.
**Produced by:** Phase B Governance Remediation — F-1 closure action
**Scope of edit:** Numerical file-count figures only. **No qualitative text, governance conclusion, RN disposition, layer mapping, blocker classification, decision proposal, or Phase A file was modified.** See §6.

---

## 1. The defect (F-1, as accepted)

The Independent ARB Review identified that two governance records cited repository file counts that were (a) unsupported by the live repository, (b) mutually inconsistent with each other, and (c) mathematically irreconcilable with the actual filesystem. The Review classified this as **Minor** — a documentation-accuracy defect, not a governance-logic defect — and verified that every *qualitative* conclusion that depended on those counts (zero broken references; zero duplicate IDs) remained correct.

---

## 2. Original values, corrected values, affected documents

| # | Document | Location | Original value | Corrected value |
|---|---|---|---|---|
| 1 | `docs/roadmap/DOCUMENT_REGISTRY_UPDATE.md` | §3 (ID uniqueness sweep), line 41 | *"55 pre-existing + 5 ingested + 6 remediation records = **66** unique IDs"* | *"50 pre-existing + 5 ingested + 6 remediation records = **61** total IDs"* |
| 2 | `docs/roadmap/CROSS_REFERENCE_AUDIT.md` | Method line, line 6 | *"(**60** files at scan time)"* | *"(**61** files at scan time — 50 pre-existing + 5 ingested + 6 remediation records)"* |

**Scan for further occurrences:** All six package documents (`GOVERNANCE_REMEDIATION_REPORT`, `HEADER_CHANGE_LOG`, `LAYER_MAPPING_TABLE`, `DOCUMENT_REGISTRY_UPDATE`, `CROSS_REFERENCE_AUDIT`, `FREEZE_READINESS_REPORT`) were scanned for the suspect figures (55, 60, 66) and the related phrases ("pre-existing", "at scan time", "unique IDs"). **Only the two locations above contained the defect.** The other four documents required no change.

---

## 3. Verified canonical counts (single source of truth)

Fresh folder-by-folder inventory of `*.md` files (max depth 1) across the five corpus folders, taken at closure time 2026-07-17:

| Folder | Pre-existing | Remediation files | Total |
|---|---:|---:|---:|
| `docs/governance/` | 7 | 0 | 7 |
| `docs/research_os/` | 19 | 3 ingested | 22 |
| `docs/roadmap/` | 22 | 6 records | 28 |
| `docs/Phase_A_Scientific_Foundation/` | 1 | 0 | 1 |
| `docs/archive/` | 1 | 2 ingested | 3 |
| **TOTAL** | **50** | **11** (5 ingested + 6 records) | **61** |

**Math check:** 50 + 5 + 6 = 61 ✓

---

## 4. Reason for correction

1. **The "55 pre-existing" figure overstated the pre-remediation corpus by 5.** The actual pre-existing count is 50 (7 + 19 + 22 + 1 + 1). The figure 55 has no defensible derivation from any folder combination.
2. **The "66 unique IDs" total was a downstream consequence** of the 55 overcount. The correct post-remediation total is 61.
3. **The "60 files at scan time" figure was internally inconsistent with the DOCUMENT_REGISTRY figure.** If the audit ran after the 5 ingested files existed (as its own §5 attests), the count at the time of audit finalization was the full post-remediation total of 61, not 60. No defensible point in time yields 60.
4. **The two reports were mutually inconsistent**: if DOCUMENT_REGISTRY's "55 + 5 = 60" were the scan basis, the post-records total would have to be 66 — but CROSS_REFERENCE_AUDIT and the live filesystem agree the total is not 66.

---

## 5. Verification method

1. **Fresh filesystem inventory** via `find … -maxdepth 1 -name '*.md' -type f | wc -l` per folder, summed. Result: **61** total, **50** pre-existing (61 − 11 remediation files).
2. **Remediation-file manifest cross-check** against `GOVERNANCE_REMEDIATION_REPORT` §5 (5 ingested + 6 records = 11). All 11 files confirmed present on disk.
3. **Math reconciliation:** 50 + 5 + 6 = 61 ✓; both corrected documents now state this equation identically.
4. **Live cross-check:** corrected total (61) matches the live filesystem count (61) ✓.
5. **Post-edit scan:** grep for `55 pre-existing`, `60 files`, `66 unique`, `66 total IDs`, `66 =`, and bare occurrences of 55/60/66 across all six package documents → **zero hits**. No conflicting totals remain.
6. **Substantive-claim preservation check:** the filename-basename uniqueness sweep (`basename … .md | sort | uniq -d`) returns **empty** under the corrected count — the "zero duplicate IDs" finding is unaffected.

---

## 6. Confirmation — governance conclusions unchanged

This edit touched **only the numerical file-count figures** in the two affected documents. The following were **not** modified, by constraint and by verification:

| Protected item | Status |
|---|---|
| Any architecture | **Not modified** |
| Any governance conclusion | **Not modified** |
| Any Phase A document (L0/L1/L2 file) | **Not modified** — the two edited files are Phase B governance records in `docs/roadmap/`, not Phase A corpus documents |
| Any decision proposal (D-025-P / D-026-P / D-027-P) | **Not modified** |
| Any layer mapping | **Not modified** |
| Any blocker classification | **Not modified** |
| Any RN disposition | **Not modified** |
| Any qualitative audit finding (zero broken refs; zero duplicate IDs; 89 mutual-citation pairs; the RESEARCH_DATABASE_CONCEPT forward-reference finding) | **Not modified** — all independently verified to hold under the corrected count |
| Any other text in either corrected document | **Not modified** — only the count substring was replaced; surrounding sentences intact |

The substantive findings the original counts were meant to support are **independently true** and remain valid:

- **"Zero duplicate basenames"** (DOCUMENT_REGISTRY_UPDATE §3) — verified TRUE under 61 files (`uniq -d` empty).
- **"Zero broken references in the pre-existing corpus"** (CROSS_REFERENCE_AUDIT §1) — qualitative finding, unaffected by count.
- **"89 mutually-referencing document pairs"** (CROSS_REFERENCE_AUDIT §2) — pair-count, not file-count; unaffected.

---

## 7. Package status after closure

- Defect **F-1 is CLOSED.**
- **No new findings introduced** by the correction.
- All counts across the package are now **identical and mathematically consistent** (50 + 5 + 6 = 61).
- **Package ARB status remains: APPROVE WITH MINOR OBSERVATIONS — pending Owner Ratification.** The sole Minor defect has been resolved; the three Observations (R-1 contested-layer limbo, R-2 unsigned-L1 inheritance, R-3 no numeric ID scheme) stand as previously noted and require no action for package approval — they are matters for the owner ratification step, not blockers to it.
