-- Aurelia Bank AML analytical schema (PostgreSQL 16 style)
-- Synthetic portfolio demonstration: no production PII is stored.

CREATE SCHEMA IF NOT EXISTS aml;

CREATE TABLE IF NOT EXISTS aml.dim_customer (
    customer_id                  varchar(16) PRIMARY KEY,
    customer_type                varchar(16) NOT NULL,
    segment                      varchar(32) NOT NULL,
    residence_country            varchar(8) NOT NULL,
    onboarding_channel           varchar(32) NOT NULL,
    onboarding_date              date NOT NULL,
    pep_flag                     boolean NOT NULL,
    synthetic_watchlist_match    boolean NOT NULL,
    expected_monthly_turnover_try numeric(18,2) NOT NULL CHECK (expected_monthly_turnover_try > 0),
    kyc_review_due_date           date NOT NULL,
    data_class                    varchar(32) NOT NULL CHECK (data_class = 'CONTROLLED_SYNTHETIC')
);

CREATE TABLE IF NOT EXISTS aml.dim_account (
    account_id       varchar(16) PRIMARY KEY,
    customer_id      varchar(16) NOT NULL REFERENCES aml.dim_customer(customer_id),
    account_type     varchar(24) NOT NULL,
    currency         char(3) NOT NULL,
    opened_date      date NOT NULL,
    status           varchar(16) NOT NULL,
    dormant_flag     boolean NOT NULL,
    dormant_since    date,
    data_class       varchar(32) NOT NULL
);

CREATE TABLE IF NOT EXISTS aml.fact_transaction (
    transaction_id       varchar(20) PRIMARY KEY,
    transaction_ts       timestamp NOT NULL,
    customer_id          varchar(16) NOT NULL REFERENCES aml.dim_customer(customer_id),
    account_id           varchar(16) NOT NULL REFERENCES aml.dim_account(account_id),
    direction            varchar(3) NOT NULL CHECK (direction IN ('IN', 'OUT')),
    counterparty_id      varchar(32) NOT NULL,
    counterparty_country varchar(8) NOT NULL,
    channel              varchar(24) NOT NULL,
    transaction_type     varchar(32) NOT NULL,
    amount_try           numeric(18,2) NOT NULL CHECK (amount_try > 0),
    currency             char(3) NOT NULL,
    cash_flag            boolean NOT NULL,
    device_id            varchar(32) NOT NULL,
    data_class           varchar(32) NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_transaction_customer_ts
    ON aml.fact_transaction (customer_id, transaction_ts);
CREATE INDEX IF NOT EXISTS ix_transaction_counterparty
    ON aml.fact_transaction (counterparty_id, transaction_ts);
CREATE INDEX IF NOT EXISTS ix_transaction_country
    ON aml.fact_transaction (counterparty_country, transaction_ts);

CREATE TABLE IF NOT EXISTS aml.fact_rule_hit (
    hit_id                  varchar(16) PRIMARY KEY,
    customer_id             varchar(16) NOT NULL REFERENCES aml.dim_customer(customer_id),
    account_id              varchar(16) NOT NULL REFERENCES aml.dim_account(account_id),
    scenario_id             varchar(32) NOT NULL,
    window_start            timestamp NOT NULL,
    window_end              timestamp NOT NULL,
    transaction_count       integer NOT NULL,
    amount_try              numeric(18,2) NOT NULL,
    evidence_value          numeric(18,4) NOT NULL,
    threshold_value         numeric(18,4) NOT NULL,
    source_transaction_ids  text NOT NULL,
    rationale               text NOT NULL
);

CREATE TABLE IF NOT EXISTS aml.fact_alert (
    alert_id             varchar(16) PRIMARY KEY,
    hit_id               varchar(16) NOT NULL REFERENCES aml.fact_rule_hit(hit_id),
    customer_id          varchar(16) NOT NULL REFERENCES aml.dim_customer(customer_id),
    scenario_id          varchar(32) NOT NULL,
    alert_score          numeric(6,2) NOT NULL CHECK (alert_score BETWEEN 0 AND 100),
    priority             varchar(8) NOT NULL CHECK (priority IN ('HIGH', 'MEDIUM', 'LOW')),
    kyc_risk_score       numeric(6,2) NOT NULL,
    anomaly_score        numeric(6,2) NOT NULL,
    graph_risk_score     numeric(6,2) NOT NULL,
    alert_explanation    text NOT NULL,
    recommended_action   text NOT NULL
);

CREATE TABLE IF NOT EXISTS aml.fact_case (
    case_id                 varchar(16) PRIMARY KEY,
    customer_id             varchar(16) NOT NULL REFERENCES aml.dim_customer(customer_id),
    priority                varchar(8) NOT NULL,
    case_status             varchar(16) NOT NULL,
    assigned_queue          varchar(32) NOT NULL,
    case_created_at         timestamp NOT NULL,
    due_at                  timestamp NOT NULL,
    closed_at               timestamp,
    sla_status              varchar(16) NOT NULL,
    analyst_disposition     varchar(48) NOT NULL,
    human_review_required   boolean NOT NULL DEFAULT true,
    CHECK (human_review_required)
);

-- Validation truth belongs in a separately permissioned schema in real deployments.
CREATE SCHEMA IF NOT EXISTS aml_validation;
CREATE TABLE IF NOT EXISTS aml_validation.typology_truth (
    case_id          varchar(16) NOT NULL,
    scenario_id      varchar(32) NOT NULL,
    customer_id      varchar(16) NOT NULL,
    injection_start  timestamp NOT NULL,
    injection_end    timestamp NOT NULL,
    validation_only  boolean NOT NULL CHECK (validation_only),
    PRIMARY KEY (case_id, scenario_id, customer_id)
);

REVOKE ALL ON SCHEMA aml_validation FROM PUBLIC;
