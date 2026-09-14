# G1 AUTHORITATIVE PREREG RETRIEVAL — 2026-09-11

**Task:** locate the authoritative broker-flow-v002 H0–H3/P0 preregistration on the ZCode/Windows corpus (expected per governance record under `C:\Users\tjies\ZCodeProject\`), establish provenance/version, and extract its registered definitions if found.

**Mode:** READ-ONLY. No G1, no data/methodology changes, no reconstruction of missing content, no commits.

---

## 17. FINAL STATUS: **NOT FOUND**

The authoritative `BROKER_FLOW_PREREGISTRATION.md` corpus is **not present anywhere reachable from this environment**. The expected location — `C:\Users\tjies\ZCodeProject\` — is on a Windows system volume that **does not exist on this machine at all** (block-device verified). This outcome independently corroborates, and is corroborated by, the repository's own governance record (§5 below).

---

## 1. Search scope (exact)

**Physically absent (cannot be searched):**
- `C:\` and `C:\Users\tjies\` — **no Windows system volume exists on this machine.** Block devices (`lsblk`): `sda` = 238.5 G Linux ext4 system (`/`), `sdb` = 465.8 G NTFS (empty, 79 M used), `sdc1` = 1.8 T NTFS (personal data volume, mounted `/mnt/storage2tb`). There is no `/mnt/c`, no third NTFS partition, no Windows OS disk. Any WSL `\\wsl$` view of a Windows host is likewise inapplicable: this is a standalone Linux box, not a WSL guest of the Windows machine.

**Searched (filenames AND targeted contents):**

| Scope | Method | Result |
|---|---|---|
| `/mnt/storage2tb` (1.8 T NTFS — the only populated Windows-format volume; contains `d-backup`, `e-backup`, `My Backups new`, `Order Flow Program`, personal/sync folders) | full recursive filename search: `*prereg*`, `*broker*`, `*v002*`, `*IDX*`, `*ZCode*` | Zero prereg hits. Only unrelated matches: a trading-course video (`…/8 - Brokers.ts`) and `d-backup/IDX-Research-Datasets/stockbit-flow-bars-v002` (the frozen **Dataset A export artifact** — a dataset, not a preregistration; its naming collision with `broker-flow-v002` is explicitly flagged in `BROKER_FLOW_DATASET_ADMISSION_DRAFT_2026-09-09.md` §risk-4) |
| `/mnt/storage2tb/d-backup/{Download, GGC SYNC, tmp, TechnoBrain}`, `e-backup`, `My Backups new` | filename sweep of all `.md/.txt/.docx/.pdf`; archive listing (`*.zip/.7z/.tar/.rar`) | Only trading courses (Emvestart, Sekolah Saham — Nov 2025), photo backups, GGC invoice PDFs. `Sync-20260128T124547Z-3-002.zip` (Jan 2026) lists only `Sync/GGC/…` invoices and personal/trading documents — pre-dates the broker-flow program |
| `$RECYCLE.BIN` on storage2tb | filename search | Empty of matches |
| `/mnt/storage500gb` | full file listing | Volume empty (79 M used, 0 files) |
| `/mnt/research-agent`, `/mnt/storage_2tb` | listing | Empty mounts |
| `/home/tjiesar/ZCodeProject/**` + `/home/tjiesar/10 Projects/**` | content grep for `broker-flow-v002`, `broker_flow_v002`, `BROKER_FLOW_PREREGISTRATION` | **Zero definition-bearing hits.** Exactly two governance *mentions* (both are records ABOUT the missing corpus — see §5): `docs/roadmap/DECISION_LOG.md` (D-032 scope note) and `docs/research_programs/P-M/BROKER_FLOW_DATASET_ADMISSION_DRAFT_2026-09-09.md` (D-032 cross-reference) |
| `/home/tjiesar/{DS, DS.backup, backups, home, CodeWhale, Documents, Downloads, 40 Archive, 00 Inbox, idx-walkforward-current}` | content grep, same tokens; filename sweep for prereg/broker-flow | Zero hits. `40 Archive` holds older repo copies (`idx-walkforward`, `idx-walkforward-5002`, `idx_screener`, …) — token grep clean |
| `/home/tjiesar/Downloads/` owner documents | full-text extraction | `P-M Broker Flow Red Team.pdf` (2026-09-10), `Dataset B Readiness.pdf`, `P-M Foundation Audit v2.pdf` — all **adversarial/audit reports** (DERIVED). None contains the preregistration; none cites a v002 prereg path. Their "P0" strings are the unrelated "P0–P7" IDX80 period labels |
| `Downloads/takeout-20260701T031658Z-3-001{,.zip}` | listing + filename search | Gmail-only takeout (`Takeout/Mail/User Settings`), July 2026 — pre-dates the program |
| `/home/tjiesar/ZCodeProject` archives/binary formats (`*.zip/7z/rar/tar/docx/pdf`) and Windows-export-style directories | find | None exist |
| Git objects | brief states branches/tags/worktrees already established NOT FOUND; spot-verified no new corpus worktrees | consistent |

**Not searchable:** OneDrive cloud-resident copies (no local OneDrive mount; `gvfs` mounts expose no cloud shares), email attachments outside the July-2026 takeout, and any storage not physically attached to this machine.

## 2. Candidate artifacts examined

| Candidate | Path | Size/mtime | SHA-256 (16…) | Self-identification | Classification |
|---|---|---|---|---|---|
| Decision record D-032 | `/home/tjiesar/10 Projects/idx-walkforward-5001/docs/roadmap/DECISION_LOG.md` §2e (lines ~564-636) | — (repo file, 2026-09-08 entry) | — (uncommitted governance file; no git repo at repo root per environment) | "Dell-side record of owner instructions… **not** a verified cross-check against the actual preregistration text, and **not itself an amendment to that document**" | **DERIVED/SUMMARY** (authoritative for what the owner decided; NOT the preregistration) |
| Dataset admission draft | `docs/research_programs/P-M/BROKER_FLOW_DATASET_ADMISSION_DRAFT_2026-09-09.md` | — | — | Cross-references D-032; states canonical governance receipt "not yet been persisted in the Research Governance Corpus" | **DERIVED/SUMMARY** |
| Red Team audit | `/home/tjiesar/Downloads/P-M Broker Flow Red Team.pdf` (404,121 B, 2026-09-10) | ✓ | — (not extracted; content-identified) | "An adversarial audit of Dataset A, the broker-flow corpus…" | **DERIVED/SUMMARY** |
| Dataset B Readiness / P-M Foundation Audit v2 PDFs | `/home/tjiesar/Downloads/` | ✓ | — | Audit reports | **DERIVED/SUMMARY** |
| `stockbit-flow-bars-v002` | `/mnt/storage2tb/d-backup/IDX-Research-Datasets/` | — | — | Frozen **dataset** export (Dataset A OFI line), explicitly NOT the prereg and explicitly distinct from `broker-flow-v002` | **NOT RELEVANT** |
| BFI-001/LIT-001/LIT-002/HLIQ/H6/S2-PM-0003 preregistrations | `ZCodeProject/*`, `docs/archive/root_artifacts/` | ✓ | BFI-001 `91c0eb9a4a42630f…` (hash-file verified) | Frozen preregistrations of **other** programs/hypotheses | **NOT RELEVANT** (task prohibits importing their definitions) |

**No candidate classifies as AUTHORITATIVE or LIKELY AUTHORITATIVE for broker-flow-v002 H0–H3/P0.**

## 3-4. Authority determination / exact path of the authoritative artifact

**Not established — artifact absent from every reachable location.** The repository's own governance record independently pins where it lives: DECISION_LOG §2e scope note (quoted verbatim):

> "`broker-flow-v002` and its Phase 1 hypotheses (H0-H3) are **not yet a registered research object in this repository** … and the authoritative preregistration corpus (`BROKER_FLOW_PREREGISTRATION.md` and siblings) is understood to live on a separate machine (Windows/ZCode, `C:\Users\tjies\ZCodeProject\`) not reachable from the session that recorded D-032. That session verified this repository contains no file, prior commit, or prior DECISION_LOG entry matching `broker-flow-v002` under any name."

Also recorded there: the target dataset artifact name `walkforward_v002_20260904.db`, and that `data/frozen/` contains only the unrelated `stockbit-flow-bars-v002`.

## 5-16. H0-H3 extraction, estimand, controls, inference, MDE, PASS/FAIL/KILL, availability, freq, NF, §4/§5 conflicts, turnover criterion

**Not extractable — the artifact was not found.** Per the hard rules, nothing was reconstructed from implementations, design memos, or audit PDFs. What CAN be reported is what the repository's governance record already states about two of the seven critical conflict checks — quoted because they are the owner's own recorded status, not my resolution:

- **§4/§5 train/test/OOS contradiction — recorded OPEN at the source.** D-032 **Item C** ("OPEN — NOT RESOLVED"), quoting the situation verbatim: *"The locked preregistration contains a contradiction between: §4: no train/test split for H0/H1 specification tests; §5: H0/H1 language containing OOS/fold criteria. This requires a dated explicit preregistration decision before H1 results can be interpreted. No H1 fold criterion is to be silently added or removed."* — "This item **blocks interpretation of any H1 result** until resolved by whoever holds and amends the authoritative preregistration."
- **§5 ≤200% monthly turnover criterion — recorded OPEN at the source.** D-032 **Item D** ("OPEN — NOT RESOLVED"): *"The §5 ≤200% monthly turnover criterion remains unresolved until an explicit mathematical operational definition is recorded. Do not invent a turnover formula. H1 cannot receive a definitive verdict based on that criterion until it is formally defined."*
- **Freeze/version information (partial, from D-032):** Decisions A and B ACCEPTED (analytical window `2025-01-02 → v002 freeze date`, no redefinition; complete-backfill-before-freeze, stop-and-escalate rather than silently changing the specification). The preregistration itself is referred to as **"locked"**; its version/date/hash were never persisted on this side.
- **freq / NF / availability convention / primary estimand / inference / MDE / PASS-FAIL-KILL:** nothing in the accessible record states the authoritative artifact's content on these. (The separately-filed semantics audit `G1_PREEXECUTION_SEMANTICS_AUDIT_2026-09-10.md` documents that NO source in the corpus ratifies `freq` as a ticket denominator or an NF control source — and this retrieval confirms the one artifact that could override or ratify those findings is not reachable.)

## 16. Unresolved gaps

1. The authoritative corpus machine/volume (`C:\Users\tjies\ZCodeProject\`) is not attached to this environment — retrieval requires that volume (or an owner-provided copy/hash).
2. §4/§5 H1 contradiction — OPEN (owner record D-032 Item C).
3. §5 ≤200% monthly turnover — OPEN, no operational formula (D-032 Item D).
4. No registered version/hash of the locked preregistration exists on this side to verify a future copy against (the only recorded anchor is the target dataset name `walkforward_v002_20260904.db` and D-032 itself).
5. The three derived audit PDFs and the ZCode semantics audit agree no freq/NF ratification exists — but the authoritative artifact could supersede them once retrieved; that check is still owed.

## Final status: **NOT FOUND** (with exact search scope in §1)

Required next step (outside this task's authority): obtain the corpus from the Windows/ZCode machine that holds `C:\Users\tjies\ZCodeProject\`, then re-run this authority test against the actual `BROKER_FLOW_PREREGISTRATION.md` (record path, size, mtime, SHA-256, freeze/version block) and resolve D-032 Items C and D by dated owner decision.

*No files created or modified other than this report. No G1. No reconstruction. No commits.*
