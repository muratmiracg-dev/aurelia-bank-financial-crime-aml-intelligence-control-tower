# Power BI implementation specification

The repository source-controls the semantic model, measures, theme and page design. It does not claim that an unverified PBIX/PBIP binary has been rendered.

## Model

Use `Customers`, `Accounts`, `Transactions`, `KYCRisk`, `Alerts`, `Cases`, `Performance`, `GraphFeatures` and a marked `Date` table. Relationships are one-to-many from customer to account, transaction, alert, case, KYC risk and graph features. Use a role-playing event date for alert-window reporting. Keep `TypologyTruth` outside the operational report and load it only into a restricted validation workspace.

## Report pages

1. **Executive control tower** — alert rate, high-priority alerts, open cases, SLA compliance, KYC overdue rate, scenario volume and decision callouts.
2. **Customer risk and KYC** — inherent-risk bands, overdue reviews, PEP/synthetic screening flags and risk-factor drill-through.
3. **Transaction monitoring** — weekly volume, scenario funnel, score distribution and rule evidence.
4. **Graph intelligence** — degree, PageRank, component and short-cycle filters. Treat graph position as supporting evidence only.
5. **Case operations** — queue inventory, aging, SLA, analyst disposition and workload capacity.
6. **Model validation** — isolated synthetic precision, recall, false positives and scenario-level trade-offs.
7. **Governance** — data-quality controls, source register, human-review coverage and explicit prohibited automations.

## Row-level security

- `AML_Analyst`: assigned queue only.
- `AML_Senior_Reviewer`: all operational cases; no validation truth.
- `Model_Validation`: performance and restricted validation data; no case writeback.
- `Executive_ReadOnly`: aggregated pages; customer-level drill-through disabled.

## Interaction rules

Tooltips must display the scenario parameter, evidence value and disclaimer. No visual may label a person criminal, display a final ŞİB/STR outcome, or imply an automatic customer restriction. The red palette represents control urgency, not guilt.
