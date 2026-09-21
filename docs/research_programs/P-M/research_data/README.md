# P-M RESEARCH DATA LAYER (views_v1)

Built by `build_research_views.py`; validated by `validate_research_views.py`
(24 checks; `--rebuild` adds the byte-identical double-build determinism test).
Sources are opened **read-only with fail-closed sha256 identity checks**:
the Dataset B frozen store (pin `21661f03…`) and the frozen flow-bars v002
store (pin `fa7f07b3…`). Nothing outside `views_v1.sqlite` is written.

| View | Grain | What it gives you |
|---|---|---|
| `v_a_side` | ticker × date × broker × side | exact frozen broker-side rows (raw pass-through, incl. freq UNVERIFIED) |
| `v_a_broker_day` | ticker × date × broker | signed aggregates by sign(value): value_pos/neg, gross, net, lots, freq_sum (raw), investor_type, vwap |
| `v_b_concentration` | ticker × date | n_brokers, top1/top3/top5 gross shares, HHI + bandar passthrough (no thresholds) |
| `v_c_pair_structure` | ticker × date × (buy broker, sell broker) | potential-counterparty space (17.3M pairs) — NOT identified trade matching (impossible at daily grain) |
| `v_d_broker_persistence` | ticker × session × broker | prev-admitted-session lookup (PIT: strictly earlier session) |
| `v_d_broker_activity` | broker × session | cross-ticker participation |
| `v_e_intraday_summary` | ticker × date (v002 window) | minute-bar coverage state per cell (BARS / CONFIRMED_EMPTY_DAILY / TRUE_GAP / NO_ROW) + session totals |
| `v_e_minute_sequence` | ticker × date × minute | via `query_intraday.py` (verifies frozen sha before opening); not copied into this store |
| `v_f_flow_price` | ticker × date | flow × price co-registration ratios (lots/2×volume, broker gross/traded value) — alignment only |
| `v_g_event_flow` | ticker × date | suspension windows, corporate actions (+applied basis), bandar, regime-aware IDX band contact |

`meta_view_catalog` carries grain, source, row count, **content sha256**, and
semantic notes per view. `meta_sources` pins all source hashes and windows.

RULES OF THE ROAD: these are data views. No thresholds, no outcome selection,
no signal construction. `freq` is passthrough only (semantics UNKNOWN — never a
transaction-count denominator). `investor_type` is brokerage ownership, never
end-investor identity. All-broker aggregate net is the exchange accounting
identity (Σ over this store is integer-exactly 0), not a directional predictor
(D-049 gate).
