import copy

import pandas as pd
import pytest

from aurelia_aml.controls import data_quality_controls, operational_controls
from aurelia_aml.scoring import build_alerts, build_cases, validation_performance


def test_alerts_are_explainable(analytics):
    alerts = analytics["alerts"]
    assert alerts["alert_id"].is_unique
    assert alerts["alert_score"].between(0, 100).all()
    assert alerts["alert_explanation"].str.contains("scenario=").all()
    assert alerts["recommended_action"].str.len().gt(20).all()


def test_alerts_have_realistic_false_positive_pressure(analytics):
    overall = (
        analytics["performance"].loc[analytics["performance"]["scenario_id"] == "OVERALL"].iloc[0]
    )
    assert 0.55 <= overall["precision"] <= 0.80
    assert overall["recall"] >= 0.95


def test_cases_require_human_review(analytics):
    cases = analytics["cases"]
    assert cases["human_review_required"].all()
    assert (
        cases["analyst_disposition"]
        .isin(["PENDING_HUMAN_REVIEW", "NO_ESCALATION", "ENHANCED_DUE_DILIGENCE"])
        .all()
    )
    assert cases["assigned_queue"].str.startswith("AML_").all()


def test_empty_alert_and_case_paths(config, analytics):
    assert build_alerts(
        pd.DataFrame(),
        analytics["kyc"],
        analytics["anomaly"],
        analytics["graph"],
        config["scenarios"],
        config["scoring"],
    ).empty
    assert build_cases(pd.DataFrame(), config["assumptions"], "2026-08-20").empty


def test_validation_metrics_empty_predictions(demo):
    empty = pd.DataFrame(columns=["scenario_id", "customer_id"])
    metrics = validation_performance(empty, demo["typology_truth"])
    overall = metrics.loc[metrics["scenario_id"] == "OVERALL"].iloc[0]
    assert overall["precision"] == 0
    assert overall["recall"] == 0


def test_data_quality_controls_pass(demo, analytics):
    controls = data_quality_controls(demo, analytics["kyc"], analytics["hits"])
    assert len(controls) == 12
    assert set(controls["status"]) == {"PASS"}


def test_operational_controls(config, demo, analytics):
    controls = operational_controls(
        demo["customers"],
        analytics["alerts"],
        analytics["cases"],
        analytics["performance"],
        config["scoring"],
        config["assumptions"],
    )
    assert len(controls) == 7
    assert set(controls["operator"]) == {">=", "<=", "=="}
    assert set(controls["status"]) <= {"PASS", "BREACH"}


def test_alert_scoring_rejects_invalid_or_unmatched_risk_signals(config, analytics):
    hits = analytics["hits"].head(1)
    customer_id = hits.iloc[0]["customer_id"]
    base = {
        "kyc": analytics["kyc"].loc[lambda frame: frame["customer_id"] == customer_id].copy(),
        "anomaly": analytics["anomaly"]
        .loc[lambda frame: frame["customer_id"] == customer_id]
        .copy(),
        "graph": analytics["graph"].loc[lambda frame: frame["customer_id"] == customer_id].copy(),
    }
    cases = [
        ("kyc", "kyc_risk_score", float("nan")),
        ("anomaly", "anomaly_score", float("inf")),
        ("graph", "graph_risk_score", -1.0),
    ]
    for frame_name, column, value in cases:
        frames = {name: frame.copy() for name, frame in base.items()}
        frames[frame_name].loc[:, column] = value
        with pytest.raises(ValueError, match="risk score"):
            build_alerts(
                hits,
                frames["kyc"],
                frames["anomaly"],
                frames["graph"],
                config["scenarios"],
                config["scoring"],
            )


@pytest.mark.parametrize("value", [True, -0.1, float("nan"), float("inf")])
def test_alert_scoring_rejects_invalid_weights(config, analytics, value):
    scoring = copy.deepcopy(config["scoring"])
    scoring["alert_scoring"]["scenario_weight"] = value
    with pytest.raises(ValueError, match="weights"):
        build_alerts(
            analytics["hits"].head(1),
            analytics["kyc"],
            analytics["anomaly"],
            analytics["graph"],
            config["scenarios"],
            scoring,
        )


def test_alert_scoring_rejects_weights_that_do_not_sum_to_one(config, analytics):
    scoring = copy.deepcopy(config["scoring"])
    scoring["alert_scoring"]["scenario_weight"] = 0.99
    with pytest.raises(ValueError, match="sum to one"):
        build_alerts(
            analytics["hits"].head(1),
            analytics["kyc"],
            analytics["anomaly"],
            analytics["graph"],
            config["scenarios"],
            scoring,
        )


def _alert(customer: str, score: float, window_end: str) -> dict:
    end = pd.Timestamp(window_end)
    return {
        "alert_id": f"A-{customer}",
        "customer_id": customer,
        "scenario_id": "SC",
        "alert_score": score,
        "amount_try": 1000.0,
        "window_start": end - pd.Timedelta(days=1),
        "window_end": end,
    }


def test_case_opens_at_first_alert_and_overdue_work_is_breached(config):
    # A High case (1-day SLA) whose alert fired ten days before the snapshot cannot be
    # "within SLA": it used to be re-dated to the snapshot day and always looked on time.
    alerts = pd.DataFrame(
        [_alert(f"C{i:03d}", 85.0, "2026-08-10 09:00") for i in range(10)]
        + [_alert("C999", 85.0, "2026-08-19 22:00")]
    )
    cases = build_cases(alerts, config["assumptions"], "2026-08-20")
    old = cases[cases["customer_id"] != "C999"]
    assert (old["case_created_at"] == pd.Timestamp("2026-08-10 10:00")).all()
    assert (old["due_at"] == pd.Timestamp("2026-08-11 10:00")).all()
    # Review effort above the SLA closes late; nothing that old is still within SLA.
    assert old["case_status"].eq("CLOSED").all()
    assert set(old["sla_status"]) == {"MET", "BREACHED"}
    late = old["closed_at"] > old["due_at"]
    assert (old.loc[late, "sla_status"] == "BREACHED").all()
    fresh = cases[cases["customer_id"] == "C999"].iloc[0]
    assert fresh["case_status"] in {"OPEN", "IN_REVIEW"}
    assert fresh["sla_status"] == "WITHIN_SLA"


def test_open_cases_past_due_are_counted_as_breaches(config, demo, analytics):
    # Effort factor 1.6 for case number 8: due after 1 day, still in review after 1.5 days.
    alerts = pd.DataFrame(
        [_alert(f"C{i:03d}", 85.0 - i * 0.1, "2026-08-18 12:00") for i in range(1, 11)]
    )
    cases = build_cases(alerts, config["assumptions"], "2026-08-20")
    eighth = cases.loc[cases["case_id"] == "CASE000008"].iloc[0]
    assert eighth["case_status"] == "IN_REVIEW"
    assert eighth["sla_status"] == "BREACHED"
    controls = operational_controls(
        demo["customers"],
        analytics["alerts"],
        cases,
        analytics["performance"],
        config["scoring"],
        config["assumptions"],
    )
    ops2 = controls.set_index("control_id").loc["OPS-02"]
    assert ops2["status"] == "BREACH"
