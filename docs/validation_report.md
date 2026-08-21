# Validation report

## Opinion

The version 1.0 analytical snapshot is reproducible and fit for its stated purpose: a portfolio-grade demonstration of AML decision support on synthetic data. It is **not validated for production use, regulatory reporting or customer action**.

## Verified snapshot

Seed `20260821`, cutoff `2026-08-20`.

| Metric | Result | Internal reference | Status |
|---|---:|---:|---|
| Customers | 1,800 | Configuration | Reconciled |
| Accounts | 2,250 | Configuration | Reconciled |
| Transactions | 48,412 | Baseline plus controlled injections | Reconciled |
| Alerts | 134 | n/a | Observed |
| Unique alerted customers | 126 | Maximum 12% of customers | 7.0% — pass |
| High-priority alerts | 21 | Human review required | 100% covered |
| Synthetic precision | 67.91% | Reference floor 8% | Pass |
| Synthetic recall | 98.91% | Floor 70% | Pass |
| Synthetic F1 | 80.53% | Monitoring metric | Observed |
| Open cases | 25 | n/a | Observed |
| Cases in review | 25 | n/a | Observed |
| Open SLA breaches | 0 | Zero tolerance | Pass |
| KYC reviews overdue | 892 / 1,800 | Maximum 35% | **49.56% — breach** |
| Data-quality controls | 12 / 12 | All pass | Pass |
| Automated tests | 38 | 90% line/branch gate | 96.53% total coverage |

## Scenario retrieval

| Scenario | TP | FP | FN | Precision | Recall |
|---|---:|---:|---:|---:|---:|
| Circular transfer | 24 | 6 | 0 | 80.00% | 100.00% |
| Dormant reactivation | 12 | 8 | 0 | 60.00% | 100.00% |
| Funnel/mule | 11 | 6 | 1 | 64.71% | 91.67% |
| High-risk geography | 14 | 7 | 0 | 66.67% | 100.00% |
| Rapid movement | 15 | 8 | 0 | 65.22% | 100.00% |
| Structuring | 15 | 8 | 0 | 65.22% | 100.00% |

The deliberate lookalike population prevents a misleading perfect-precision result. High recall is still a synthetic construction outcome and must not be extrapolated to real customer behaviour.

## Tests performed

- deterministic generation and schema checks;
- identifier uniqueness and account/customer referential integrity;
- positive amounts, complete timestamps and controlled data-class assertions;
- all six scenario paths and evidence lineage;
- KYC, anomaly and graph score boundaries;
- isolated-label precision and recall;
- human-review and prohibited-automation invariants;
- read-only API authentication, filtering and unavailable-output behaviour;
- pipeline, chart and SQLite integration;
- SHA-256 artifact verification.

## Management finding

KYC periodic review backlog is the only internal management breach. The recommended action is to segment the 892 overdue reviews by inherent risk and alert exposure, clear High-risk/alerted customers first, allocate weekly capacity, and monitor the remaining backlog to the 35% internal ceiling. This is an operational decision, not a regulatory conclusion.

## Limitations

Synthetic customers lack the complexity, missingness, seasonality and evolving adversarial behaviour of production data. No name matching, sanctions screening, adverse-media retrieval, beneficial-ownership resolution, privacy impact assessment or jurisdiction-specific legal review has been performed. Calibration is illustrative, labels are generated, case outcomes are simulated, and no independent second-line validation has approved the model.
