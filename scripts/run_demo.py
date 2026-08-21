from pathlib import Path

from aurelia_aml.pipeline import run_pipeline

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    summary = run_pipeline(root)
    print(
        f"Pipeline complete: {summary['project']} as of {summary['as_of_date']} | "
        f"{summary['monitoring']['alerts']} alerts"
    )
