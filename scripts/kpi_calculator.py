"""
kpi_calculator.py
-----------------
Pure-function KPI calculations for the supply chain pipeline.
All functions accept a clean DataFrame and return serialisable dicts.
"""

import pandas as pd
import numpy as np


def _safe_pct(numerator: float, denominator: float) -> float:
    """Return percentage, guarding against zero division."""
    return round((numerator / denominator) * 100, 2) if denominator else 0.0


def overall_kpis(df: pd.DataFrame) -> dict:
    """Compute fleet-wide summary KPIs."""
    delivered  = df[df["delivery_status"] == "Delivered"]
    on_time    = df["is_on_time"].sum()
    total      = len(df)
    cancelled  = (df["delivery_status"] == "Cancelled").sum()
    delayed    = (df["delivery_status"] == "Delayed").sum()

    return {
        "total_orders":         int(total),
        "delivered_orders":     int(len(delivered)),
        "on_time_orders":       int(on_time),
        "delayed_orders":       int(delayed),
        "cancelled_orders":     int(cancelled),
        "on_time_rate_pct":     _safe_pct(on_time, total),
        "cancellation_rate_pct": _safe_pct(cancelled, total),
        "avg_delay_days":       round(float(df["delay_days"].mean()), 3),
        "avg_cost_per_order":   round(float(df["cost_lkr"].mean()), 2),
        "total_revenue_lkr":    round(float(df["cost_lkr"].sum()), 2),
    }


def warehouse_kpis(df: pd.DataFrame) -> list[dict]:
    """
    KPIs aggregated per warehouse:
    - on_time_rate_pct
    - avg_delay_days
    - total_orders
    - avg_cost_per_order
    """
    records = []
    for wh, grp in df.groupby("warehouse"):
        on_time = grp["is_on_time"].sum()
        records.append({
            "warehouse":          wh,
            "total_orders":       int(len(grp)),
            "on_time_rate_pct":   _safe_pct(on_time, len(grp)),
            "avg_delay_days":     round(float(grp["delay_days"].mean()), 3),
            "avg_cost_per_order": round(float(grp["cost_lkr"].mean()), 2),
            "cancelled_orders":   int((grp["delivery_status"] == "Cancelled").sum()),
        })
    return sorted(records, key=lambda r: r["on_time_rate_pct"], reverse=True)


def monthly_trend(df: pd.DataFrame) -> list[dict]:
    """Month-over-month on-time rate and order volume."""
    monthly = (
        df.groupby("month")
        .agg(
            total_orders=("order_id", "count"),
            on_time_orders=("is_on_time", "sum"),
            avg_cost=("cost_lkr", "mean"),
            avg_delay=("delay_days", "mean"),
        )
        .reset_index()
    )
    monthly["on_time_rate_pct"] = (monthly["on_time_orders"] / monthly["total_orders"] * 100).round(2)
    monthly["avg_cost"]         = monthly["avg_cost"].round(2)
    monthly["avg_delay"]        = monthly["avg_delay"].round(3)
    return monthly.to_dict(orient="records")


def category_kpis(df: pd.DataFrame) -> list[dict]:
    """Cost and on-time performance by product category."""
    records = []
    for cat, grp in df.groupby("product_category"):
        on_time = grp["is_on_time"].sum()
        records.append({
            "category":           cat,
            "total_orders":       int(len(grp)),
            "on_time_rate_pct":   _safe_pct(on_time, len(grp)),
            "avg_cost_per_order": round(float(grp["cost_lkr"].mean()), 2),
            "total_revenue_lkr":  round(float(grp["cost_lkr"].sum()), 2),
        })
    return sorted(records, key=lambda r: r["total_revenue_lkr"], reverse=True)


def regional_kpis(df: pd.DataFrame) -> list[dict]:
    """On-time rate and cost by region."""
    records = []
    for region, grp in df.groupby("region"):
        on_time = grp["is_on_time"].sum()
        records.append({
            "region":             region,
            "total_orders":       int(len(grp)),
            "on_time_rate_pct":   _safe_pct(on_time, len(grp)),
            "avg_cost_per_order": round(float(grp["cost_lkr"].mean()), 2),
        })
    return sorted(records, key=lambda r: r["on_time_rate_pct"], reverse=True)


def calculate_kpis(df: pd.DataFrame) -> dict:
    """
    Master KPI function.  Returns a single dict with all KPI sections,
    ready for JSON serialisation.
    """
    return {
        "overall":   overall_kpis(df),
        "warehouse": warehouse_kpis(df),
        "monthly":   monthly_trend(df),
        "category":  category_kpis(df),
        "regional":  regional_kpis(df),
    }
