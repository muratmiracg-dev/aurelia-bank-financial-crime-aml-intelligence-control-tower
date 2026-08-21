import pandas as pd

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
