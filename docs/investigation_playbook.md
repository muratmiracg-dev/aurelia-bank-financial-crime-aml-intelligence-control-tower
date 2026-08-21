# Human-led investigation playbook

## Triage sequence

1. Confirm the customer/account identity and evidence lineage.
2. Read the rule rationale, observed value and internal parameter; do not infer intent.
3. Compare activity with expected turnover, occupation/industry, tenure, channel and prior behaviour.
4. Reconstruct incoming/outgoing chronology and counterparty purpose.
5. Review KYC freshness, beneficial ownership and source-of-funds evidence.
6. Perform screening and open-source checks only through approved production procedures.
7. Document supporting and contradictory evidence.
8. Choose `NO_ESCALATION`, `ENHANCED_DUE_DILIGENCE` or escalation to the designated compliance/MLRO decision maker.

## Evidence packet

Every case should contain alert IDs, transaction IDs, timestamps, value, currency, parties, channels, graph context, KYC profile, anomaly features, analyst rationale, reviewed sources and approval trail. The generated `investigation_packets.csv` is a safe template; it deliberately leaves the reporting decision unset.

## Scenario-specific questions

| Scenario | Questions to test |
|---|---|
| Structuring | Is cash intensity expected? Are deposits linked to documented sales, branches or events? Is the clustering persistent? |
| Rapid movement | Is the account a settlement, payroll, escrow or treasury account? Does the outgoing purpose match the inflow? |
| Dormant reactivation | Was reactivation customer-initiated and authenticated? Is the source of funds plausible? |
| Funnel/mule | Why are many parties paying one customer? Is there a marketplace, collections or family explanation? |
| Circular transfer | Are entities related? Is there invoicing, group treasury, round-tripping or balance manipulation context? |
| High-risk geography | `XH` is fictitious in this demo. In production, verify current approved classifications, transaction purpose and counterparties. |

## Quality standard

The analyst must distinguish observation, inference and decision. Copying a scenario description into a case conclusion is insufficient. Escalation requires coherent chronology, cited evidence, consideration of legitimate explanations and supervisor review under bank policy.

## Governance guardrail

Only an authorised human function determines whether a ŞİB/STR obligation exists. The system never recommends notifying the customer, and generated materials must not be treated as a completed regulatory form.
