# Statistical Gatekeeper — Validation Report

Run: 2026-07-12T07:13:41

- **strategy:** NR7 Breakout
- **DECISION: REJECT** (failing stage: walk_forward)
- config_hash `c86edb9e8b435979e8cd72c11b5b408f4152f9b0bc68e254d49bb34109aad66c` | dataset `0d0175095fe72a32982eb9935b5bddecc1bf4d328f18fdf78112d32c96342f11` | commit `19f1132494e43a9482f2a959bf60d744e7bb8da3` | seed 20260711

## Stages

| stage | verdict | statistic |
|---|---|---|
| min_sample | PASS | `{"n_overall": 1108, "governing_cell": "BULL", "cell_n": 333}` |
| confidence_interval | WATCH | `{"point": 1.1968583451016337, "lo": 0.32379287138295737, "hi": 2.0561005616221526, "se": 0.4434078138907337, "n": 333, "n_boot": 10000, "ci": 0.95, "seed": 20260711}` |
| multiplicity | PASS | `{"governing_label": "BULL", "raw_p": 0.0035547314976294153, "bh_p": 0.024883120483405907, "bonferroni_p": 0.024883120483405907, "family_size": 7}` |
| psr | PASS | `{"psr": 0.9962746149920673, "sr": 0.14750276787668856}` |
| deflated_sharpe | WATCH | `{"dsr": 0.7687583943380494, "sr": 0.14750276787668856, "sr_benchmark": 0.10700204972942205, "n_trials": 3, "sr_trials_std": 0.12547078517104143}` |
| walk_forward | FAIL | `{"consistency_pct": 46.788990825688074, "pooled_oos_exp": 1.1968583451016337, "windows_tested": 218, "windows_profitable": 102, "n_windows": 218}` |
| out_of_sample | PASS | `{"retention": 0.6685819807296276, "late_exp": 0.9597077116801449, "late_n": 167, "early_exp": 1.4354375967967459, "boundary": "2025-05-26"}` |
| ft_eligibility | PASS | `{"forward_test_rule": {"min_n": 15, "go_exp": 0.5, "nogo_exp": 0.0, "timebox_months": 6}}` |

## Evidence bundle

```json
{
  "final_state": "REJECT",
  "failing_stage": "walk_forward",
  "strategy_fn": "NR7 Breakout",
  "candidate_hash": "34b30aa885217dcee3c4ba18d728d2fcc49a68452d027dedc55f307a6aa910e3",
  "config_hash": "c86edb9e8b435979e8cd72c11b5b408f4152f9b0bc68e254d49bb34109aad66c",
  "dataset_fingerprint": "0d0175095fe72a32982eb9935b5bddecc1bf4d328f18fdf78112d32c96342f11",
  "git_commit": "19f1132494e43a9482f2a959bf60d744e7bb8da3",
  "seed": 20260711,
  "forward_test_rule": null,
  "run_id": "dbcd21f849e44c358954a0a0b4fdf44a",
  "stages": [
    {
      "stage": "min_sample",
      "verdict": "PASS",
      "statistic": {
        "n_overall": 1108,
        "governing_cell": "BULL",
        "cell_n": 333
      },
      "threshold": {
        "min_n_overall": 300,
        "min_n_cell": 100
      }
    },
    {
      "stage": "confidence_interval",
      "verdict": "WATCH",
      "statistic": {
        "point": 1.1968583451016337,
        "lo": 0.32379287138295737,
        "hi": 2.0561005616221526,
        "se": 0.4434078138907337,
        "n": 333,
        "n_boot": 10000,
        "ci": 0.95,
        "seed": 20260711
      },
      "threshold": {
        "promotion_bar_pct": 0.5
      }
    },
    {
      "stage": "multiplicity",
      "verdict": "PASS",
      "statistic": {
        "governing_label": "BULL",
        "raw_p": 0.0035547314976294153,
        "bh_p": 0.024883120483405907,
        "bonferroni_p": 0.024883120483405907,
        "family_size": 7
      },
      "threshold": {
        "alpha": 0.05,
        "require_both": true
      }
    },
    {
      "stage": "psr",
      "verdict": "PASS",
      "statistic": {
        "psr": 0.9962746149920673,
        "sr": 0.14750276787668856
      },
      "threshold": {
        "min": 0.95
      }
    },
    {
      "stage": "deflated_sharpe",
      "verdict": "WATCH",
      "statistic": {
        "dsr": 0.7687583943380494,
        "sr": 0.14750276787668856,
        "sr_benchmark": 0.10700204972942205,
        "n_trials": 3,
        "sr_trials_std": 0.12547078517104143
      },
      "threshold": {
        "min": 0.9
      }
    },
    {
      "stage": "walk_forward",
      "verdict": "FAIL",
      "statistic": {
        "consistency_pct": 46.788990825688074,
        "pooled_oos_exp": 1.1968583451016337,
        "windows_tested": 218,
        "windows_profitable": 102,
        "n_windows": 218
      },
      "threshold": {
        "min_consistency_pct": 50,
        "promotion_bar_pct": 0.5
      }
    },
    {
      "stage": "out_of_sample",
      "verdict": "PASS",
      "statistic": {
        "retention": 0.6685819807296276,
        "late_exp": 0.9597077116801449,
        "late_n": 167,
        "early_exp": 1.4354375967967459,
        "boundary": "2025-05-26"
      },
      "threshold": {
        "min_retention": 0.5,
        "promotion_bar_pct": 0.5
      }
    },
    {
      "stage": "ft_eligibility",
      "verdict": "PASS",
      "statistic": {
        "forward_test_rule": {
          "min_n": 15,
          "go_exp": 0.5,
          "nogo_exp": 0.0,
          "timebox_months": 6
        }
      },
      "threshold": {}
    }
  ]
}
```
