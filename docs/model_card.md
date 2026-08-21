# Model card: alert prioritisation stack

## Intended use

Rank rule-generated synthetic AML alerts for trained human analysts. Support scenario tuning, workload planning and model-risk discussion.

## Prohibited use

- automatic ŞİB/STR filing or regulator communication;
- automatic account closure, blocking, de-risking or customer notification;
- criminal, sanctions or PEP classification of a real person;
- use on production data without privacy, legal, security and model validation approval;
- treating anomaly or network centrality as evidence of wrongdoing.

## Components

| Component | Technique | Output | Explainability |
|---|---|---|---|
| KYC | Additive policy score | 0–100 inherent risk | Component scores and reason string |
| Monitoring | Six deterministic scenarios | Rule hit | Window, transactions, amount, observed value and parameter |
| Behaviour | Isolation Forest | Percentile anomaly | Eight exported input features |
| Network | NetworkX metrics | 0–100 graph score | Degree, PageRank, component and cycle flag |
| Triage | Weighted linear score | Priority and action | Every score contribution in plain text |

## Training and evaluation data

The Isolation Forest is fitted to 1,800 synthetic customer profiles. Rules do not train. Validation uses 92 isolated synthetic subjects plus unlabeled lookalike activity. No real customer or watchlist data is included.

## Fairness and explainability

The synthetic geography and occupation factors can act as proxies in real systems. A production deployment would require protected-group testing where legally permissible, proxy analysis, outcome disparity monitoring, reason-code quality checks and documented challenge by Compliance, Legal, Privacy and Model Risk.

## Monitoring

Track alert rate, precision/recall on permissioned outcomes, queue volume, SLA, disposition mix, feature drift, missing fields, score distribution, segment concentration and manual override. Any breach triggers investigation, parameter freeze or rollback under the change protocol.

## Owner and approval

Portfolio owner: Murat Miraç Gedik. Production owner, second-line validator, MLRO approval, legal opinion and data-protection approval: not assigned because this is a demonstration.
