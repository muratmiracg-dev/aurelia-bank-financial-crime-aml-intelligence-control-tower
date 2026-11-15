import importlib.util
import json
import shutil
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aurelia_aml.api import app
from aurelia_aml.manifest import MANIFEST_NAME, write_manifest
from aurelia_aml.pipeline import run_pipeline


def _isolated_root(project_root: Path, target: Path) -> Path:
    """A throwaway project root, so tests never rewrite the committed decision pack."""
    shutil.copytree(project_root / "config", target / "config")
    shutil.copytree(project_root / "data" / "reference", target / "data" / "reference")
    for relative in ("excel", "presentation", "report"):
        shutil.copytree(project_root / relative, target / relative)
    return target


def _load_compare_outputs(project_root: Path):
    path = project_root / "scripts" / "compare_outputs.py"
    spec = importlib.util.spec_from_file_location("compare_outputs", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def pipeline_root(project_root: Path, tmp_path_factory) -> Path:
    root = _isolated_root(project_root, tmp_path_factory.mktemp("pipeline"))
    run_pipeline(root)
    return root


def test_pipeline_integration(pipeline_root: Path):
    summary = json.loads(
        (pipeline_root / "artifacts/results/executive_summary.json").read_text(encoding="utf-8")
    )
    assert summary["population"]["customers"] == 1800
    assert summary["controls"]["data_quality_passed"] == 12
    assert summary["governance"]["human_review_required"] is True
    assert (pipeline_root / "artifacts/aurelia_aml_demo.sqlite").exists()
    assert (pipeline_root / "artifacts/figures/executive-overview.png").exists()


def test_pipeline_manifest_matches_build_manifest(pipeline_root: Path):
    # `make demo` used to write a manifest without the SQLite layer and the static
    # deliverables, so `make demo` and `make verify` disagreed on MANIFEST.sha256.
    written = (pipeline_root / MANIFEST_NAME).read_text(encoding="utf-8")
    relatives = [line.split("  ", 1)[1] for line in written.splitlines()]
    for expected in (
        "artifacts/aurelia_aml_demo.sqlite",
        "excel/Aurelia_Bank_AML_Investigation_Workbench.xlsx",
        "presentation/Aurelia_Bank_AML_Executive_Deck_EN.pptx",
        "report/Aurelia_Bank_AML_Executive_Report.pdf",
    ):
        assert expected in relatives
    assert "data/demo/transactions.csv" not in relatives
    assert write_manifest(pipeline_root) == len(relatives)
    assert (pipeline_root / MANIFEST_NAME).read_text(encoding="utf-8") == written


def test_committed_outputs_match_regeneration(project_root: Path, pipeline_root: Path):
    compare_outputs = _load_compare_outputs(project_root)
    assert compare_outputs.compare(project_root, pipeline_root) == []


def test_compare_outputs_detects_stale_committed_values(
    project_root: Path, pipeline_root: Path, tmp_path: Path
):
    compare_outputs = _load_compare_outputs(project_root)
    stale = tmp_path / "stale"
    for relative in ("data/demo", "artifacts/results"):
        shutil.copytree(pipeline_root / relative, stale / relative)
    shutil.copy2(
        pipeline_root / "artifacts/aurelia_aml_demo.sqlite",
        stale / "artifacts/aurelia_aml_demo.sqlite",
    )
    alerts = stale / "artifacts/results/alerts.csv"
    lines = alerts.read_text(encoding="utf-8").splitlines()
    header = lines[0].split(",")
    first = lines[1].split(",")
    column = header.index("alert_score")
    first[column] = f"{float(first[column]) + 0.5:.6f}"
    lines[1] = ",".join(first)
    alerts.write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary_path = stale / "artifacts/results/executive_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["monitoring"]["alerts"] += 1
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    with sqlite3.connect(stale / "artifacts/aurelia_aml_demo.sqlite") as connection:
        connection.execute("DELETE FROM cases WHERE rowid = 1")

    errors = compare_outputs.compare(stale, pipeline_root)
    assert any(
        e.startswith("artifacts/results/alerts.csv row 1 column alert_score") for e in errors
    )
    assert any("executive_summary.json.monitoring.alerts" in e for e in errors)
    assert any(e.startswith("artifacts/aurelia_aml_demo.sqlite:cases") for e in errors)
    assert compare_outputs.main(["compare_outputs.py", str(stale), str(pipeline_root)]) == 1


def test_api_read_only_outputs(project_root: Path, monkeypatch):
    monkeypatch.setenv("AURELIA_AML_PROJECT_ROOT", str(project_root))
    client = TestClient(app)
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 200
    summary = client.get("/api/v1/summary")
    assert summary.status_code == 200
    assert summary.json()["project"].startswith("Aurelia Bank")
    assert 1 <= len(client.get("/api/v1/alerts?priority=HIGH&limit=5").json()) <= 5
    assert len(client.get("/api/v1/cases?limit=3").json()) == 3
    assert "data_quality" in client.get("/api/v1/controls").json()


def test_api_scenario_filter(project_root: Path, monkeypatch):
    monkeypatch.setenv("AURELIA_AML_PROJECT_ROOT", str(project_root))
    client = TestClient(app)
    rows = client.get("/api/v1/alerts?scenario=STRUCTURING&limit=200").json()
    assert rows
    assert {row["scenario_id"] for row in rows} == {"STRUCTURING"}


def test_api_key_and_missing_outputs(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AURELIA_AML_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("AURELIA_AML_API_KEY", "secret")
    client = TestClient(app)
    assert client.get("/health/ready").status_code == 503
    assert client.get("/api/v1/summary").status_code == 401
    response = client.get("/api/v1/summary", headers={"X-API-Key": "secret"})
    assert response.status_code == 503
    assert client.get("/api/v1/alerts", headers={"X-API-Key": "secret"}).status_code == 503


def test_summary_json_is_valid(project_root: Path):
    payload = json.loads(
        (project_root / "artifacts/results/executive_summary.json").read_text(encoding="utf-8")
    )
    assert payload["validation"]["truth_labels_used_for_detection"] is False
