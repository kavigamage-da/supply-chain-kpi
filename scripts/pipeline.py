"""
pipeline.py
-----------
Main ETL + KPI pipeline for the Supply Chain KPI Automation project.

Steps
-----
1. Load raw CSV from local disk (or S3 if USE_S3=true in .env)
2. Clean data  → remove duplicates, fill/drop nulls, parse dates
3. Calculate KPIs
4. Save cleaned CSV + KPI summary JSON
5. Upload artefacts to S3  (optional)
6. Generate charts

Usage:
    python scripts/pipeline.py
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np
from dotenv import load_dotenv

# Local imports
from s3_utils import upload_file, download_file, S3_ENABLED
from kpi_calculator import calculate_kpis
from chart_generator import generate_dashboard

# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).resolve().parent.parent
DATA_DIR     = BASE_DIR / "data"
OUTPUT_DIR   = BASE_DIR / "output"
CHARTS_DIR   = OUTPUT_DIR / "charts"
REPORTS_DIR  = OUTPUT_DIR / "reports"

for d in [DATA_DIR, CHARTS_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

RAW_CSV     = DATA_DIR / "orders_raw.csv"
CLEAN_CSV   = DATA_DIR / "orders_clean.csv"
KPI_JSON    = REPORTS_DIR / "kpi_summary.json"


# ── 1. Load ────────────────────────────────────────────────────────────────

def load_data() -> pd.DataFrame:
    """Load raw orders CSV from disk or S3."""
    if S3_ENABLED:
        log.info("Downloading raw data from S3 …")
        download_file("data/orders_raw.csv", str(RAW_CSV))

    log.info(f"Reading {RAW_CSV} …")
    df = pd.read_csv(RAW_CSV, parse_dates=["order_date"])
    log.info(f"  Loaded {len(df):,} rows, {df.shape[1]} columns")
    return df


# ── 2. Clean ───────────────────────────────────────────────────────────────

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean the raw DataFrame:
    - Drop exact duplicates
    - Parse / coerce dates
    - Fill or drop nulls
    - Validate ranges
    """
    initial_len = len(df)

    # Drop duplicates
    df = df.drop_duplicates()
    log.info(f"  Dropped {initial_len - len(df):,} duplicate rows")

    # Ensure order_date is datetime
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    bad_dates = df["order_date"].isna().sum()
    if bad_dates:
        log.warning(f"  {bad_dates} rows with unparseable dates — dropping")
        df = df.dropna(subset=["order_date"])

    # Fill missing cost with category median
    median_cost = df.groupby("product_category")["cost_lkr"].transform("median")
    null_cost   = df["cost_lkr"].isna().sum()
    df["cost_lkr"] = df["cost_lkr"].fillna(median_cost)
    log.info(f"  Imputed {null_cost:,} missing cost values with category median")

    # Convert numeric cols
    for col in ["eta_days", "actual_days", "cost_lkr"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Derived columns
    df["is_on_time"] = (
        (df["delivery_status"] == "Delivered") &
        (df["actual_days"] <= df["eta_days"])
    )
    df["delay_days"] = (df["actual_days"] - df["eta_days"]).clip(lower=0)
    df["month"]      = df["order_date"].dt.to_period("M").astype(str)
    df["week"]       = df["order_date"].dt.isocalendar().week.astype(int)

    log.info(f"  Clean dataset: {len(df):,} rows")
    return df.reset_index(drop=True)


# ── 3 & 4. Calculate + Save ────────────────────────────────────────────────

def save_artefacts(clean_df: pd.DataFrame, kpis: dict) -> None:
    """Persist cleaned CSV and KPI JSON to disk."""
    clean_df.to_csv(CLEAN_CSV, index=False)
    log.info(f"  Saved cleaned data → {CLEAN_CSV}")

    kpis["generated_at"] = datetime.utcnow().isoformat() + "Z"
    with open(KPI_JSON, "w") as f:
        json.dump(kpis, f, indent=2, default=str)
    log.info(f"  Saved KPI summary → {KPI_JSON}")


# ── 5. Upload to S3 ────────────────────────────────────────────────────────

def upload_artefacts() -> None:
    """Upload cleaned data + reports to S3."""
    if not S3_ENABLED:
        log.info("S3 not enabled — skipping upload (set USE_S3=true to enable)")
        return

    for local, s3_key in [
        (str(CLEAN_CSV),  "data/orders_clean.csv"),
        (str(KPI_JSON),   "reports/kpi_summary.json"),
    ]:
        upload_file(local, s3_key)

    # Upload charts
    for chart in CHARTS_DIR.glob("*.png"):
        upload_file(str(chart), f"charts/{chart.name}")


# ── Main ───────────────────────────────────────────────────────────────────

def run_pipeline() -> dict:
    """Execute the full ETL + KPI pipeline. Returns KPI dict."""
    log.info("=" * 60)
    log.info("  Supply Chain KPI Pipeline — starting")
    log.info("=" * 60)

    df_raw   = load_data()
    df_clean = clean_data(df_raw)

    log.info("Calculating KPIs …")
    kpis = calculate_kpis(df_clean)

    # Pretty-print top-level KPIs
    log.info("  Overall KPIs:")
    log.info(f"    On-time delivery rate : {kpis['overall']['on_time_rate_pct']:.1f} %")
    log.info(f"    Average delay         : {kpis['overall']['avg_delay_days']:.2f} days")
    log.info(f"    Total orders          : {kpis['overall']['total_orders']:,}")
    log.info(f"    Cancelled orders      : {kpis['overall']['cancelled_orders']:,}")
    log.info(f"    Avg cost per order    : LKR {kpis['overall']['avg_cost_per_order']:,.0f}")

    save_artefacts(df_clean, kpis)

    log.info("Generating dashboard charts …")
    generate_dashboard(df_clean, kpis, str(CHARTS_DIR))

    upload_artefacts()

    log.info("Pipeline complete ✓")
    log.info("=" * 60)
    return kpis


if __name__ == "__main__":
    run_pipeline()
