import json
from pathlib import Path

from fastapi.testclient import TestClient

from aurelia_aml.api import app
from aurelia_aml.pipeline import run_pipeline


def test_pipeline_integration(project_root: Path):
    summary = run_pipeline(project_root)
    assert summary["population"]["customers"] == 1800
    assert summary["controls"]["data_quality_passed"] == 12
    assert summary["governance"]["human_review_required"] is True
    assert (project_root / "artifacts/aurelia_aml_demo.sqlite").exists()
    assert (project_root / "artifacts/figures/executive-overview.png").exists()


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
