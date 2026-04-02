"""
generate_data.py
----------------
Generates 12 months of synthetic supply chain order data for the
Sysco LABS KPI Automation project.

Usage:
    python scripts/generate_data.py
"""

import os
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


WAREHOUSES = ["Colombo-Central", "Kandy-Hub", "Galle-South", "Jaffna-North", "Kurunegala-West"]
REGIONS = ["Western", "Central", "Southern", "Northern", "North-Western"]
CATEGORIES = ["Dairy", "Produce", "Frozen", "Dry Goods", "Beverages", "Meat & Seafood"]
STATUSES = ["Delivered", "Delayed", "In Transit", "Cancelled"]

STATUS_WEIGHTS = [0.70, 0.15, 0.10, 0.05]

# Cost per order by category (LKR)
COST_RANGES = {
    "Dairy":        (2500,  6000),
    "Produce":      (1500,  4000),
    "Frozen":       (5000, 12000),
    "Dry Goods":    (1000,  3500),
    "Beverages":    (2000,  5500),
    "Meat & Seafood": (8000, 20000),
}


def generate_orders(n_records: int = 5000, seed: int = 42) -> pd.DataFrame:
    """
    Generate synthetic supply chain order records.

    Args:
        n_records: Number of order rows to generate.
        seed: Random seed for reproducibility.

    Returns:
        DataFrame with order data.
    """
    rng = np.random.default_rng(seed)
    random.seed(seed)

    start_date = datetime(2024, 1, 1)
    end_date   = datetime(2024, 12, 31)
    date_range = (end_date - start_date).days

    order_dates = [start_date + timedelta(days=int(d)) for d in rng.integers(0, date_range, n_records)]

    warehouses = rng.choice(WAREHOUSES, n_records)
    regions    = [REGIONS[WAREHOUSES.index(w)] for w in warehouses]
    categories = rng.choice(CATEGORIES, n_records)
    statuses   = rng.choice(STATUSES,   n_records, p=STATUS_WEIGHTS)

    # ETA days: 1–5 days based on region distance
    eta_days = rng.integers(1, 6, n_records)

    # Actual days: on-time if Delivered, delayed if Delayed
    actual_days = []
    for status, eta in zip(statuses, eta_days):
        if status == "Delivered":
            actual_days.append(eta)
        elif status == "Delayed":
            actual_days.append(eta + rng.integers(1, 5))
        elif status == "In Transit":
            actual_days.append(None)       # not yet delivered
        else:                              # Cancelled
            actual_days.append(None)

    # Cost per order
    costs = [
        round(rng.uniform(*COST_RANGES[cat]), 2)
        for cat in categories
    ]

    # Inject ~3 % noise: nulls and duplicates for cleaning exercise
    n_nulls = int(n_records * 0.03)
    null_idx = rng.choice(n_records, n_nulls, replace=False)
    costs_noisy = list(costs)
    for i in null_idx:
        costs_noisy[i] = None

    df = pd.DataFrame({
        "order_id":        [f"ORD-{100000 + i}" for i in range(n_records)],
        "order_date":      order_dates,
        "warehouse":       warehouses,
        "region":          regions,
        "product_category": categories,
        "delivery_status": statuses,
        "eta_days":        eta_days,
        "actual_days":     actual_days,
        "cost_lkr":        costs_noisy,
    })

    # Add ~50 duplicate rows
    dup_rows = df.sample(50, random_state=seed)
    df = pd.concat([df, dup_rows], ignore_index=True).sample(frac=1, random_state=seed).reset_index(drop=True)

    return df


def main():
    os.makedirs("data", exist_ok=True)
    print("Generating supply chain dataset …")
    df = generate_orders()
    out_path = "data/orders_raw.csv"
    df.to_csv(out_path, index=False)
    print(f"  ✓ Saved {len(df):,} rows → {out_path}")
    print(f"  Columns : {list(df.columns)}")
    print(f"  Date range: {df['order_date'].min().date()} → {df['order_date'].max().date()}")


if __name__ == "__main__":
    main()
