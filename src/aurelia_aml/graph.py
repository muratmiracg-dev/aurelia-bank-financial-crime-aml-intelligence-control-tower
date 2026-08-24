"""Customer-counterparty graph analytics using NetworkX."""

from __future__ import annotations

import networkx as nx
import numpy as np
import pandas as pd


GRAPH_FEATURE_COLUMNS = [
    "customer_id",
    "in_degree",
    "out_degree",
    "total_degree",
    "pagerank",
    "component_size",
    "short_cycle_member",
]


def build_graph_features(transactions: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    """Calculate interpretable graph features without making guilt inferences."""
    internal = transactions.loc[
        transactions["counterparty_id"].astype(str).str.startswith("C")
        & (transactions["customer_id"] != transactions["counterparty_id"])
    ].copy()
    graph = nx.DiGraph()
    graph.add_nodes_from(customers["customer_id"])
    edge_summary = internal.groupby(["customer_id", "counterparty_id"], as_index=False).agg(
        transaction_count=("transaction_id", "count"), amount_try=("amount_try", "sum")
    )
    for row in edge_summary.itertuples():
        graph.add_edge(
            row.customer_id,
            row.counterparty_id,
            transaction_count=int(row.transaction_count),
            amount_try=float(row.amount_try),
        )
    pagerank = nx.pagerank(graph, weight="amount_try") if graph.number_of_edges() else {}
    undirected = graph.to_undirected()
    component_size: dict[str, int] = {}
    for component in nx.connected_components(undirected):
        size = len(component)
        component_size.update(dict.fromkeys(component, size))
    cycle_members = _cycle_members(internal)
    rows = []
    for customer in customers["customer_id"]:
        outbound = graph.out_degree(customer)
        inbound = graph.in_degree(customer)
        rows.append(
            {
                "customer_id": customer,
                "in_degree": int(inbound),
                "out_degree": int(outbound),
                "total_degree": int(inbound + outbound),
                "pagerank": float(pagerank.get(customer, 0.0)),
                "component_size": int(component_size.get(customer, 1)),
                "short_cycle_member": customer in cycle_members,
            }
        )
    frame = pd.DataFrame(rows, columns=GRAPH_FEATURE_COLUMNS)
    frame["degree_percentile"] = frame["total_degree"].rank(pct=True) * 100
    frame["pagerank_percentile"] = frame["pagerank"].rank(pct=True) * 100
    frame["component_percentile"] = frame["component_size"].rank(pct=True) * 100
    frame["graph_risk_score"] = (
        frame["degree_percentile"] * 0.35
        + frame["pagerank_percentile"] * 0.35
        + frame["component_percentile"] * 0.10
        + frame["short_cycle_member"].astype(int) * 20
    ).clip(0, 100)
    frame["graph_risk_score"] = frame["graph_risk_score"].round(2)
    return frame


def _cycle_members(internal: pd.DataFrame) -> set[str]:
    if internal.empty:
        return set()
    high_value = internal.loc[internal["amount_try"] >= 75_000].copy()
    high_value["time_bucket"] = pd.to_datetime(high_value["timestamp"]).dt.floor("48h")
    members: set[str] = set()
    for _, group in high_value.groupby("time_bucket"):
        graph = nx.DiGraph()
        graph.add_edges_from(zip(group["customer_id"], group["counterparty_id"], strict=False))
        for cycle in nx.simple_cycles(graph, length_bound=4):
            if 2 < len(cycle) <= 4:
                members.update(cycle)
            if len(members) >= 250:
                break
    return members


def graph_summary(features: pd.DataFrame) -> dict[str, float | int]:
    """Return compact management-level graph indicators."""
    if features.empty:
        return {
            "customers_in_short_cycles": 0,
            "maximum_component_size": 0,
            "p95_graph_risk_score": 0.0,
        }
    return {
        "customers_in_short_cycles": int(features["short_cycle_member"].sum()),
        "maximum_component_size": int(features["component_size"].max()),
        "p95_graph_risk_score": round(float(np.percentile(features["graph_risk_score"], 95)), 2),
    }
