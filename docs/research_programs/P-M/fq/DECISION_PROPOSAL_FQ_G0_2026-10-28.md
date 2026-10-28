# {FQ} E/P G0 — proposed D-entry text (propose-only, NOT filed)

**Status:** PROPOSAL. The D-number and the filing into `docs/roadmap/DECISION_LOG.md` belong to the owner.
Fills the template in `docs/reports/ZCODE_TUESDAY_2026-10-27.md` §J1.5 with the committed result (`588ce80`).
Every number below was re-checked on 2026-10-28 against the result JSON, the run log and the files on disk.

---

> ### D-1xx · {FQ} E/P value G0: stop rule not fired — eligible for registration on the owner's go
> **Status:** RECORDED · **Date:** 2026-10-27 · **Type:** G0 breadth/power · **Approval authority:** the frozen
> stop rule (`P-M/fq/G0_FREEZE_FQ_EP_2026-10-26.md`; precedents D-087, D-094, D-097, D-102, D-110).
>
> - **Run.** Once, 2026-10-27 17:41 WIB (one-shot timer `zcode-fq-g0-20261027`, exit 0, 12 s). Breadth and power
>   only; no panel return was computed or read.
> - **Pins (freeze §7.2).** Freeze file sha256 `e14ab4d96d58947f7d1a475c46f754d39ad258e0215db9f1e6b0aba747358549`
>   (= `FREEZE_SHA256` in the script). Script `g0_fq_ep_breadth.py` sha256
>   `d741e9b50a3d6547f683f0d94e6bd237734187c9ad370752f4e2c4392e7ef1b1` (unchanged since `d1e9497`). Sums file
>   `~/idx_external/stockbit_fin/SHA256SUMS_2026-10-26.txt` sha256
>   `debbda26697307a83ea9287bd0fa9811154a26dae86c7c13a7a2b024557114e1`, written 2026-10-27 08:40 after the
>   2026-10-26 19:12 parse; its `fin.db` line `caefb1a2…` matches the result JSON. fin.db mtime 2026-10-26 19:12.
> - **Result.** Qualifying formation months **203 of 208** (≥ 120 names with valid E/P, ≥ 40 per tercile);
>   T_eff **16.92 y**; prior-only power Φ(0.75·√T_eff − 3.300069) = **41.5%** against the **20%** stop
>   (129 qualifying months needed). **Stop rule not fired.** (D-112 projected 43.0% on 208 months; the 5
>   non-qualifying months account for the gap.) The 50% post-publication haircut row in D-112 still applies: a null
>   G1 would be weak evidence.
> - **Report-only lines (no rule attached).** FX cross-check: 0 of 4,908 USD-reporter periods beyond the 3%
>   tolerance. New-code coverage: 41 of the 92 newly pulled KSEI codes carry fundamentals (755 valid
>   name-months); the other 51 are never-tracked delisted names (ZCode 10-27, K4.1).
> - **Not decided by this entry.** Registration of the arm (HYP-PM-0023; census 613 → 614) and the single G1 run
>   wait for the owner's separate go (freeze §7.4, D-112). No hypothesis-registry row is created by this entry.
> - **Census:** stays at **613**.
> - **No outcome was read.**
>
> **Amendment.** Only by a superseding D-entry.

---

## Owner questions
1. File this text (with its D-number), amend it, or hold it?
2. Separately: go / no-go for registering HYP-PM-0023 and the single G1 run (`g1_fq_ep.py`, which refuses until the
   registration is pinned).
3. The PEAD withdrawal D-entry (`ZCODE_TUESDAY_2026-10-27.md` §J2.2) is also unfiled; the two can take consecutive
   numbers.
