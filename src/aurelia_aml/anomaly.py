"""Unsupervised behavioural anomaly signals with transparent feature output."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler


def score_anomalies(
    transactions: pd.DataFrame,
    customers: pd.DataFrame,
    assumptions: dict[str, Any],
    scoring_config: dict[str, Any],
    seed: int,
) -> pd.DataFrame:
    """Fit a deterministic Isolation Forest to customer-level behavioural features."""
    high_risk = assumptions["synthetic_high_risk_jurisdiction"]
    tx = transactions.assign(
        incoming_amount=np.where(transactions["direction"] == "IN", transactions["amount_try"], 0),
        outgoing_amount=np.where(transactions["direction"] == "OUT", transactions["amount_try"], 0),
        cash_amount=np.where(transactions["cash_flag"], transactions["amount_try"], 0),
        high_risk_amount=np.where(
            transactions["counterparty_country"] == high_risk, transactions["amount_try"], 0
        ),
    )
    aggregate = tx.groupby("customer_id", as_index=False).agg(
        transaction_count=("transaction_id", "count"),
        total_amount_try=("amount_try", "sum"),
        incoming_amount_try=("incoming_amount", "sum"),
        outgoing_amount_try=("outgoing_amount", "sum"),
        cash_amount_try=("cash_amount", "sum"),
        high_risk_amount_try=("high_risk_amount", "sum"),
        unique_counterparties=("counterparty_id", "nunique"),
        maximum_transaction_try=("amount_try", "max"),
    )
    frame = customers[["customer_id", "expected_monthly_turnover_try"]].merge(
        aggregate, on="customer_id", how="left"
    )
    numeric = [column for column in frame.columns if column != "customer_id"]
    frame[numeric] = frame[numeric].fillna(0)
    frame["turnover_deviation"] = frame["total_amount_try"] / np.maximum(
        frame["expected_monthly_turnover_try"] * 3, 1
    )
    frame["cash_ratio"] = frame["cash_amount_try"] / np.maximum(frame["total_amount_try"], 1)
    frame["high_risk_ratio"] = frame["high_risk_amount_try"] / np.maximum(
        frame["total_amount_try"], 1
    )
    frame["out_in_ratio"] = frame["outgoing_amount_try"] / np.maximum(
        frame["incoming_amount_try"], 1
    )
    model_features = [
        "transaction_count",
        "total_amount_try",
        "unique_counterparties",
        "maximum_transaction_try",
        "turnover_deviation",
        "cash_ratio",
        "high_risk_ratio",
        "out_in_ratio",
    ]
    matrix = RobustScaler().fit_transform(frame[model_features])
    contamination = float(scoring_config["model_validation"]["anomaly_contamination"])
    model = IsolationForest(
        n_estimators=180,
        contamination=contamination,
        random_state=seed,
        n_jobs=1,
    )
    model.fit(matrix)
    raw = -model.decision_function(matrix)
    frame["anomaly_score"] = pd.Series(raw).rank(pct=True).to_numpy() * 100
    frame["anomaly_score"] = frame["anomaly_score"].round(2)
    frame["anomaly_flag"] = model.predict(matrix) == -1
    return frame[["customer_id", *model_features, "anomaly_score", "anomaly_flag"]]
