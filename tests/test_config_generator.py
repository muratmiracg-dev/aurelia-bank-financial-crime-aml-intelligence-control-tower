from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest

from aurelia_aml.config import load_yaml, validate_project_config
from aurelia_aml.constants import REPORTING_CURRENCY, SCENARIO_IDS, SUPPORTED_CURRENCIES
from aurelia_aml.exceptions import ConfigurationError
from aurelia_aml.generator import build_demo_data


def test_constants():
    assert len(SCENARIO_IDS) == 6
    assert REPORTING_CURRENCY == "TRY"
    assert SUPPORTED_CURRENCIES == ("TRY", "USD", "EUR")


def test_config_loads(config):
    assert config["assumptions"]["as_of_date"] == "2026-08-20"
    assert set(config["scenarios"]["scenarios"]) == set(SCENARIO_IDS)


def test_load_yaml_errors(tmp_path: Path):
    with pytest.raises(ConfigurationError):
        load_yaml(tmp_path / "missing.yml")
    path = tmp_path / "list.yml"
    path.write_text("- x\n- y\n", encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_yaml(path)


@pytest.mark.parametrize("field", ["customers", "accounts", "baseline_transactions"])
def test_population_must_be_positive(config, field):
    bad = deepcopy(config)
    bad["assumptions"]["synthetic_population"][field] = 0
    with pytest.raises(ConfigurationError):
        validate_project_config(bad)


def test_missing_scenario_rejected(config):
    bad = deepcopy(config)
    del bad["scenarios"]["scenarios"]["STRUCTURING"]
    with pytest.raises(ConfigurationError):
        validate_project_config(bad)


def test_bad_weights_rejected(config):
    bad = deepcopy(config)
    bad["scoring"]["alert_scoring"]["graph_weight"] = 0.2
    with pytest.raises(ConfigurationError):
        validate_project_config(bad)


def test_missing_high_risk_taxonomy_rejected(config):
    bad = deepcopy(config)
    bad["assumptions"]["synthetic_high_risk_jurisdiction"] = "MISSING"
    with pytest.raises(ConfigurationError):
        validate_project_config(bad)


def test_generator_is_deterministic(config):
    first = build_demo_data(config, seed=19)
    second = build_demo_data(config, seed=19)
    pd.testing.assert_frame_equal(first["customers"].head(20), second["customers"].head(20))
    pd.testing.assert_frame_equal(first["transactions"].tail(20), second["transactions"].tail(20))


def test_population_and_referential_integrity(demo):
    assert len(demo["customers"]) == 1800
    assert len(demo["accounts"]) == 2250
    assert len(demo["transactions"]) > 48_000
    assert demo["customers"]["customer_id"].is_unique
    assert demo["accounts"]["account_id"].is_unique
    assert set(demo["accounts"]["customer_id"]) <= set(demo["customers"]["customer_id"])


def test_truth_is_isolated(demo):
    assert demo["typology_truth"]["validation_only"].all()
    assert "scenario_id" not in demo["transactions"].columns
    assert demo["typology_truth"]["customer_id"].nunique() == 92


def test_data_are_synthetic(demo):
    assert demo["customers"]["data_class"].eq("CONTROLLED_SYNTHETIC").all()
    assert demo["transactions"]["data_class"].eq("CONTROLLED_SYNTHETIC").all()
    assert demo["transactions"]["amount_try"].gt(0).all()
