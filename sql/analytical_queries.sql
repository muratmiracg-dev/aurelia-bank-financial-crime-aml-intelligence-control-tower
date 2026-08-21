-- 1. Senior-review queue ordered by explainable risk score.
SELECT alert_id, customer_id, scenario_id, alert_score, alert_explanation
FROM aml.fact_alert
WHERE priority = 'HIGH'
ORDER BY alert_score DESC, alert_id;

-- 2. Open workload and nearest SLA deadline.
SELECT assigned_queue, priority, COUNT(*) AS open_cases, MIN(due_at) AS nearest_due_at
FROM aml.fact_case
WHERE case_status <> 'CLOSED'
GROUP BY assigned_queue, priority
ORDER BY MIN(due_at);

-- 3. Cash behaviour to support structuring investigations.
SELECT customer_id, DATE_TRUNC('day', transaction_ts) AS activity_day,
       COUNT(*) AS cash_in_count, SUM(amount_try) AS cash_in_try
FROM aml.fact_transaction
WHERE cash_flag AND direction = 'IN'
GROUP BY customer_id, DATE_TRUNC('day', transaction_ts)
HAVING COUNT(*) >= 3
ORDER BY cash_in_try DESC;

-- 4. Counterparty fan-in used as supporting evidence, not a final conclusion.
SELECT customer_id, COUNT(DISTINCT counterparty_id) AS unique_inbound_counterparties,
       SUM(amount_try) AS inbound_try
FROM aml.fact_transaction
WHERE direction = 'IN'
GROUP BY customer_id
ORDER BY unique_inbound_counterparties DESC, inbound_try DESC;

-- 5. Closed-case outcome mix for controlled scenario tuning.
SELECT analyst_disposition, COUNT(*) AS cases,
       ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER (), 4) AS share
FROM aml.fact_case
WHERE case_status = 'CLOSED'
GROUP BY analyst_disposition
ORDER BY cases DESC;

-- 6. Governance invariant: this query must return zero rows.
SELECT case_id
FROM aml.fact_case
WHERE human_review_required IS NOT TRUE;
