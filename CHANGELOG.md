# Changelog

## Unreleased

- CI now proves that the committed decision pack is reproducible. Before, the
  `deterministic-demo` job regenerated the outputs, rewrote `MANIFEST.sha256` from them and then
  verified the new manifest, so stale or edited committed results always passed. The job now
  verifies the committed files against the committed manifest first, then regenerates and
  compares every CSV, JSON and SQLite table with the committed values (`scripts/compare_outputs.py`).
- `make demo` and `make verify` now write the same manifest (`aurelia_aml.manifest`). The
  pipeline's own manifest omitted the SQLite layer, workbook, deck and PDF.
- The pipeline integration test runs in a temporary project root instead of rewriting the
  committed artifacts during `pytest`.
- CI test matrix adds Python 3.13.
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
