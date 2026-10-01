# Prompt untuk Claude Code (jalankan di /home/tjiesar/idx-walkforward-5001)

Paste ini ke Claude Code setelah `atr_plan/` sudah ada di repo dan null test lolos.

---

Context: `atr_plan/` is a standalone harness comparing exit methods (A fixed %, B ATR TP/SL, C ATR stop + chandelier) on identical entries. Its entries in `atr_plan/exit_compare.py` (`STRATS`, `sig_*` functions) are approximations. Wire it to the real strategies. Do NOT change any existing engine behaviour.

Tasks, in order. Stop and report after each phase.

**Phase 1 — audit (read-only)**
1. In `engine/walkforward_multi.py`, `engine/strategies.py` and `paper_trade.py`, find how TP/SL are evaluated on daily bars. Report exactly what happens when one bar's high >= TP AND low <= SL. Also report whether the entry bar can be stopped out, and whether gaps through the stop fill at the stop or at the open. Quote the lines.
2. List every strategy currently in `STRATEGY_FUNCS` with its entry rule, entry price (close t / open t+1 / trigger), TP/SL and max hold.

**Phase 2 — adapters**
3. In `atr_plan/exit_compare.py`, add `sig_real_<name>(df)` adapters that call the real entry logic from `engine/strategies.py` and return a boolean Series aligned to df (signal on bar t, entry t+1). Register them in `STRATS` with their real fixed TP/SL as variant A and the correct type (`mr` / `mom`). Keep the old `sig_*` functions.
4. If a strategy needs columns not in `ohlcv_long` (e.g. Stockbit flow), skip it and list it.
5. Run `python atr_plan/test_atr_exits.py` and `python atr_plan/exit_compare.py --db data/history_long.db --strategies <real names>`. Show the summary.md section 1–2.

**Phase 3 — only if I approve after reading the results**
6. Add ATR exits behind a feature flag `EXIT_MODE = "fixed" | "atr"` (default "fixed") in the engine and `paper_trade.py`, reusing `atr_plan/atr_exits.py`. Include IDX tick rounding and the 3-tick minimum stop. No other behaviour changes.

Constraints: no changes to `data/walkforward.db` schema, no scheduler/Telegram changes, no refactors outside the listed files.
