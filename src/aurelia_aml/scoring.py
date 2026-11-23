"""Alert prioritisation, human-led case aggregation and validation metrics."""

from __future__ import annotations

import math
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
    risk_columns = ["scenario_severity", "kyc_risk_score", "anomaly_score", "graph_risk_score"]
    numeric_risk = frame[risk_columns].apply(pd.to_numeric, errors="coerce")
    if numeric_risk.isna().any().any() or not np.isfinite(numeric_risk.to_numpy()).all():
        raise ValueError(
            "Every alert must have finite scenario, KYC, anomaly and graph risk scores"
        )
    if ((numeric_risk < 0) | (numeric_risk > 100)).any().any():
        raise ValueError("Alert risk scores must be between 0 and 100")
    frame[risk_columns] = numeric_risk
    weights = scoring_config["alert_scoring"]
    weight_names = ("scenario_weight", "kyc_weight", "anomaly_weight", "graph_weight")
    raw_weights = [weights.get(name) for name in weight_names]
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in raw_weights):
        raise ValueError("Alert scoring weights must be numeric and must not be booleans")
    numeric_weights = [float(value) for value in raw_weights]
    if not all(
        math.isfinite(value) and value >= 0 for value in numeric_weights
    ) or not math.isclose(sum(numeric_weights), 1.0, abs_tol=1e-9):
        raise ValueError("Alert scoring weights must be finite, non-negative and sum to one")
    frame["alert_score"] = (
        frame["scenario_severity"] * numeric_weights[0]
        + frame["kyc_risk_score"] * numeric_weights[1]
        + frame["anomaly_score"] * numeric_weights[2]
        + frame["graph_risk_score"] * numeric_weights[3]
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


# Review effort per case as a multiple of its SLA, cycled by case number.
REVIEW_EFFORT_FACTORS = (0.4, 0.55, 0.7, 0.85, 0.55, 0.95, 1.2, 0.6, 1.6, 0.75)


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
        first_alert_at=("window_end", "min"),
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
    # The case opens when the customer's first alert is generated (its rule window closes,
    # plus a one-hour monitoring batch lag). It used to be pulled forward to at most
    # ``sla_days - 1`` before the snapshot, which made every open case look in SLA.
    grouped["case_created_at"] = pd.to_datetime(grouped["first_alert_at"]) + pd.to_timedelta(
        1, unit="h"
    )
    grouped = grouped.drop(columns="first_alert_at")
    case_number = grouped["case_id"].str[-3:].astype(int)
    # Deterministic synthetic review effort as a multiple of the SLA (mean ~0.8): most cases
    # finish in time, a minority runs late. Status follows from age, not from a fixed mix.
    review_factor = case_number.mod(len(REVIEW_EFFORT_FACTORS)).map(
        dict(enumerate(REVIEW_EFFORT_FACTORS))
    )
    review_time = pd.to_timedelta(review_factor * grouped["sla_days"], unit="D")
    finished_at = grouped["case_created_at"] + review_time
    started = grouped["case_created_at"] + 0.25 * review_time <= snapshot
    grouped["case_status"] = np.select(
        [finished_at <= snapshot, started], ["CLOSED", "IN_REVIEW"], default="OPEN"
    )
    grouped["due_at"] = grouped["case_created_at"] + pd.to_timedelta(grouped["sla_days"], unit="D")
    grouped["closed_at"] = pd.NaT
    closed = grouped["case_status"] == "CLOSED"
    grouped.loc[closed, "closed_at"] = finished_at[closed]
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
