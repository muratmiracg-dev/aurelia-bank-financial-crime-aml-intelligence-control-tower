# Risk register

| ID | Risk | Impact | Key mitigation | Residual status |
|---|---|---|---|---|
| R-01 | Synthetic labels overstate effectiveness | False confidence | Explicit scope limits; production validation required | High |
| R-02 | Scenario parameters become mistaken for legal thresholds | Missed reporting duty | Label every value internal; amount-independent reporting note | Medium |
| R-03 | Geography, occupation or channel creates proxy bias | Unfair prioritisation | Fairness/proxy analysis and human challenge before deployment | High |
| R-04 | Network centrality is treated as guilt | Unjustified escalation | Supporting-evidence label, reason codes and reviewer training | Medium |
| R-05 | Isolation Forest drifts | Unstable volume | Score/feature drift monitoring, champion–challenger and rollback | Medium |
| R-06 | Validation truth leaks into detection | Inflated metrics | Separate table, code-path isolation and restricted SQL schema | Low |
| R-07 | Real PII is committed to Git | Privacy/security breach | Synthetic-only policy, secret scanning and review checklist | Low |
| R-08 | Sanctions data becomes stale | Missed or false matches | No real list committed; approved live screening connector required | High |
| R-09 | Alert backlog exceeds analyst capacity | SLA breach | Capacity limit, queue dashboard and risk-based allocation | Medium |
| R-10 | KYC review backlog weakens context | Poor investigations | Prioritise 892 overdue reviews; weekly burn-down to 35% ceiling | High |
| R-11 | Automated adverse action is added | Customer harm and legal exposure | Read-only API, prohibited-use policy and human-review invariant | Low |
| R-12 | Analyst outcome bias feeds tuning | Reinforced false positives | Outcome QA, sampling, second-line review and reason-code audit | Medium |

Risk ratings are management judgments for the fictional project, not regulatory classifications.
