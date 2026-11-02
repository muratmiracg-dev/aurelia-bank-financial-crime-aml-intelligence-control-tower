# Changelog

## Unreleased

- Fixed a false negative in `CIRCULAR_TRANSFER`. Transfers were grouped into fixed 48-hour
  calendar buckets, so a three-party cycle completed within hours was missed whenever it
  crossed a bucket boundary. The scenario now evaluates a rolling `window_hours` window
  anchored at each transfer. Demo results are unchanged: the committed demo data has no
  boundary-crossing cycle.
- Added regression tests for boundary-crossing cycles, the inclusive window edge, the minimum
  amount and open chains.

## 1.0.0 — 2026-08-21

- Added deterministic synthetic customer, account, transaction and relationship generation.
- Added six explainable transaction-monitoring scenarios.
- Added KYC inherent-risk, Isolation Forest and NetworkX graph signals.
- Added alert prioritisation, case aggregation, SLA controls and human-review evidence packs.
- Added isolated synthetic validation metrics and realistic lookalike activity.
- Added SQLite, PostgreSQL, FastAPI, Power BI, Excel, PowerPoint and PDF deliverables.
- Added 38 tests, a 90% coverage gate, Ruff, CI, CodeQL and checksum verification.
