"""CIRCULAR_TRANSFER must use a true rolling window, not fixed calendar buckets."""

import pandas as pd
import pytest

from aurelia_aml.scenarios import _circular_transfer

CONFIG = {"minimum_cycle_amount_try": 75_000, "window_hours": 48}
# 48-hour pandas floor buckets are anchored at the Unix epoch; this is a bucket boundary.
BOUNDARY = pd.Timestamp("2026-08-09 00:00:00")
HOUR = pd.to_timedelta(1, unit="h")


def transfers(*legs: tuple[pd.Timestamp, str, str], amount: float = 100_000.0) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "transaction_id": f"T{index}",
                "timestamp": timestamp,
                "customer_id": sender,
                "account_id": f"A{sender}",
                "direction": "OUT",
                "counterparty_id": receiver,
                "counterparty_country": "TR",
                "transaction_type": "EFT",
                "amount_try": amount,
                "cash_flag": False,
            }
            for index, (timestamp, sender, receiver) in enumerate(legs)
        ]
    )


def flagged(frame: pd.DataFrame) -> set[str]:
    return {str(hit["customer_id"]) for hit in _circular_transfer(frame, None, CONFIG, None)}


def test_boundary_is_a_real_floor_bucket_edge():
    assert BOUNDARY.floor("48h") == BOUNDARY
    assert (BOUNDARY - HOUR).floor("48h") != BOUNDARY


def test_cycle_inside_one_bucket_is_flagged():
    frame = transfers(
        (BOUNDARY + HOUR, "C1", "C2"),
        (BOUNDARY + 2 * HOUR, "C2", "C3"),
        (BOUNDARY + 3 * HOUR, "C3", "C1"),
    )
    assert flagged(frame) == {"C1", "C2", "C3"}


def test_cycle_crossing_a_bucket_boundary_is_flagged():
    # Completed within three hours, but straddles the 48h floor boundary.
    frame = transfers(
        (BOUNDARY - HOUR, "C1", "C2"),
        (BOUNDARY + HOUR, "C2", "C3"),
        (BOUNDARY + 2 * HOUR, "C3", "C1"),
    )
    assert flagged(frame) == {"C1", "C2", "C3"}


@pytest.mark.parametrize(("last_leg_hours", "expected"), [(48, {"C1", "C2", "C3"}), (49, set())])
def test_window_length_is_inclusive_and_bounded(last_leg_hours, expected):
    frame = transfers(
        (BOUNDARY - 10 * HOUR, "C1", "C2"),
        (BOUNDARY - 9 * HOUR, "C2", "C3"),
        (BOUNDARY + (last_leg_hours - 10) * HOUR, "C3", "C1"),
    )
    assert flagged(frame) == expected


def test_small_cycles_and_open_chains_are_not_flagged():
    below_minimum = transfers(
        (BOUNDARY, "C1", "C2"),
        (BOUNDARY + HOUR, "C2", "C3"),
        (BOUNDARY + 2 * HOUR, "C3", "C1"),
        amount=50_000.0,
    )
    open_chain = transfers(
        (BOUNDARY, "C1", "C2"),
        (BOUNDARY + HOUR, "C2", "C3"),
        (BOUNDARY + 2 * HOUR, "C3", "C4"),
    )
    assert flagged(below_minimum) == set()
    assert flagged(open_chain) == set()
