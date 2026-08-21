from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pandas as pd


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    required = [
        "artifacts/results/executive_summary.json",
        "artifacts/results/alerts.csv",
        "artifacts/results/cases.csv",
        "artifacts/results/performance.csv",
        "artifacts/results/data_quality_controls.csv",
        "artifacts/figures/executive-overview.png",
        "artifacts/aurelia_aml_demo.sqlite",
        "excel/Aurelia_Bank_AML_Investigation_Workbench.xlsx",
        "presentation/Aurelia_Bank_AML_Executive_Deck_EN.pptx",
        "report/Aurelia_Bank_AML_Executive_Report.pdf",
        "powerbi/AML_Measures.dax",
        "MANIFEST.sha256",
    ]
    missing = [path for path in required if not (root / path).exists()]
    if missing:
        raise SystemExit(f"Missing required artifacts: {missing}")

    summary = json.loads((root / required[0]).read_text(encoding="utf-8"))
    if summary["controls"]["data_quality_passed"] != summary["controls"]["data_quality_total"]:
        raise SystemExit("Not all data-quality controls passed")
    if summary["governance"]["automated_str_submission"]:
        raise SystemExit("Governance invariant violated: automated reporting is enabled")
    controls = pd.read_csv(root / "artifacts/results/data_quality_controls.csv")
    if set(controls["status"]) != {"PASS"}:
        raise SystemExit("Data-quality control file contains a failure")
    with sqlite3.connect(root / "artifacts/aurelia_aml_demo.sqlite") as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    required_tables = {
        "customers",
        "accounts",
        "typology_truth",
        "alerts",
        "cases",
        "performance",
        "data_quality_controls",
        "operational_controls",
        "investigation_packets",
    }
    if not required_tables.issubset(tables):
        raise SystemExit(f"SQLite analytical layer is incomplete: {required_tables - tables}")

    entries = (root / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines()
    for line in entries:
        expected, relative = line.split("  ", maxsplit=1)
        actual = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        if actual != expected:
            raise SystemExit(f"Checksum mismatch: {relative}")
    print(f"Verified {len(required)} required deliverables and {len(entries)} checksums.")


if __name__ == "__main__":
    main()
