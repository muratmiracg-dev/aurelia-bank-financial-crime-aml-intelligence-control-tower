# Interview guide

## 30-second explanation

“Aurelia AML is a synthetic, end-to-end financial-crime decision-support project. It combines rules, KYC, anomaly detection and graph signals, but keeps the final decision human. I isolated validation labels, added realistic false positives, measured operations and built the same outputs an analyst, validation team and executive committee would need.”

## Questions and evidence

### Why not use machine learning alone?

Rules preserve policy intent and transaction evidence. Isolation Forest and graph metrics add independent prioritisation signals. The weighted score remains transparent, and the system cannot create an adverse outcome without a reviewer.

### How did you prevent leakage?

Injected labels live in `typology_truth.csv`; no detection module accepts that table. The SQL design also separates validation into a restricted schema. Only the completed alert set enters evaluation.

### Why is recall so high?

The dataset deliberately contains known synthetic patterns, so high retrieval is expected. I explicitly refuse to extrapolate it to production. Lookalike transactions reduce precision to 67.91%, and the model card requires time-separated real-world validation before any use.

### What would you tune first?

Segment funnel/mule and rapid-movement logic by business model and account purpose, then measure review outcomes. The current largest operational issue is not alert volume; it is the KYC backlog of 892 overdue reviews.

### What is the role of NetworkX?

It provides degree, PageRank, connected-component and short-cycle context. These are evidence cues—not guilt indicators. The score contributes only 10% to priority.

### How does the project reflect MASAK/FATF?

It adopts risk-based prioritisation, evidence quality, payment transparency, beneficial-ownership and human-governance principles from official public guidance. It does not claim regulatory certification, and it states that suspicious transaction assessment is independent of amount.

### What would production require?

Approved live screening data, temporal graph infrastructure, privacy impact assessment, encryption, fine-grained access, immutable audit trails, independent validation, drift monitoring, case-system integration, legal review and MLRO ownership.

## Demonstration path

1. Start with the executive README finding.
2. Open `artifacts/figures/executive-overview.png`.
3. Show one alert row and trace its source transaction IDs.
4. Compare rule severity, KYC, anomaly and graph components.
5. Open the case and its human-review packet.
6. Show synthetic validation performance and false positives.
7. Finish with KYC backlog remediation and governance limits.
