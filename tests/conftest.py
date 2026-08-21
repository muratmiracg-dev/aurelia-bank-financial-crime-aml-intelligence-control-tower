from pathlib import Path

import pytest

from aurelia_aml.anomaly import score_anomalies
from aurelia_aml.config import load_project_config
from aurelia_aml.generator import build_demo_data
from aurelia_aml.graph import build_graph_features
from aurelia_aml.kyc import score_kyc
from aurelia_aml.scenarios import run_scenarios
from aurelia_aml.scoring import build_alerts, build_cases, validation_performance


@pytest.fixture(scope="session")
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def config(project_root: Path):
    return load_project_config(project_root)


@pytest.fixture(scope="session")
def demo(config):
    return build_demo_data(config)


@pytest.fixture(scope="session")
def analytics(config, demo):
    kyc = score_kyc(demo["customers"], config["assumptions"])
    hits = run_scenarios(
        demo["transactions"], demo["accounts"], config["scenarios"], config["assumptions"]
    )
    graph = build_graph_features(demo["transactions"], demo["customers"])
    anomaly = score_anomalies(
        demo["transactions"],
        demo["customers"],
        config["assumptions"],
        config["scoring"],
        20260821,
    )
    alerts = build_alerts(hits, kyc, anomaly, graph, config["scenarios"], config["scoring"])
    cases = build_cases(alerts, config["assumptions"], config["assumptions"]["as_of_date"])
    performance = validation_performance(alerts, demo["typology_truth"])
    return {
        "kyc": kyc,
        "hits": hits,
        "graph": graph,
        "anomaly": anomaly,
        "alerts": alerts,
        "cases": cases,
        "performance": performance,
    }
