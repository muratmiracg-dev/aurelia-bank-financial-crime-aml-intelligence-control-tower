# Data dictionary

## Core entities

| Table | Grain | Primary key | Description |
|---|---|---|---|
| `customers` | One synthetic customer | `customer_id` | KYC profile, expected activity and review date |
| `accounts` | One synthetic account | `account_id` | Owner, product, currency and dormancy state |
| `transactions` | One synthetic event | `transaction_id` | Customer-centric incoming/outgoing transaction |
| `relationships` | One entity relationship | composite | Account ownership and synthetic shared-device links |
| `typology_truth` | One validation subject per injected case/scenario | composite | Restricted post-detection validation labels |

## Key customer fields

| Field | Type | Meaning |
|---|---|---|
| `customer_id` | string | Non-PII synthetic identifier |
| `customer_type` | category | Individual or corporate |
| `residence_country` | string | Synthetic routing country code |
| `pep_flag` | boolean | Random synthetic test flag; not a real PEP result |
| `synthetic_watchlist_match` | boolean | Random placeholder; not real screening data |
| `expected_monthly_turnover_try` | decimal | Synthetic expected activity profile |
| `kyc_review_due_date` | date | Internal periodic-review due date |
| `beneficial_owner_complete` | boolean | Synthetic KYC completeness indicator |

## Key transaction fields

| Field | Type | Meaning |
|---|---|---|
| `timestamp` | timestamp | Event time within the 90-day observation window |
| `direction` | category | Incoming or outgoing from the subject customer's perspective |
| `counterparty_id` | string | Synthetic customer or external entity identifier |
| `counterparty_country` | string | Synthetic route used by the geography scenario |
| `transaction_type` | category | Wire, instant payment, card, cash deposit or withdrawal |
| `amount_try` | decimal | TRY-equivalent synthetic value |
| `cash_flag` | boolean | Cash transaction indicator |
| `device_id` | string | Synthetic telemetry identifier |

## Analytical outputs

| Output | Grain | Decision use |
|---|---|---|
| `kyc_risk` | Customer | Explainable inherent-risk context |
| `rule_hits` | Scenario hit | Evidence and internal-parameter lineage |
| `anomaly_scores` | Customer | Behavioural prioritisation signal |
| `graph_features` | Customer | Network-supporting evidence |
| `alerts` | Rule hit | Weighted triage priority and reason string |
| `cases` | Customer | Human-review workload and SLA |
| `performance` | Scenario | Isolated synthetic precision/recall/F1 |
| `data_quality_controls` | Control | Data invariant evidence |
| `operational_controls` | Control | Model and workload appetite evidence |
| `investigation_packets` | Case | Safe evidence template with decision unset |

Dates are ISO-8601, booleans are explicit, and monetary amounts are TRY equivalents unless otherwise stated.
