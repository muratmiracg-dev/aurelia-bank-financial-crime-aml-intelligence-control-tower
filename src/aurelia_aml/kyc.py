"""Explainable customer-risk scoring for synthetic KYC records."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .exceptions import DataQualityError


def score_kyc(customers: pd.DataFrame, assumptions: dict[str, Any]) -> pd.DataFrame:
    """Return a transparent 0-100 inherent-risk score and component evidence."""
    required = {
        "customer_id",
        "residence_country",
        "onboarding_channel",
        "pep_flag",
        "synthetic_watchlist_match",
        "occupation_risk",
        "kyc_review_due_date",
        "beneficial_owner_complete",
        "source_of_funds_verified",
    }
    missing = required - set(customers.columns)
    if missing:
        raise DataQualityError(f"Customer data missing KYC fields: {sorted(missing)}")
    frame = customers.copy()
    risk_map = assumptions["jurisdiction_risk"]
    frame["geography_score"] = frame["residence_country"].map(risk_map).fillna(25).astype(float)
    frame["pep_score"] = frame["pep_flag"].astype(int) * 22.0
    frame["watchlist_score"] = frame["synthetic_watchlist_match"].astype(int) * 35.0
    frame["occupation_score"] = frame["occupation_risk"].map(
        {"LOW": 2.0, "MEDIUM": 10.0, "HIGH": 20.0}
    )
    frame["channel_score"] = frame["onboarding_channel"].map(
        {"BRANCH": 2.0, "RELATIONSHIP_MANAGER": 5.0, "DIGITAL": 8.0}
    )
    frame["control_gap_score"] = (~frame["beneficial_owner_complete"].astype(bool)).astype(
        int
    ) * 13.0 + (~frame["source_of_funds_verified"].astype(bool)).astype(int) * 12.0
    components = [
        "geography_score",
        "pep_score",
        "watchlist_score",
        "occupation_score",
        "channel_score",
        "control_gap_score",
    ]
    frame["kyc_risk_score"] = frame[components].sum(axis=1).clip(0, 100).round(2)
    frame["kyc_risk_band"] = np.select(
        [frame["kyc_risk_score"] >= 45, frame["kyc_risk_score"] >= 28],
        ["HIGH", "MEDIUM"],
        default="LOW",
    )
    frame["kyc_overdue_flag"] = pd.to_datetime(frame["kyc_review_due_date"]) < pd.Timestamp(
        assumptions["as_of_date"]
    )
    frame["risk_reason"] = frame.apply(_reason, axis=1)
    return frame[
        [
            "customer_id",
            *components,
            "kyc_risk_score",
            "kyc_risk_band",
            "kyc_overdue_flag",
            "risk_reason",
        ]
    ]


def _reason(row: pd.Series) -> str:
    ranked = sorted(
        (
            ("geography", row["geography_score"]),
            ("PEP", row["pep_score"]),
            ("synthetic screening", row["watchlist_score"]),
            ("occupation", row["occupation_score"]),
            ("channel", row["channel_score"]),
            ("KYC control gap", row["control_gap_score"]),
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    material = [f"{name}={score:.0f}" for name, score in ranked if score > 0][:3]
    return "; ".join(material) if material else "No material inherent-risk factors"
