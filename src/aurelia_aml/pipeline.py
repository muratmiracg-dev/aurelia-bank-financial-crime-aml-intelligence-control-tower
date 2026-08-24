"""End-to-end governed AML analytical pipeline."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from .anomaly import score_anomalies
from .config import load_project_config
from .controls import data_quality_controls, operational_controls
from .generator import build_demo_data
from .graph import build_graph_features, graph_summary
from .kyc import score_kyc
from .reporting import create_figures
from .scenarios import run_scenarios
from .scoring import build_alerts, build_cases, validation_performance


def run_pipeline(root: str | Path, seed: int = 20260821) -> dict[str, Any]:
    """Generate data, execute analytics and write a reproducible decision pack."""
    root = Path(root).resolve()
    config = load_project_config(root)
    data = build_demo_data(config, seed=seed)
    _write_frames(data, root / "data" / "demo")
    kyc = score_kyc(data["customers"], config["assumptions"])
    rule_hits = run_scenarios(
        data["transactions"],
        data["accounts"],
        config["scenarios"],
        config["assumptions"],
    )
    graph_features = build_graph_features(data["transactions"], data["customers"])
    graph_edges = _graph_edges(data["transactions"])
    anomalies = score_anomalies(
        data["transactions"],
        data["customers"],
        config["assumptions"],
        config["scoring"],
        seed,
    )
    alerts = build_alerts(
        rule_hits,
        kyc,
        anomalies,
        graph_features,
        config["scenarios"],
        config["scoring"],
    )
    cases = build_cases(alerts, config["assumptions"], config["assumptions"]["as_of_date"])
    performance = validation_performance(alerts, data["typology_truth"])
    dq_controls = data_quality_controls(data, kyc, rule_hits)
    ops_controls = operational_controls(
        data["customers"],
        alerts,
        cases,
        performance,
        config["scoring"],
        config["assumptions"],
    )
    investigation_packets = _investigation_packets(cases, alerts)
    results = {
        "kyc_risk": kyc,
        "rule_hits": rule_hits,
        "graph_features": graph_features,
        "graph_edges": graph_edges,
        "anomaly_scores": anomalies,
        "alerts": alerts,
        "cases": cases,
        "performance": performance,
        "data_quality_controls": dq_controls,
        "operational_controls": ops_controls,
        "investigation_packets": investigation_packets,
    }
    _write_frames(results, root / "artifacts" / "results")
    figures = create_figures(results, root / "artifacts" / "figures")
    summary = _executive_summary(data, results, config, seed)
    summary_path = root / "artifacts" / "results" / "executive_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    sqlite_frames = {
        "customers": data["customers"],
        "accounts": data["accounts"],
        "typology_truth": data["typology_truth"],
        "alerts": results["alerts"],
        "cases": results["cases"],
        "performance": results["performance"],
        "data_quality_controls": results["data_quality_controls"],
        "operational_controls": results["operational_controls"],
        "investigation_packets": results["investigation_packets"],
    }
    _write_sqlite(root / "artifacts" / "aurelia_aml_demo.sqlite", sqlite_frames)
    _write_manifest(root, figures)
    return summary


def _write_frames(frames: dict[str, pd.DataFrame], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in frames.items():
        frame.to_csv(output_dir / f"{name}.csv", index=False, float_format="%.6f")


def _investigation_packets(cases: pd.DataFrame, alerts: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for case in cases.itertuples():
        evidence = alerts.loc[alerts["customer_id"] == case.customer_id]
        rows.append(
            {
                "case_id": case.case_id,
                "customer_id": case.customer_id,
                "investigative_hypothesis": (
                    "Review whether observed behaviour is consistent with the customer's "
                    "stated profile; the alert is not a conclusion."
                ),
                "scenario_evidence": " | ".join(
                    f"{row.scenario_id}: {row.rationale}" for row in evidence.itertuples()
                ),
                "required_checks": (
                    "KYC refresh; source-of-funds review; counterparty context; transaction "
                    "chronology; open-source and screening checks under approved procedures"
                ),
                "reporting_decision": "NOT_MADE__MLRO_HUMAN_DECISION_REQUIRED",
                "customer_action": "NONE_AUTOMATED",
            }
        )
    return pd.DataFrame(rows)


def _graph_edges(transactions: pd.DataFrame) -> pd.DataFrame:
    internal = transactions.loc[
        transactions["counterparty_id"].astype(str).str.startswith("C")
        & transactions["customer_id"].ne(transactions["counterparty_id"])
    ]
    return (
        internal.groupby(["customer_id", "counterparty_id"], as_index=False)
        .agg(
            transaction_count=("transaction_id", "count"),
            amount_try=("amount_try", "sum"),
            first_seen=("timestamp", "min"),
            last_seen=("timestamp", "max"),
        )
        .rename(
            columns={"customer_id": "source_customer_id", "counterparty_id": "target_customer_id"}
        )
    )


def _executive_summary(
    data: dict[str, pd.DataFrame],
    results: dict[str, pd.DataFrame],
    config: dict[str, Any],
    seed: int,
) -> dict[str, Any]:
    alerts = results["alerts"]
    cases = results["cases"]
    overall = results["performance"].loc[results["performance"]["scenario_id"] == "OVERALL"].iloc[0]
    priority = alerts["priority"].value_counts()
    status = cases["case_status"].value_counts()
    top_scenario = alerts["scenario_id"].value_counts().idxmax()
    return {
        "project": "Aurelia Bank Financial Crime & AML Intelligence Control Tower",
        "as_of_date": config["assumptions"]["as_of_date"],
        "seed": seed,
        "data_posture": {
            "bank_data": "deterministic controlled synthetic",
            "validation_labels": "isolated synthetic holdout truth",
            "watchlist_data": "synthetic placeholders only",
            "regulatory_material": "official public methodology references",
        },
        "population": {
            "customers": int(len(data["customers"])),
            "accounts": int(len(data["accounts"])),
            "transactions": int(len(data["transactions"])),
            "transaction_value_try": round(float(data["transactions"]["amount_try"].sum()), 2),
        },
        "kyc": {
            "high_risk_customers": int(results["kyc_risk"]["kyc_risk_band"].eq("HIGH").sum()),
            "overdue_reviews": int(results["kyc_risk"]["kyc_overdue_flag"].sum()),
        },
        "monitoring": {
            "alerts": int(len(alerts)),
            "unique_alerted_customers": int(alerts["customer_id"].nunique()),
            "alert_rate_pct": round(
                alerts["customer_id"].nunique() / len(data["customers"]) * 100, 2
            ),
            "high_priority": int(priority.get("HIGH", 0)),
            "medium_priority": int(priority.get("MEDIUM", 0)),
            "low_priority": int(priority.get("LOW", 0)),
            "largest_alert_scenario": str(top_scenario),
        },
        "validation": {
            "precision_pct": round(float(overall["precision"]) * 100, 2),
            "recall_pct": round(float(overall["recall"]) * 100, 2),
            "f1_pct": round(float(overall["f1_score"]) * 100, 2),
            "truth_labels_used_for_detection": False,
        },
        "case_operations": {
            "cases": int(len(cases)),
            "open": int(status.get("OPEN", 0)),
            "in_review": int(status.get("IN_REVIEW", 0)),
            "closed": int(status.get("CLOSED", 0)),
            "open_sla_breaches": int(
                (cases["case_status"].ne("CLOSED") & cases["sla_status"].eq("BREACHED")).sum()
            ),
        },
        "graph": graph_summary(results["graph_features"]),
        "controls": {
            "data_quality_passed": int(results["data_quality_controls"]["status"].eq("PASS").sum()),
            "data_quality_total": int(len(results["data_quality_controls"])),
            "management_breaches": int(
                results["operational_controls"]["status"].eq("BREACH").sum()
            ),
            "management_controls_total": int(len(results["operational_controls"])),
        },
        "governance": {
            "automated_str_submission": False,
            "automated_customer_restriction": False,
            "human_review_required": True,
            "thresholds_are_internal_parameters": True,
        },
    }


def _write_sqlite(path: Path, frames: dict[str, pd.DataFrame]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    with sqlite3.connect(path) as connection:
        for name, frame in frames.items():
            serializable = frame.copy()
            for column in serializable.columns:
                if pd.api.types.is_datetime64_any_dtype(serializable[column]):
                    serializable[column] = serializable[column].astype(str)
                elif serializable[column].dtype == "object":
                    serializable[column] = serializable[column].map(
                        lambda value: (
                            value.isoformat() if isinstance(value, pd.Timestamp) else value
                        )
                    )
            serializable.to_sql(name, connection, if_exists="replace", index=False)


def _write_manifest(root: Path, figures: list[Path]) -> None:
    candidates = [
        path for path in (root / "data" / "demo").glob("*.csv") if path.name != "transactions.csv"
    ]
    candidates += [
        path
        for path in (root / "artifacts" / "results").glob("*.csv")
        if path.name != "graph_edges.csv"
    ]
    candidates += [root / "artifacts" / "results" / "executive_summary.json", *figures]
    lines = []
    for path in sorted(candidates):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(root).as_posix()}")
    (root / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
