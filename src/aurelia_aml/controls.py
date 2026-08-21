"""Data-quality, model-validation and operational risk controls."""

from __future__ import annotations

from typing import Any

import pandas as pd


def data_quality_controls(
    data: dict[str, pd.DataFrame],
    kyc: pd.DataFrame,
    rule_hits: pd.DataFrame,
) -> pd.DataFrame:
    """Return evidence for required data and pipeline invariants."""
    customers = data["customers"]
    accounts = data["accounts"]
    transactions = data["transactions"]
    known_accounts = set(accounts["account_id"])
    known_customers = set(customers["customer_id"])
    checks = [
        ("DQ-01", "Customer identifiers are unique", customers["customer_id"].is_unique),
        ("DQ-02", "Account identifiers are unique", accounts["account_id"].is_unique),
        (
            "DQ-03",
            "Transaction identifiers are unique",
            transactions["transaction_id"].is_unique,
        ),
        (
            "DQ-04",
            "Every account maps to a known customer",
            set(accounts["customer_id"]).issubset(known_customers),
        ),
        (
            "DQ-05",
            "Every transaction maps to a known account",
            set(transactions["account_id"]).issubset(known_accounts),
        ),
        (
            "DQ-06",
            "Every transaction maps to a known customer",
            set(transactions["customer_id"]).issubset(known_customers),
        ),
        ("DQ-07", "Transaction amounts are positive", (transactions["amount_try"] > 0).all()),
        (
            "DQ-08",
            "Transaction timestamps are complete",
            transactions["timestamp"].notna().all(),
        ),
        ("DQ-09", "KYC scores remain within 0-100", kyc["kyc_risk_score"].between(0, 100).all()),
        (
            "DQ-10",
            "Rule-hit evidence contains source transaction IDs",
            rule_hits["source_transaction_ids"].fillna("").ne("").all(),
        ),
        (
            "DQ-11",
            "Validation truth is isolated and labelled",
            data["typology_truth"]["validation_only"].eq(True).all(),  # noqa: E712
        ),
        (
            "DQ-12",
            "Only controlled synthetic records are in customer data",
            customers["data_class"].eq("CONTROLLED_SYNTHETIC").all(),
        ),
    ]
    return pd.DataFrame(
        [
            {
                "control_id": control_id,
                "control": description,
                "status": "PASS" if result else "FAIL",
            }
            for control_id, description, result in checks
        ]
    )


def operational_controls(
    customers: pd.DataFrame,
    alerts: pd.DataFrame,
    cases: pd.DataFrame,
    performance: pd.DataFrame,
    scoring_config: dict[str, Any],
    assumptions: dict[str, Any],
) -> pd.DataFrame:
    """Evaluate model and operating metrics against internal management limits."""
    validation = scoring_config["model_validation"]
    overall = performance.loc[performance["scenario_id"] == "OVERALL"].iloc[0]
    alert_rate = alerts["customer_id"].nunique() / max(len(customers), 1)
    open_cases = cases["case_status"].ne("CLOSED")
    breached_open = open_cases & cases["sla_status"].eq("BREACHED")
    high_cases = cases["priority"].eq("HIGH")
    capacity = int(assumptions["case_operations"]["analyst_daily_capacity"]) * 5
    as_of = pd.Timestamp(assumptions["as_of_date"])
    kyc_overdue_rate = pd.to_datetime(customers["kyc_review_due_date"]).lt(as_of).mean()
    metrics = [
        (
            "VAL-01",
            "Synthetic holdout recall",
            float(overall["recall"]),
            float(validation["alert_recall_floor"]),
            ">=",
        ),
        (
            "VAL-02",
            "Synthetic holdout precision reference",
            float(overall["precision"]),
            float(validation["alert_precision_reference_floor"]),
            ">=",
        ),
        (
            "VAL-03",
            "Unique-customer alert rate",
            alert_rate,
            float(validation["maximum_alert_rate"]),
            "<=",
        ),
        (
            "OPS-01",
            "Open case inventory vs weekly capacity",
            int(open_cases.sum()),
            capacity,
            "<=",
        ),
        (
            "OPS-02",
            "Open SLA breaches",
            int(breached_open.sum()),
            0,
            "<=",
        ),
        (
            "OPS-03",
            "High-priority cases with human-review flag",
            int(cases.loc[high_cases, "human_review_required"].sum()),
            int(high_cases.sum()),
            "==",
        ),
        (
            "OPS-04",
            "KYC reviews overdue",
            float(kyc_overdue_rate),
            float(assumptions["case_operations"]["maximum_kyc_overdue_rate"]),
            "<=",
        ),
    ]
    rows = []
    for control_id, metric, actual, limit, operator in metrics:
        passed = (
            actual >= limit
            if operator == ">="
            else actual <= limit
            if operator == "<="
            else actual == limit
        )
        rows.append(
            {
                "control_id": control_id,
                "metric": metric,
                "actual": round(float(actual), 4),
                "limit": round(float(limit), 4),
                "operator": operator,
                "status": "PASS" if passed else "BREACH",
            }
        )
    return pd.DataFrame(rows)
