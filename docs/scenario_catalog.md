# Transaction-monitoring scenario catalog

All parameters below are fictional internal settings for a portfolio demonstration. They are not MASAK reporting thresholds, sanctions rules or legal conclusions.

| Scenario | Detection logic | Primary evidence | Internal parameter | Main false-positive risk |
|---|---|---|---|---|
| `STRUCTURING` | At least five cash inflows between 70% and 100% of the internal amount parameter in a rolling 48-hour window | Count, amount, source transactions | TRY 50,000 amount parameter; five transactions | Cash-intensive legitimate activity |
| `RAPID_MOVEMENT` | A material inflow followed by outbound value of at least 80% within 24 hours | Inflow, outbound ratio, chronology | TRY 120,000 inflow; 80% ratio | Payroll, settlement or treasury pass-through |
| `DORMANT_REACTIVATION` | Material activity on an account designated dormant | Dormancy status, amount, event time | TRY 100,000; 180-day context | Legitimate reactivation after inactivity |
| `FUNNEL_MULE` | At least five distinct incoming counterparties and material inflow followed by at least 75% outbound within 48 hours | Fan-in, amount, outbound ratio | Five counterparties; TRY 200,000; 75% | Marketplace, collections or family aggregation |
| `CIRCULAR_TRANSFER` | Three-node internal directed cycle in a 48-hour high-value subgraph | Cycle members, edges, source transactions | TRY 75,000 minimum edge | Legitimate intercompany or group treasury activity |
| `HIGH_RISK_GEOGRAPHY` | At least two transactions and TRY 150,000 with fictitious jurisdiction `XH` in 30 days | Country, value, count | Two transactions; TRY 150,000 | Legitimate trade or remittance corridor |

## Tuning protocol

1. Define the investigative hypothesis and adverse-use boundary.
2. Compare alert volume with analyst capacity and KYC segmentation.
3. Measure precision and recall on time-separated, permissioned labels.
4. Review false positives by segment, product and channel.
5. Challenge protected-group and proxy effects before promotion.
6. Require compliance-owner approval, version the configuration and retain rollback parameters.
7. Monitor volume, data drift, queue aging and reviewer outcomes after release.

## Evidence standard

A hit must preserve source transaction IDs, observed value, internal parameter, time window and rationale. Investigators must corroborate behaviour using current KYC, source of funds, counterparty purpose, transactional history, screening results and approved open-source research. A single rule hit is insufficient for a reporting decision.
