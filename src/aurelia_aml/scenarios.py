"""Transparent transaction-monitoring scenarios.

All thresholds are internal demonstration parameters. A rule hit is an investigative
lead, never a finding of criminal conduct or an automated reporting decision.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import networkx as nx
import pandas as pd

from .exceptions import DataQualityError


def run_scenarios(
    transactions: pd.DataFrame,
    accounts: pd.DataFrame,
    scenario_config: dict[str, Any],
    assumptions: dict[str, Any],
) -> pd.DataFrame:
    """Execute every governed monitoring scenario and return explainable hits."""
    required = {
        "transaction_id",
        "timestamp",
        "customer_id",
        "account_id",
        "direction",
        "counterparty_id",
        "counterparty_country",
        "transaction_type",
        "amount_try",
        "cash_flag",
    }
    missing = required - set(transactions.columns)
    if missing:
        raise DataQualityError(f"Transaction data missing fields: {sorted(missing)}")
    tx = transactions.copy()
    tx["timestamp"] = pd.to_datetime(tx["timestamp"])
    tx["amount_try"] = pd.to_numeric(tx["amount_try"])
    if (tx["amount_try"] <= 0).any():
        raise DataQualityError("Transaction amounts must be positive")
    scenarios = scenario_config["scenarios"]
    runners: tuple[tuple[str, Callable[..., list[dict[str, object]]]], ...] = (
        ("STRUCTURING", _structuring),
        ("RAPID_MOVEMENT", _rapid_movement),
        ("DORMANT_REACTIVATION", _dormant_reactivation),
        ("FUNNEL_MULE", _funnel_mule),
        ("CIRCULAR_TRANSFER", _circular_transfer),
        ("HIGH_RISK_GEOGRAPHY", _high_risk_geography),
    )
    hits: list[dict[str, object]] = []
    for scenario_id, runner in runners:
        hits.extend(runner(tx, accounts, scenarios[scenario_id], assumptions))
    columns = [
        "hit_id",
        "customer_id",
        "account_id",
        "scenario_id",
        "window_start",
        "window_end",
        "transaction_count",
        "amount_try",
        "evidence_value",
        "threshold_value",
        "source_transaction_ids",
        "rationale",
    ]
    frame = pd.DataFrame(hits)
    if frame.empty:
        return pd.DataFrame(columns=columns)
    frame = frame.sort_values(["scenario_id", "customer_id", "window_start"]).reset_index(drop=True)
    frame["hit_id"] = [f"H{i:06d}" for i in range(1, len(frame) + 1)]
    return frame[columns]


def _base_hit(
    customer_id: str,
    account_id: str,
    scenario_id: str,
    window: pd.DataFrame,
    evidence_value: float,
    threshold_value: float,
    rationale: str,
) -> dict[str, object]:
    ids = "|".join(window["transaction_id"].astype(str).head(20))
    return {
        "customer_id": customer_id,
        "account_id": account_id,
        "scenario_id": scenario_id,
        "window_start": window["timestamp"].min(),
        "window_end": window["timestamp"].max(),
        "transaction_count": int(len(window)),
        "amount_try": round(float(window["amount_try"].sum()), 2),
        "evidence_value": round(float(evidence_value), 4),
        "threshold_value": round(float(threshold_value), 4),
        "source_transaction_ids": ids,
        "rationale": rationale,
    }


def _best_rolling_window(
    group: pd.DataFrame,
    hours: int,
    qualifier: Callable[[pd.DataFrame], tuple[bool, float]],
) -> tuple[pd.DataFrame | None, float]:
    ordered = group.sort_values("timestamp").reset_index(drop=True)
    best: pd.DataFrame | None = None
    best_value = float("-inf")
    left = 0
    delta = pd.to_timedelta(hours, unit="h")
    for right in range(len(ordered)):
        while ordered.loc[right, "timestamp"] - ordered.loc[left, "timestamp"] > delta:
            left += 1
        window = ordered.iloc[left : right + 1]
        valid, value = qualifier(window)
        if valid and value > best_value:
            best, best_value = window.copy(), value
    return best, best_value


def _structuring(
    tx: pd.DataFrame, accounts: pd.DataFrame, cfg: dict[str, Any], assumptions: dict[str, Any]
) -> list[dict[str, object]]:
    del accounts, assumptions
    threshold = float(cfg["internal_amount_threshold_try"])
    minimum = int(cfg["minimum_transactions"])
    eligible = tx.loc[
        tx["cash_flag"]
        & (tx["direction"] == "IN")
        & (tx["amount_try"] < threshold)
        & (tx["amount_try"] >= threshold * 0.70)
    ]
    hits = []
    for customer, group in eligible.groupby("customer_id"):
        window, value = _best_rolling_window(
            group,
            int(cfg["window_hours"]),
            lambda sample: (len(sample) >= minimum, float(len(sample))),
        )
        if window is not None:
            hits.append(
                _base_hit(
                    customer,
                    str(window.iloc[0]["account_id"]),
                    "STRUCTURING",
                    window,
                    value,
                    minimum,
                    "Repeated cash inflows clustered below an internal monitoring parameter.",
                )
            )
    return hits


def _rapid_movement(
    tx: pd.DataFrame, accounts: pd.DataFrame, cfg: dict[str, Any], assumptions: dict[str, Any]
) -> list[dict[str, object]]:
    del accounts, assumptions
    hits = []
    hours = int(cfg["window_hours"])
    minimum_inflow = float(cfg["minimum_inflow_try"])
    minimum_ratio = float(cfg["outbound_ratio"])
    for customer, group in tx.groupby("customer_id"):
        ordered = group.sort_values("timestamp")
        best: tuple[float, pd.DataFrame] | None = None
        for inflow in ordered.loc[
            (ordered["direction"] == "IN") & (ordered["amount_try"] >= minimum_inflow)
        ].itertuples():
            end = inflow.timestamp + pd.to_timedelta(hours, unit="h")
            window = ordered.loc[
                (ordered["timestamp"] >= inflow.timestamp) & (ordered["timestamp"] <= end)
            ]
            outbound = float(window.loc[window["direction"] == "OUT", "amount_try"].sum())
            ratio = outbound / float(inflow.amount_try)
            if ratio >= minimum_ratio and (best is None or ratio > best[0]):
                best = (ratio, window)
        if best:
            ratio, window = best
            hits.append(
                _base_hit(
                    customer,
                    str(window.iloc[0]["account_id"]),
                    "RAPID_MOVEMENT",
                    window,
                    ratio,
                    minimum_ratio,
                    "Material incoming funds were followed by rapid outbound movement.",
                )
            )
    return hits


def _dormant_reactivation(
    tx: pd.DataFrame, accounts: pd.DataFrame, cfg: dict[str, Any], assumptions: dict[str, Any]
) -> list[dict[str, object]]:
    del assumptions
    account_status = accounts[["account_id", "dormant_flag", "dormant_since"]].copy()
    joined = tx.merge(account_status, on="account_id", how="left", validate="many_to_one")
    minimum = float(cfg["minimum_amount_try"])
    candidates = joined.loc[
        joined["dormant_flag"].fillna(False) & (joined["amount_try"] >= minimum)
    ]
    hits = []
    for customer, group in candidates.groupby("customer_id"):
        row = group.loc[group["amount_try"].idxmax()]
        window = group.loc[[row.name]]
        hits.append(
            _base_hit(
                customer,
                str(row["account_id"]),
                "DORMANT_REACTIVATION",
                window,
                float(row["amount_try"]),
                minimum,
                "A dormant-designated account recorded material new activity.",
            )
        )
    return hits


def _funnel_mule(
    tx: pd.DataFrame, accounts: pd.DataFrame, cfg: dict[str, Any], assumptions: dict[str, Any]
) -> list[dict[str, object]]:
    del accounts, assumptions
    minimum_cp = int(cfg["minimum_unique_counterparties"])
    minimum_inflow = float(cfg["minimum_inflow_try"])
    minimum_ratio = float(cfg["outbound_ratio"])
    hits = []

    def qualify(sample: pd.DataFrame) -> tuple[bool, float]:
        incoming = sample.loc[sample["direction"] == "IN"]
        outgoing = sample.loc[sample["direction"] == "OUT", "amount_try"].sum()
        inflow = incoming["amount_try"].sum()
        counterparties = incoming["counterparty_id"].nunique()
        ratio = float(outgoing / inflow) if inflow else 0.0
        valid = counterparties >= minimum_cp and inflow >= minimum_inflow and ratio >= minimum_ratio
        return valid, counterparties + ratio

    for customer, group in tx.groupby("customer_id"):
        window, evidence = _best_rolling_window(group, int(cfg["window_hours"]), qualify)
        if window is not None:
            hits.append(
                _base_hit(
                    customer,
                    str(window.iloc[0]["account_id"]),
                    "FUNNEL_MULE",
                    window,
                    evidence,
                    minimum_cp + minimum_ratio,
                    (
                        "Multiple incoming counterparties were followed by concentrated "
                        "outbound movement."
                    ),
                )
            )
    return hits


def _circular_transfer(
    tx: pd.DataFrame, accounts: pd.DataFrame, cfg: dict[str, Any], assumptions: dict[str, Any]
) -> list[dict[str, object]]:
    del accounts, assumptions
    minimum = float(cfg["minimum_cycle_amount_try"])
    internal = tx.loc[
        tx["counterparty_id"].astype(str).str.startswith("C")
        & (tx["direction"] == "OUT")
        & (tx["amount_try"] >= minimum)
    ].copy()
    internal["time_bucket"] = internal["timestamp"].dt.floor(f"{int(cfg['window_hours'])}h")
    candidates: dict[str, dict[str, object]] = {}
    for _, group in internal.groupby("time_bucket"):
        graph = nx.DiGraph()
        for row in group.itertuples():
            graph.add_edge(row.customer_id, row.counterparty_id, transaction_id=row.transaction_id)
        for cycle in nx.simple_cycles(graph, length_bound=3):
            if len(cycle) != 3:
                continue
            members = set(cycle)
            window = group.loc[
                group["customer_id"].isin(members) & group["counterparty_id"].isin(members)
            ]
            if len(window) < 3:
                continue
            for customer in members:
                existing = candidates.get(customer)
                amount = float(window["amount_try"].sum())
                if existing is None or amount > float(existing["amount_try"]):
                    candidates[customer] = _base_hit(
                        customer,
                        str(window.loc[window["customer_id"] == customer, "account_id"].iloc[0]),
                        "CIRCULAR_TRANSFER",
                        window,
                        len(members),
                        3,
                        "A short internal transfer cycle connected three synthetic customers.",
                    )
    return list(candidates.values())


def _high_risk_geography(
    tx: pd.DataFrame, accounts: pd.DataFrame, cfg: dict[str, Any], assumptions: dict[str, Any]
) -> list[dict[str, object]]:
    del accounts
    as_of = pd.Timestamp(assumptions["as_of_date"])
    high_risk = assumptions["synthetic_high_risk_jurisdiction"]
    recent = tx.loc[
        (tx["timestamp"] >= as_of - pd.to_timedelta(int(cfg["window_days"]), unit="D"))
        & (tx["counterparty_country"] == high_risk)
    ]
    minimum_total = float(cfg["minimum_total_try"])
    minimum_count = int(cfg["minimum_transactions"])
    hits = []
    for customer, group in recent.groupby("customer_id"):
        total = float(group["amount_try"].sum())
        if total >= minimum_total and len(group) >= minimum_count:
            hits.append(
                _base_hit(
                    customer,
                    str(group.iloc[0]["account_id"]),
                    "HIGH_RISK_GEOGRAPHY",
                    group,
                    total,
                    minimum_total,
                    "Material activity involved a fictitious high-risk test jurisdiction.",
                )
            )
    return hits
