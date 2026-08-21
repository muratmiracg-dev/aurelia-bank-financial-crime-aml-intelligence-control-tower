"""Alert prioritisation, human-led case aggregation and validation metrics."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def build_alerts(
    rule_hits: pd.DataFrame,
    kyc: pd.DataFrame,
    anomalies: pd.DataFrame,
    graph_features: pd.DataFrame,
    scenario_config: dict[str, Any],
    scoring_config: dict[str, Any],
) -> pd.DataFrame:
    """Combine independent signals into an explainable triage score."""
    if rule_hits.empty:
        return pd.DataFrame()
    severity = {
        key: float(value["severity"]) for key, value in scenario_config["scenarios"].items()
    }
    frame = (
        rule_hits.merge(
            kyc[["customer_id", "kyc_risk_score", "kyc_risk_band", "kyc_overdue_flag"]],
            on="customer_id",
            how="left",
            validate="many_to_one",
        )
        .merge(
            anomalies[["customer_id", "anomaly_score", "anomaly_flag"]],
            on="customer_id",
            how="left",
            validate="many_to_one",
        )
        .merge(
            graph_features[
                ["customer_id", "graph_risk_score", "short_cycle_member", "total_degree"]
            ],
            on="customer_id",
            how="left",
            validate="many_to_one",
        )
    )
    frame["scenario_severity"] = frame["scenario_id"].map(severity)
    weights = scoring_config["alert_scoring"]
    frame["alert_score"] = (
        frame["scenario_severity"] * float(weights["scenario_weight"])
        + frame["kyc_risk_score"] * float(weights["kyc_weight"])
        + frame["anomaly_score"] * float(weights["anomaly_weight"])
        + frame["graph_risk_score"] * float(weights["graph_weight"])
    ).clip(0, 100)
    frame["alert_score"] = frame["alert_score"].round(2)
    frame["priority"] = np.select(
        [
            frame["alert_score"] >= float(weights["high_priority_floor"]),
            frame["alert_score"] >= float(weights["medium_priority_floor"]),
        ],
        ["HIGH", "MEDIUM"],
        default="LOW",
    )
    frame["recommended_action"] = frame["priority"].map(
        {
            "HIGH": "Senior analyst review; preserve evidence; consider enhanced due diligence",
            "MEDIUM": "Analyst review with customer and counterparty context",
            "LOW": "Queue for standard review or controlled suppression assessment",
        }
    )
    frame["alert_explanation"] = frame.apply(
        lambda row: (
            f"scenario={row.scenario_id}:{row.scenario_severity:.0f}; "
            f"KYC={row.kyc_risk_score:.1f}; anomaly={row.anomaly_score:.1f}; "
            f"graph={row.graph_risk_score:.1f}"
        ),
        axis=1,
    )
    frame = frame.sort_values(["alert_score", "window_end"], ascending=[False, False]).reset_index(
        drop=True
    )
    frame.insert(0, "alert_id", [f"AL{i:06d}" for i in range(1, len(frame) + 1)])
    return frame


def build_cases(
    alerts: pd.DataFrame, assumptions: dict[str, Any], as_of: str | pd.Timestamp
) -> pd.DataFrame:
    """Aggregate alerts into a deterministic human-review workload snapshot."""
    if alerts.empty:
        return pd.DataFrame()
    grouped = alerts.groupby("customer_id", as_index=False).agg(
        alert_count=("alert_id", "count"),
        alert_ids=("alert_id", lambda values: "|".join(values)),
        scenarios=("scenario_id", lambda values: "|".join(sorted(set(values)))),
        maximum_alert_score=("alert_score", "max"),
        total_alert_amount_try=("amount_try", "sum"),
        first_event_at=("window_start", "min"),
        last_event_at=("window_end", "max"),
    )
    high = float(80)
    medium = float(62)
    grouped["priority"] = np.select(
        [grouped["maximum_alert_score"] >= high, grouped["maximum_alert_score"] >= medium],
        ["HIGH", "MEDIUM"],
        default="LOW",
    )
    grouped = grouped.sort_values(
        ["maximum_alert_score", "last_event_at"], ascending=[False, False]
    ).reset_index(drop=True)
    grouped.insert(0, "case_id", [f"CASE{i:06d}" for i in range(1, len(grouped) + 1)])
    ops = assumptions["case_operations"]
    sla_map = {
        "HIGH": int(ops["high_priority_sla_days"]),
        "MEDIUM": int(ops["medium_priority_sla_days"]),
        "LOW": int(ops["low_priority_sla_days"]),
    }
    snapshot = pd.Timestamp(as_of)
    grouped["sla_days"] = grouped["priority"].map(sla_map)
    grouped["case_created_at"] = grouped.apply(
        lambda row: max(
            pd.Timestamp(row["last_event_at"]) + pd.to_timedelta(1, unit="h"),
            snapshot - pd.to_timedelta(max(1, int(row["sla_days"]) - 1), unit="D"),
        ),
        axis=1,
    )
    case_number = grouped["case_id"].str[-3:].astype(int)
    grouped["case_status"] = np.select(
        [case_number % 5 <= 2, case_number % 5 == 3], ["CLOSED", "IN_REVIEW"], default="OPEN"
    )
    grouped["due_at"] = grouped["case_created_at"] + pd.to_timedelta(grouped["sla_days"], unit="D")
    grouped["closed_at"] = pd.NaT
    closed = grouped["case_status"] == "CLOSED"
    grouped.loc[closed, "closed_at"] = grouped.loc[closed, "case_created_at"] + pd.to_timedelta(
        0.55 * grouped.loc[closed, "sla_days"], unit="D"
    )
    grouped["sla_status"] = np.where(
        closed,
        np.where(grouped["closed_at"] <= grouped["due_at"], "MET", "BREACHED"),
        np.where(grouped["due_at"] >= snapshot, "WITHIN_SLA", "BREACHED"),
    )
    grouped["assigned_queue"] = grouped["priority"].map(
        {"HIGH": "AML_SENIOR_REVIEW", "MEDIUM": "AML_STANDARD_REVIEW", "LOW": "AML_TRIAGE"}
    )
    grouped["analyst_disposition"] = "PENDING_HUMAN_REVIEW"
    grouped.loc[closed & (case_number % 7 != 0), "analyst_disposition"] = "NO_ESCALATION"
    grouped.loc[closed & (case_number % 7 == 0), "analyst_disposition"] = "ENHANCED_DUE_DILIGENCE"
    grouped["human_review_required"] = True
    return grouped


def validation_performance(alerts: pd.DataFrame, truth: pd.DataFrame) -> pd.DataFrame:
    """Measure synthetic holdout retrieval without exposing labels to detection."""
    predicted = set(zip(alerts["scenario_id"], alerts["customer_id"], strict=False))
    expected = set(zip(truth["scenario_id"], truth["customer_id"], strict=False))
    rows = []
    for scenario in sorted(truth["scenario_id"].unique()):
        scenario_predicted = {pair for pair in predicted if pair[0] == scenario}
        scenario_expected = {pair for pair in expected if pair[0] == scenario}
        rows.append(_metric_row(scenario, scenario_predicted, scenario_expected))
    rows.append(_metric_row("OVERALL", predicted, expected))
    return pd.DataFrame(rows)


def _metric_row(
    scenario: str, predicted: set[tuple[str, str]], expected: set[tuple[str, str]]
) -> dict[str, object]:
    true_positive = len(predicted & expected)
    false_positive = len(predicted - expected)
    false_negative = len(expected - predicted)
    precision = true_positive / max(true_positive + false_positive, 1)
    recall = true_positive / max(true_positive + false_negative, 1)
    return {
        "scenario_id": scenario,
        "true_positives": true_positive,
        "false_positives": false_positive,
        "false_negatives": false_negative,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(2 * precision * recall / max(precision + recall, 1e-12), 4),
    }
