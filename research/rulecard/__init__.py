"""Rule Card framework — freeze-then-run-once testing of literature-backed rules (D-055).

See docs/research_notes/RULE_FIRST_PROTOCOL_2026-09-24.md for the method, and
docs/research_notes/RULE_CARD_TEMPLATE.yaml for the card. Modules:

  card.py      load + validate a card (tier hurdle, power admissibility)
  engine.py    month-end characteristic sort: universe, next-open fills, EW-rest benchmark
  checks.py    mandatory checks, one per past incident (LA-1, ZV-1, ID-1, EX-1, FILL-1, BM-1, SPL-1)
  stats.py     Newey-West t, Patton-Timmermann MR test, power
  evaluate.py  summary windows + the central verdict
  runner.py    validate / dry / freeze / run (refuses on hash drift or a second run)
  synthetic.py planted-effect panels for tests and script self-tests
"""
