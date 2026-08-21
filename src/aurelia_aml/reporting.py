"""Reproducible management figures for AML governance."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

NAVY = "#0B1F33"
TEAL = "#0E7490"
CYAN = "#32B7C7"
AMBER = "#D97706"
RED = "#C2413B"
GREEN = "#15803D"
SLATE = "#64748B"


def create_figures(results: dict[str, pd.DataFrame], output_dir: str | Path) -> list[Path]:
    """Create the governed analytical visual set."""
    _style()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    return [
        _executive_overview(results, output / "executive-overview.png"),
        _alert_trend(results["alerts"], output / "alert-trend.png"),
        _scenario_performance(results["performance"], output / "scenario-performance.png"),
        _case_workload(results["cases"], output / "case-workload.png"),
        _network_anomaly(results["alerts"], output / "network-anomaly.png"),
        _kyc_distribution(results["kyc_risk"], output / "kyc-risk-distribution.png"),
    ]


def _style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#CBD5E1",
            "axes.labelcolor": NAVY,
            "axes.titlecolor": NAVY,
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "grid.color": "#E2E8F0",
            "grid.linewidth": 0.7,
            "xtick.color": "#475569",
            "ytick.color": "#475569",
        }
    )


def _executive_overview(results: dict[str, pd.DataFrame], path: Path) -> Path:
    alerts = results["alerts"]
    cases = results["cases"]
    performance = results["performance"].loc[results["performance"]["scenario_id"] != "OVERALL"]
    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    priority = alerts["priority"].value_counts().reindex(["HIGH", "MEDIUM", "LOW"], fill_value=0)
    axes[0, 0].bar(priority.index, priority.values, color=[RED, AMBER, TEAL])
    axes[0, 0].set_title("Alert volume by triage priority")
    axes[0, 0].set_ylabel("Alerts")

    scenario = alerts["scenario_id"].value_counts().sort_values()
    axes[0, 1].barh(scenario.index.str.replace("_", " ").str.title(), scenario.values, color=TEAL)
    axes[0, 1].set_title("Rule hits by scenario")
    axes[0, 1].set_xlabel("Alerts")

    x = np.arange(len(performance))
    axes[1, 0].bar(x - 0.18, performance["precision"] * 100, 0.36, label="Precision", color=CYAN)
    axes[1, 0].bar(x + 0.18, performance["recall"] * 100, 0.36, label="Recall", color=GREEN)
    axes[1, 0].set_xticks(x, performance["scenario_id"].str.replace("_", " "), rotation=25)
    axes[1, 0].set_ylim(0, 105)
    axes[1, 0].set_title("Synthetic holdout retrieval")
    axes[1, 0].set_ylabel("Percent")
    axes[1, 0].legend(frameon=False)

    status = (
        cases["case_status"].value_counts().reindex(["OPEN", "IN_REVIEW", "CLOSED"], fill_value=0)
    )
    axes[1, 1].bar(status.index, status.values, color=[RED, AMBER, GREEN])
    axes[1, 1].set_title("Human-review case inventory")
    axes[1, 1].set_ylabel("Cases")
    for axis in axes.flat:
        axis.grid(axis="y")
    fig.suptitle(
        "Aurelia Bank Financial Crime & AML Intelligence Control Tower",
        fontsize=18,
        fontweight="bold",
        color=NAVY,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def _alert_trend(alerts: pd.DataFrame, path: Path) -> Path:
    frame = alerts.assign(week=pd.to_datetime(alerts["window_end"]).dt.to_period("W").dt.start_time)
    pivot = frame.pivot_table(
        index="week", columns="priority", values="alert_id", aggfunc="count", fill_value=0
    ).sort_index()
    fig, ax = plt.subplots(figsize=(11, 5.5))
    for priority, color in (("HIGH", RED), ("MEDIUM", AMBER), ("LOW", TEAL)):
        values = pivot.get(priority, pd.Series(0, index=pivot.index))
        ax.plot(pivot.index, values, marker="o", label=priority.title(), color=color)
    ax.set_title("Weekly alert creation trend")
    ax.set_ylabel("Alerts")
    ax.grid(axis="y")
    ax.legend(frameon=False, ncol=3)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def _scenario_performance(performance: pd.DataFrame, path: Path) -> Path:
    frame = performance.loc[performance["scenario_id"] != "OVERALL"].copy()
    frame["label"] = frame["scenario_id"].str.replace("_", " ").str.title()
    fig, ax = plt.subplots(figsize=(10.5, 5.7))
    sizes = np.maximum(frame["true_positives"] * 35, 100)
    ax.scatter(frame["precision"] * 100, frame["recall"] * 100, s=sizes, color=TEAL, alpha=0.8)
    for row in frame.itertuples():
        ax.annotate(
            row.label,
            (row.precision * 100, row.recall * 100),
            xytext=(5, 5),
            textcoords="offset points",
        )
    ax.set_xlim(0, max(100, float(frame["precision"].max() * 110)))
    ax.set_ylim(0, 105)
    ax.set_xlabel("Precision (%)")
    ax.set_ylabel("Recall (%)")
    ax.set_title("Scenario retrieval trade-off on isolated synthetic truth")
    ax.grid()
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def _case_workload(cases: pd.DataFrame, path: Path) -> Path:
    pivot = cases.pivot_table(
        index="assigned_queue",
        columns="case_status",
        values="case_id",
        aggfunc="count",
        fill_value=0,
    )
    fig, ax = plt.subplots(figsize=(10.5, 5.5))
    bottom = np.zeros(len(pivot))
    for status, color in (("OPEN", RED), ("IN_REVIEW", AMBER), ("CLOSED", GREEN)):
        values = pivot.get(status, pd.Series(0, index=pivot.index)).to_numpy()
        ax.bar(
            pivot.index, values, bottom=bottom, label=status.replace("_", " ").title(), color=color
        )
        bottom += values
    ax.set_title("Case workload by analyst queue")
    ax.set_ylabel("Cases")
    ax.grid(axis="y")
    ax.legend(frameon=False, ncol=3)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def _network_anomaly(alerts: pd.DataFrame, path: Path) -> Path:
    colors = alerts["priority"].map({"HIGH": RED, "MEDIUM": AMBER, "LOW": TEAL})
    fig, ax = plt.subplots(figsize=(9.5, 5.5))
    ax.scatter(
        alerts["graph_risk_score"],
        alerts["anomaly_score"],
        s=np.maximum(alerts["alert_score"], 20),
        c=colors,
        alpha=0.55,
        edgecolors="white",
    )
    ax.set_xlabel("Graph risk score")
    ax.set_ylabel("Behavioural anomaly score")
    ax.set_title("Independent signals used for alert prioritisation")
    ax.grid()
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def _kyc_distribution(kyc: pd.DataFrame, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(9.5, 5.4))
    ax.hist(kyc["kyc_risk_score"], bins=20, color=TEAL, edgecolor="white")
    ax.axvline(28, color=AMBER, linestyle="--", label="Medium floor")
    ax.axvline(45, color=RED, linestyle="--", label="High floor")
    ax.set_title("KYC inherent-risk score distribution")
    ax.set_xlabel("Risk score")
    ax.set_ylabel("Customers")
    ax.grid(axis="y")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path
