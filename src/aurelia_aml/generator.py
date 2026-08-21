"""Deterministic synthetic AML data with isolated validation truth.

The generator creates no real people, sanctions records or bank transactions. Pattern
labels are written to a separate validation-only table and are never consumed by the
detection engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class _InjectionState:
    next_transaction: int
    next_case: int = 1


def _offset(*, days: int = 0, hours: int = 0) -> pd.Timedelta:
    return pd.to_timedelta(days, unit="D") + pd.to_timedelta(hours, unit="h")


def build_demo_data(config: dict[str, Any], seed: int = 20260821) -> dict[str, pd.DataFrame]:
    """Build the complete, reproducible synthetic data layer."""
    rng = np.random.default_rng(seed)
    assumptions = config["assumptions"]
    population = assumptions["synthetic_population"]
    as_of = pd.Timestamp(assumptions["as_of_date"])
    customers = _build_customers(int(population["customers"]), as_of, rng)
    accounts = _build_accounts(customers, int(population["accounts"]), as_of, rng)
    transactions = _build_baseline_transactions(
        customers,
        accounts,
        int(population["baseline_transactions"]),
        int(assumptions["observation_days"]),
        as_of,
        rng,
    )
    transactions, accounts, truth = _inject_typologies(
        transactions, customers, accounts, as_of, rng
    )
    relationships = _build_relationships(customers, accounts, rng)
    return {
        "customers": customers,
        "accounts": accounts,
        "transactions": transactions.sort_values(["timestamp", "transaction_id"]).reset_index(
            drop=True
        ),
        "relationships": relationships,
        "typology_truth": truth.sort_values(["scenario_id", "case_id", "customer_id"]).reset_index(
            drop=True
        ),
    }


def _build_customers(count: int, as_of: pd.Timestamp, rng: np.random.Generator) -> pd.DataFrame:
    customer_ids = np.array([f"C{i:06d}" for i in range(1, count + 1)])
    customer_type = rng.choice(["INDIVIDUAL", "CORPORATE"], count, p=[0.78, 0.22])
    segment = np.where(
        customer_type == "CORPORATE",
        rng.choice(["SME", "COMMERCIAL", "CORPORATE"], count, p=[0.58, 0.30, 0.12]),
        rng.choice(["MASS", "AFFLUENT", "PRIVATE"], count, p=[0.72, 0.23, 0.05]),
    )
    countries = rng.choice(
        ["TR", "DE", "GB", "US", "AE", "GE", "RS", "XH"],
        count,
        p=[0.82, 0.035, 0.03, 0.025, 0.035, 0.025, 0.025, 0.005],
    )
    expected_turnover = np.clip(rng.lognormal(11.2, 1.15, count), 8_000, 8_000_000)
    expected_count = np.clip(rng.poisson(24, count) + 4, 5, 150)
    onboard_days = rng.integers(60, 3650, count)
    review_offset = rng.integers(-420, 420, count)
    beneficial_owner_complete = np.where(
        customer_type == "INDIVIDUAL", True, rng.random(count) > 0.09
    )
    frame = pd.DataFrame(
        {
            "customer_id": customer_ids,
            "customer_label": [f"Synthetic Customer {i:06d}" for i in range(1, count + 1)],
            "customer_type": customer_type,
            "segment": segment,
            "residence_country": countries,
            "onboarding_channel": rng.choice(
                ["BRANCH", "DIGITAL", "RELATIONSHIP_MANAGER"], count, p=[0.42, 0.46, 0.12]
            ),
            "onboarding_date": as_of - pd.to_timedelta(onboard_days, unit="D"),
            "pep_flag": rng.random(count) < 0.018,
            "synthetic_watchlist_match": rng.random(count) < 0.004,
            "occupation_risk": rng.choice(["LOW", "MEDIUM", "HIGH"], count, p=[0.67, 0.27, 0.06]),
            "expected_monthly_turnover_try": expected_turnover.round(2),
            "expected_tx_count_30d": expected_count,
            "kyc_review_due_date": as_of + pd.to_timedelta(review_offset, unit="D"),
            "beneficial_owner_complete": beneficial_owner_complete,
            "source_of_funds_verified": rng.random(count) > 0.055,
            "data_class": "CONTROLLED_SYNTHETIC",
        }
    )
    return frame


def _build_accounts(
    customers: pd.DataFrame, count: int, as_of: pd.Timestamp, rng: np.random.Generator
) -> pd.DataFrame:
    customer_ids = customers["customer_id"].to_numpy()
    owners = np.concatenate(
        [customer_ids, rng.choice(customer_ids, size=count - len(customer_ids), replace=True)]
    )
    rng.shuffle(owners)
    dormant = rng.random(count) < 0.055
    dormant_days = rng.integers(185, 900, count)
    return pd.DataFrame(
        {
            "account_id": [f"A{i:07d}" for i in range(1, count + 1)],
            "customer_id": owners,
            "account_type": rng.choice(
                ["CURRENT", "SAVINGS", "PAYMENT", "BUSINESS"],
                count,
                p=[0.42, 0.25, 0.20, 0.13],
            ),
            "currency": rng.choice(["TRY", "USD", "EUR"], count, p=[0.84, 0.10, 0.06]),
            "opened_date": as_of - pd.to_timedelta(rng.integers(190, 4300, count), unit="D"),
            "status": "OPEN",
            "dormant_flag": dormant,
            "dormant_since": pd.Series(
                np.where(dormant, as_of - pd.to_timedelta(dormant_days, unit="D"), pd.NaT)
            ),
            "data_class": "CONTROLLED_SYNTHETIC",
        }
    )


def _build_baseline_transactions(
    customers: pd.DataFrame,
    accounts: pd.DataFrame,
    count: int,
    observation_days: int,
    as_of: pd.Timestamp,
    rng: np.random.Generator,
) -> pd.DataFrame:
    active = accounts.loc[~accounts["dormant_flag"]].reset_index(drop=True)
    chosen = rng.integers(0, len(active), count)
    account_ids = active.loc[chosen, "account_id"].to_numpy()
    customer_ids = active.loc[chosen, "customer_id"].to_numpy()
    customer_index = customers.set_index("customer_id")
    expected = customer_index.loc[customer_ids, "expected_monthly_turnover_try"].to_numpy()
    expected_count = customer_index.loc[customer_ids, "expected_tx_count_30d"].to_numpy()
    baseline = expected / np.maximum(expected_count, 1)
    amounts = np.clip(baseline * rng.lognormal(0.0, 0.85, count), 25, 2_500_000)
    internal = rng.random(count) < 0.57
    cp_customer = rng.choice(customers["customer_id"].to_numpy(), count)
    self_mask = cp_customer == customer_ids
    cp_customer[self_mask] = np.roll(cp_customer[self_mask], 1)
    external_ids = np.array([f"EXT{value:06d}" for value in rng.integers(1, 9000, count)])
    counterparties = np.where(internal, cp_customer, external_ids)
    txn_type = rng.choice(
        ["WIRE_TRANSFER", "INSTANT_PAYMENT", "CARD_PAYMENT", "CASH_DEPOSIT", "CASH_WITHDRAWAL"],
        count,
        p=[0.38, 0.26, 0.20, 0.09, 0.07],
    )
    seconds = rng.integers(0, observation_days * 24 * 3600, count)
    return pd.DataFrame(
        {
            "transaction_id": [f"T{i:09d}" for i in range(1, count + 1)],
            "timestamp": as_of - pd.to_timedelta(seconds, unit="s"),
            "customer_id": customer_ids,
            "account_id": account_ids,
            "direction": rng.choice(["IN", "OUT"], count, p=[0.49, 0.51]),
            "counterparty_id": counterparties,
            "counterparty_country": rng.choice(
                ["TR", "DE", "GB", "US", "AE", "GE", "RS", "XH"],
                count,
                p=[0.80, 0.04, 0.035, 0.03, 0.04, 0.025, 0.025, 0.005],
            ),
            "channel": rng.choice(
                ["MOBILE", "INTERNET", "BRANCH", "ATM", "API"],
                count,
                p=[0.37, 0.27, 0.12, 0.16, 0.08],
            ),
            "transaction_type": txn_type,
            "amount_try": amounts.round(2),
            "currency": rng.choice(["TRY", "USD", "EUR"], count, p=[0.86, 0.09, 0.05]),
            "cash_flag": np.isin(txn_type, ["CASH_DEPOSIT", "CASH_WITHDRAWAL"]),
            "device_id": [f"D{value:06d}" for value in rng.integers(1, 2400, count)],
            "data_class": "CONTROLLED_SYNTHETIC",
        }
    )


def _inject_typologies(
    transactions: pd.DataFrame,
    customers: pd.DataFrame,
    accounts: pd.DataFrame,
    as_of: pd.Timestamp,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    pool = customers["customer_id"].to_numpy().copy()
    rng.shuffle(pool)
    groups = {
        "STRUCTURING": pool[0:15],
        "RAPID_MOVEMENT": pool[15:30],
        "DORMANT_REACTIVATION": pool[30:42],
        "FUNNEL_MULE": pool[42:54],
        "CIRCULAR_TRANSFER": pool[54:78],
        "HIGH_RISK_GEOGRAPHY": pool[78:92],
    }
    account_map = accounts.groupby("customer_id", sort=False)["account_id"].first().to_dict()
    dormant_subjects = set(groups["DORMANT_REACTIVATION"])
    dormant_account_ids = {account_map[customer] for customer in dormant_subjects}
    accounts = accounts.copy()
    mask = accounts["account_id"].isin(dormant_account_ids)
    accounts.loc[mask, "dormant_flag"] = True
    accounts.loc[mask, "dormant_since"] = as_of - _offset(days=420)

    rows: list[dict[str, object]] = []
    truth: list[dict[str, object]] = []
    state = _InjectionState(next_transaction=len(transactions) + 1)

    def add_tx(
        customer: str,
        when: pd.Timestamp,
        direction: str,
        counterparty: str,
        amount: float,
        txn_type: str = "WIRE_TRANSFER",
        country: str = "TR",
        account: str | None = None,
    ) -> None:
        rows.append(
            {
                "transaction_id": f"T{state.next_transaction:09d}",
                "timestamp": when,
                "customer_id": customer,
                "account_id": account or account_map[customer],
                "direction": direction,
                "counterparty_id": counterparty,
                "counterparty_country": country,
                "channel": "BRANCH" if "CASH" in txn_type else "INTERNET",
                "transaction_type": txn_type,
                "amount_try": round(float(amount), 2),
                "currency": "TRY",
                "cash_flag": "CASH" in txn_type,
                "device_id": f"D-INJECT-{customer}",
                "data_class": "CONTROLLED_SYNTHETIC",
            }
        )
        state.next_transaction += 1

    def add_truth(
        scenario: str, subjects: list[str], start: pd.Timestamp, end: pd.Timestamp
    ) -> None:
        case_id = f"VC{state.next_case:04d}"
        for subject in subjects:
            truth.append(
                {
                    "case_id": case_id,
                    "scenario_id": scenario,
                    "customer_id": subject,
                    "injection_start": start,
                    "injection_end": end,
                    "validation_only": True,
                    "data_class": "SYNTHETIC_VALIDATION_TRUTH",
                }
            )
        state.next_case += 1

    for customer in groups["STRUCTURING"]:
        start = as_of - _offset(days=int(rng.integers(4, 75)), hours=18)
        for index in range(6):
            add_tx(
                customer,
                start + _offset(hours=index * 5),
                "IN",
                f"EXT-STRUCT-{customer}-{index}",
                rng.uniform(43_500, 49_500),
                "CASH_DEPOSIT",
            )
        add_truth("STRUCTURING", [customer], start, start + _offset(hours=25))

    for customer in groups["RAPID_MOVEMENT"]:
        start = as_of - _offset(days=int(rng.integers(3, 70)), hours=10)
        inflow = float(rng.uniform(180_000, 650_000))
        add_tx(customer, start, "IN", f"EXT-RAPID-IN-{customer}", inflow)
        add_tx(
            customer,
            start + _offset(hours=5),
            "OUT",
            f"EXT-RAPID-OUT-{customer}",
            inflow * rng.uniform(0.83, 0.94),
        )
        add_truth("RAPID_MOVEMENT", [customer], start, start + _offset(hours=5))

    for customer in groups["DORMANT_REACTIVATION"]:
        start = as_of - _offset(days=int(rng.integers(1, 35)), hours=7)
        account = account_map[customer]
        add_tx(
            customer,
            start,
            "IN",
            f"EXT-DORMANT-{customer}",
            rng.uniform(140_000, 480_000),
            account=account,
        )
        add_truth("DORMANT_REACTIVATION", [customer], start, start)

    for customer in groups["FUNNEL_MULE"]:
        start = as_of - _offset(days=int(rng.integers(2, 60)), hours=16)
        inflows: list[float] = []
        for index in range(7):
            amount = float(rng.uniform(35_000, 70_000))
            inflows.append(amount)
            add_tx(
                customer,
                start + _offset(hours=index * 2),
                "IN",
                f"EXT-FUNNEL-{customer}-{index}",
                amount,
            )
        add_tx(
            customer,
            start + _offset(hours=18),
            "OUT",
            f"EXT-FUNNEL-OUT-{customer}",
            sum(inflows) * 0.84,
        )
        add_truth("FUNNEL_MULE", [customer], start, start + _offset(hours=18))

    cycle_subjects = list(groups["CIRCULAR_TRANSFER"])
    for group_start in range(0, len(cycle_subjects), 3):
        trio = cycle_subjects[group_start : group_start + 3]
        start = as_of - _offset(days=int(rng.integers(2, 55)), hours=12)
        amount = float(rng.uniform(110_000, 320_000))
        for index, customer in enumerate(trio):
            add_tx(
                customer,
                start + _offset(hours=index * 4),
                "OUT",
                trio[(index + 1) % 3],
                amount * (1 - index * 0.015),
            )
        add_truth("CIRCULAR_TRANSFER", trio, start, start + _offset(hours=8))

    for customer in groups["HIGH_RISK_GEOGRAPHY"]:
        start = as_of - _offset(days=int(rng.integers(2, 28)), hours=9)
        for index in range(3):
            add_tx(
                customer,
                start + _offset(days=index * 3),
                "OUT" if index % 2 else "IN",
                f"EXT-XH-{customer}-{index}",
                rng.uniform(65_000, 145_000),
                country="XH",
            )
        add_truth("HIGH_RISK_GEOGRAPHY", [customer], start, start + _offset(days=6))

    # Unlabelled lookalike activity deliberately creates realistic false-positive pressure.
    # The detection layer has no access to this generator context.
    lookalikes = {
        "STRUCTURING": pool[92:100],
        "RAPID_MOVEMENT": pool[100:108],
        "FUNNEL_MULE": pool[108:114],
        "CIRCULAR_TRANSFER": pool[114:120],
        "HIGH_RISK_GEOGRAPHY": pool[120:127],
    }
    for customer in lookalikes["STRUCTURING"]:
        start = as_of - _offset(days=int(rng.integers(5, 70)), hours=14)
        for index in range(5):
            add_tx(
                customer,
                start + _offset(hours=index * 6),
                "IN",
                f"EXT-LOOKALIKE-CASH-{customer}-{index}",
                rng.uniform(38_000, 49_000),
                "CASH_DEPOSIT",
            )
    for customer in lookalikes["RAPID_MOVEMENT"]:
        start = as_of - _offset(days=int(rng.integers(4, 65)), hours=11)
        inflow = float(rng.uniform(150_000, 420_000))
        add_tx(customer, start, "IN", f"EXT-LOOKALIKE-IN-{customer}", inflow)
        add_tx(
            customer,
            start + _offset(hours=8),
            "OUT",
            f"EXT-LOOKALIKE-OUT-{customer}",
            inflow * 0.84,
        )
    for customer in lookalikes["FUNNEL_MULE"]:
        start = as_of - _offset(days=int(rng.integers(3, 58)), hours=15)
        amounts = []
        for index in range(6):
            amount = float(rng.uniform(38_000, 62_000))
            amounts.append(amount)
            add_tx(
                customer,
                start + _offset(hours=index * 2),
                "IN",
                f"EXT-LOOKALIKE-FUNNEL-{customer}-{index}",
                amount,
            )
        add_tx(
            customer,
            start + _offset(hours=16),
            "OUT",
            f"EXT-LOOKALIKE-FUNNEL-OUT-{customer}",
            sum(amounts) * 0.78,
        )
    cycle_lookalikes = list(lookalikes["CIRCULAR_TRANSFER"])
    for group_start in range(0, len(cycle_lookalikes), 3):
        trio = cycle_lookalikes[group_start : group_start + 3]
        start = as_of - _offset(days=int(rng.integers(4, 50)), hours=12)
        amount = float(rng.uniform(90_000, 180_000))
        for index, customer in enumerate(trio):
            add_tx(
                customer,
                start + _offset(hours=index * 3),
                "OUT",
                trio[(index + 1) % 3],
                amount,
            )
    for customer in lookalikes["HIGH_RISK_GEOGRAPHY"]:
        start = as_of - _offset(days=int(rng.integers(2, 24)), hours=8)
        for index in range(2):
            add_tx(
                customer,
                start + _offset(days=index * 4),
                "OUT",
                f"EXT-LOOKALIKE-XH-{customer}-{index}",
                rng.uniform(78_000, 120_000),
                country="XH",
            )

    injected = pd.DataFrame(rows, columns=transactions.columns)
    return (
        pd.concat([transactions, injected], ignore_index=True),
        accounts,
        pd.DataFrame(truth),
    )


def _build_relationships(
    customers: pd.DataFrame, accounts: pd.DataFrame, rng: np.random.Generator
) -> pd.DataFrame:
    customer_ids = customers["customer_id"].to_numpy()
    account_rows = [
        {
            "source_id": row.customer_id,
            "target_id": row.account_id,
            "relationship_type": "OWNS_ACCOUNT",
            "evidence_source": "SYNTHETIC_CORE_BANKING",
        }
        for row in accounts.itertuples()
    ]
    shared_device_rows = []
    for index in range(36):
        members = rng.choice(customer_ids, size=int(rng.integers(2, 5)), replace=False)
        entity = f"SHARED_DEVICE_{index + 1:03d}"
        shared_device_rows.extend(
            {
                "source_id": customer,
                "target_id": entity,
                "relationship_type": "USES_DEVICE",
                "evidence_source": "SYNTHETIC_DIGITAL_TELEMETRY",
            }
            for customer in members
        )
    return pd.DataFrame(account_rows + shared_device_rows)
