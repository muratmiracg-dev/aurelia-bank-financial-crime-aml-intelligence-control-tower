import pandas as pd
import pytest

from aurelia_aml.anomaly import score_anomalies
from aurelia_aml.exceptions import DataQualityError
from aurelia_aml.graph import graph_summary
from aurelia_aml.kyc import score_kyc
from aurelia_aml.scenarios import run_scenarios


def test_kyc_scores_and_bands(analytics):
    frame = analytics["kyc"]
    assert frame["kyc_risk_score"].between(0, 100).all()
    assert set(frame["kyc_risk_band"]) <= {"LOW", "MEDIUM", "HIGH"}
    assert frame["kyc_overdue_flag"].any()
    assert frame["kyc_risk_band"].eq("HIGH").sum() >= 10


def test_kyc_missing_columns(config, demo):
    with pytest.raises(DataQualityError):
        score_kyc(demo["customers"].drop(columns="pep_flag"), config["assumptions"])


def test_anomaly_output(analytics):
    frame = analytics["anomaly"]
    assert frame["anomaly_score"].between(0, 100).all()
    assert 70 <= frame["anomaly_flag"].sum() <= 110
    assert frame["unique_counterparties"].ge(0).all()


def test_anomaly_is_reproducible(config, demo):
    first = score_anomalies(
        demo["transactions"], demo["customers"], config["assumptions"], config["scoring"], 7
    )
    second = score_anomalies(
        demo["transactions"], demo["customers"], config["assumptions"], config["scoring"], 7
    )
    pd.testing.assert_series_equal(first["anomaly_score"], second["anomaly_score"])


def test_graph_output(analytics):
    frame = analytics["graph"]
    assert frame["graph_risk_score"].between(0, 100).all()
    assert frame["short_cycle_member"].sum() >= 24
    summary = graph_summary(frame)
    assert summary["customers_in_short_cycles"] >= 24
    assert summary["maximum_component_size"] >= 1


def test_all_scenarios_execute(analytics):
    hits = analytics["hits"]
    assert set(hits["scenario_id"]) == {
        "STRUCTURING",
        "RAPID_MOVEMENT",
        "DORMANT_REACTIVATION",
        "FUNNEL_MULE",
        "CIRCULAR_TRANSFER",
        "HIGH_RISK_GEOGRAPHY",
    }
    assert hits["source_transaction_ids"].str.len().gt(0).all()


def test_scenario_data_quality_errors(config, demo):
    with pytest.raises(DataQualityError):
        run_scenarios(
            demo["transactions"].drop(columns="amount_try"),
            demo["accounts"],
            config["scenarios"],
            config["assumptions"],
        )
    invalid = demo["transactions"].head(2).copy()
    invalid.loc[:, "amount_try"] = -1
    with pytest.raises(DataQualityError):
        run_scenarios(invalid, demo["accounts"], config["scenarios"], config["assumptions"])


@pytest.mark.parametrize(
    "scenario,minimum_recall",
    [
        ("STRUCTURING", 0.95),
        ("RAPID_MOVEMENT", 0.95),
        ("DORMANT_REACTIVATION", 0.95),
        ("FUNNEL_MULE", 0.85),
        ("CIRCULAR_TRANSFER", 0.95),
        ("HIGH_RISK_GEOGRAPHY", 0.95),
    ],
)
def test_synthetic_holdout_recall(analytics, scenario, minimum_recall):
    row = analytics["performance"].loc[analytics["performance"]["scenario_id"] == scenario].iloc[0]
    assert row["recall"] >= minimum_recall
