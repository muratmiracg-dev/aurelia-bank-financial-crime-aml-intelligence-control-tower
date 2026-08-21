"""Governed configuration loading and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .constants import SCENARIO_IDS
from .exceptions import ConfigurationError


def load_yaml(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise ConfigurationError(f"Configuration file not found: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ConfigurationError(f"Configuration root must be a mapping: {path}")
    return payload


def load_project_config(root: str | Path) -> dict[str, Any]:
    root = Path(root)
    config = {
        "assumptions": load_yaml(root / "config" / "assumptions.yml"),
        "scenarios": load_yaml(root / "config" / "scenarios.yml"),
        "scoring": load_yaml(root / "config" / "scoring.yml"),
    }
    validate_project_config(config)
    return config


def validate_project_config(config: dict[str, Any]) -> None:
    assumptions = config.get("assumptions", {})
    population = assumptions.get("synthetic_population", {})
    if any(
        int(population.get(key, 0)) <= 0
        for key in ("customers", "accounts", "baseline_transactions")
    ):
        raise ConfigurationError("Synthetic population settings must be positive integers")
    scenarios = config.get("scenarios", {}).get("scenarios", {})
    missing = [scenario for scenario in SCENARIO_IDS if scenario not in scenarios]
    if missing:
        raise ConfigurationError(f"Missing governed scenarios: {missing}")
    weights = config.get("scoring", {}).get("alert_scoring", {})
    total = sum(
        float(weights.get(key, 0))
        for key in ("scenario_weight", "kyc_weight", "anomaly_weight", "graph_weight")
    )
    if abs(total - 1.0) > 1e-9:
        raise ConfigurationError("Alert scoring weights must sum to 1.0")
    if assumptions.get("synthetic_high_risk_jurisdiction") not in assumptions.get(
        "jurisdiction_risk", {}
    ):
        raise ConfigurationError("Synthetic high-risk jurisdiction must exist in the risk taxonomy")
