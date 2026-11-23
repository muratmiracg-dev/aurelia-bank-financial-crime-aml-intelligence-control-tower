# Changelog

## Unreleased

- Control OPS-02 ("open SLA breaches = 0") could never fail. Every case's creation time was
  pulled forward to at most `sla_days - 1` before the snapshot, whenever its alerts actually
  fired, so every open case was due after the snapshot; statuses came from a fixed 3:1:1
  Closed/In Review/Open mix and closed cases always closed at 55% of the SLA. Cases now open one
  hour after the customer's first alert, review effort is a deterministic 0.4-1.6 x SLA, and
  status and SLA outcome follow from age. Result: 125 Closed and 1 In Review (was 76/25/25),
  24 cases closed after SLA (new `closed_after_sla` in the executive summary), no open case
  overdue. Alert, precision/recall and KYC figures are unchanged.
- The synthetic snapshot no longer contains activity after its 2026-08-20 cut-off. Injected
  high-risk-geography transfers span six days (lookalikes four) but could start two days before
  the as-of date, so four transactions were dated 20-23 August and three alerts closed after
  the snapshot (one case was "created" on 23 August). Their start is now pushed back by the span,
  the generator refuses to emit post-cut-off transactions, and tests cover five seeds. Headline
  counts are unchanged (134 alerts, 126 cases, precision 67.91%, recall 98.91%); 21 case event
  times and the affected rule-hit windows move earlier.
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
