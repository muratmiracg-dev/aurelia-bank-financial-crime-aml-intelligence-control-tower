"""Read-only API over verified AML decision-support outputs."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
from fastapi import Depends, FastAPI, Header, HTTPException, Query

app = FastAPI(
    title="Aurelia Bank Financial Crime & AML API",
    version="1.0.0",
    description=(
        "Read-only access to synthetic AML alerts and cases. Outputs require human review and "
        "must not be treated as findings or automated reporting decisions."
    ),
)


def _root() -> Path:
    return Path(os.getenv("AURELIA_AML_PROJECT_ROOT", ".")).resolve()


def _authorize(x_api_key: str | None = Header(default=None)) -> None:
    configured = os.getenv("AURELIA_AML_API_KEY", "")
    if configured and x_api_key != configured:
        raise HTTPException(status_code=401, detail="Invalid API key")


def _read_csv(name: str) -> pd.DataFrame:
    path = _root() / "artifacts" / "results" / f"{name}.csv"
    if not path.exists():
        raise HTTPException(status_code=503, detail="Pipeline outputs are not available")
    return pd.read_csv(path)


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready")
def ready() -> dict[str, str]:
    if not (_root() / "artifacts" / "results" / "executive_summary.json").exists():
        raise HTTPException(status_code=503, detail="Run the pipeline first")
    return {"status": "ready"}


@app.get("/api/v1/summary", dependencies=[Depends(_authorize)])
def summary() -> dict[str, object]:
    path = _root() / "artifacts" / "results" / "executive_summary.json"
    if not path.exists():
        raise HTTPException(status_code=503, detail="Pipeline outputs are not available")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/v1/alerts", dependencies=[Depends(_authorize)])
def alerts(
    priority: str | None = Query(default=None, pattern="^(HIGH|MEDIUM|LOW)$"),
    scenario: str | None = None,
    limit: int = Query(default=100, ge=1, le=200),
) -> list[dict[str, object]]:
    frame = _read_csv("alerts")
    if priority:
        frame = frame.loc[frame["priority"] == priority]
    if scenario:
        frame = frame.loc[frame["scenario_id"] == scenario]
    return frame.head(limit).to_dict(orient="records")


@app.get("/api/v1/cases", dependencies=[Depends(_authorize)])
def cases(limit: int = Query(default=100, ge=1, le=200)) -> list[dict[str, object]]:
    return _read_csv("cases").head(limit).to_dict(orient="records")


@app.get("/api/v1/controls", dependencies=[Depends(_authorize)])
def controls() -> dict[str, list[dict[str, object]]]:
    return {
        "data_quality": _read_csv("data_quality_controls").to_dict(orient="records"),
        "operations": _read_csv("operational_controls").to_dict(orient="records"),
    }
