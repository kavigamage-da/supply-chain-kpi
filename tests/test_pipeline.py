"""
tests/test_pipeline.py
----------------------
Unit tests for the supply chain KPI pipeline.
Run with:  pytest tests/ -v --cov=scripts
"""

import sys
import json
import pytest
import pandas as pd
import numpy as np
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from generate_data  import generate_orders
from kpi_calculator import (
    overall_kpis, warehouse_kpis, monthly_trend,
    category_kpis, calculate_kpis,
)


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def raw_df() -> pd.DataFrame:
    return generate_orders(n_records=500, seed=0)


@pytest.fixture(scope="module")
def clean_df(raw_df) -> pd.DataFrame:
    """Minimal inline clean — mirrors pipeline.py logic."""
    df = raw_df.drop_duplicates().copy()
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    df = df.dropna(subset=["order_date"])
    median_cost = df.groupby("product_category")["cost_lkr"].transform("median")
    df["cost_lkr"] = df["cost_lkr"].fillna(median_cost)
    for col in ["eta_days", "actual_days", "cost_lkr"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["is_on_time"] = (
        (df["delivery_status"] == "Delivered") &
        (df["actual_days"] <= df["eta_days"])
    )
    df["delay_days"] = (df["actual_days"] - df["eta_days"]).clip(lower=0)
    df["month"]      = df["order_date"].dt.to_period("M").astype(str)
    return df.reset_index(drop=True)


# ── Data generation tests ───────────────────────────────────────────────────

class TestDataGeneration:
    def test_row_count(self, raw_df):
        # 500 records + ~5 duplicate rows (1%)
        assert len(raw_df) >= 500

    def test_expected_columns(self, raw_df):
        expected = {"order_id","order_date","warehouse","region",
                    "product_category","delivery_status","eta_days",
                    "actual_days","cost_lkr"}
        assert expected.issubset(set(raw_df.columns))

    def test_order_ids_unique_in_base(self, raw_df):
        # Even with duplicates there should be many unique IDs
        assert raw_df["order_id"].nunique() > 400

    def test_status_values(self, raw_df):
        valid = {"Delivered", "Delayed", "In Transit", "Cancelled"}
        assert set(raw_df["delivery_status"].unique()).issubset(valid)

    def test_cost_range(self, raw_df):
        valid_costs = raw_df["cost_lkr"].dropna()
        assert valid_costs.min() >= 1000
        assert valid_costs.max() <= 25000


# ── KPI calculation tests ───────────────────────────────────────────────────

class TestOverallKPIs:
    def test_keys_present(self, clean_df):
        result = overall_kpis(clean_df)
        for key in ["total_orders","on_time_rate_pct","avg_delay_days",
                    "avg_cost_per_order","total_revenue_lkr"]:
            assert key in result

    def test_on_time_rate_range(self, clean_df):
        result = overall_kpis(clean_df)
        assert 0 <= result["on_time_rate_pct"] <= 100

    def test_total_orders_matches(self, clean_df):
        result = overall_kpis(clean_df)
        assert result["total_orders"] == len(clean_df)

    def test_no_negative_delay(self, clean_df):
        result = overall_kpis(clean_df)
        assert result["avg_delay_days"] >= 0


class TestWarehouseKPIs:
    def test_returns_list(self, clean_df):
        result = warehouse_kpis(clean_df)
        assert isinstance(result, list)

    def test_all_warehouses_present(self, clean_df):
        result  = warehouse_kpis(clean_df)
        names   = {r["warehouse"] for r in result}
        expected = set(clean_df["warehouse"].unique())
        assert names == expected

    def test_sorted_descending(self, clean_df):
        result = warehouse_kpis(clean_df)
        rates  = [r["on_time_rate_pct"] for r in result]
        assert rates == sorted(rates, reverse=True)


class TestMonthlyTrend:
    def test_returns_12_months(self, clean_df):
        result = monthly_trend(clean_df)
        # Generated data covers Jan–Dec 2024
        assert len(result) == 12

    def test_monthly_rate_range(self, clean_df):
        result = monthly_trend(clean_df)
        for row in result:
            assert 0 <= row["on_time_rate_pct"] <= 100


class TestMasterKPIs:
    def test_serialisable(self, clean_df):
        result = calculate_kpis(clean_df)
        # Should not raise
        json.dumps(result, default=str)

    def test_all_sections_present(self, clean_df):
        result = calculate_kpis(clean_df)
        for section in ["overall", "warehouse", "monthly", "category", "regional"]:
            assert section in result
