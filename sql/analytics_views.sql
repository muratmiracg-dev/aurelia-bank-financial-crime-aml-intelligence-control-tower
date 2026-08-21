CREATE OR REPLACE VIEW aml.v_alert_funnel AS
SELECT
    scenario_id,
    priority,
    COUNT(*) AS alerts,
    COUNT(DISTINCT customer_id) AS customers,
    ROUND(AVG(alert_score), 2) AS average_alert_score
FROM aml.fact_alert
GROUP BY scenario_id, priority;

CREATE OR REPLACE VIEW aml.v_case_sla_inventory AS
SELECT
    assigned_queue,
    priority,
    case_status,
    sla_status,
    COUNT(*) AS cases,
    MIN(due_at) AS earliest_due_at
FROM aml.fact_case
GROUP BY assigned_queue, priority, case_status, sla_status;

CREATE OR REPLACE VIEW aml.v_customer_transaction_profile AS
SELECT
    customer_id,
    COUNT(*) AS transaction_count,
    SUM(amount_try) AS total_amount_try,
    SUM(amount_try) FILTER (WHERE direction = 'IN') AS incoming_amount_try,
    SUM(amount_try) FILTER (WHERE direction = 'OUT') AS outgoing_amount_try,
    SUM(amount_try) FILTER (WHERE cash_flag) AS cash_amount_try,
    COUNT(DISTINCT counterparty_id) AS unique_counterparties,
    MAX(amount_try) AS maximum_transaction_try
FROM aml.fact_transaction
GROUP BY customer_id;

CREATE OR REPLACE VIEW aml.v_alert_case_lineage AS
SELECT
    a.alert_id,
    a.hit_id,
    a.customer_id,
    a.scenario_id,
    a.alert_score,
    a.priority AS alert_priority,
    c.case_id,
    c.case_status,
    c.sla_status,
    c.analyst_disposition,
    c.human_review_required
FROM aml.fact_alert a
LEFT JOIN aml.fact_case c ON c.customer_id = a.customer_id;
