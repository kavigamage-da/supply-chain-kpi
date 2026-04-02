# Supply Chain KPI Automation
**Automating warehouse performance reporting for a food distribution network — from 3 hours of manual Excel work to a 5-second daily pipeline**

Built to simulate the analytics work done at Sysco LABS — the tech arm powering a $70B food distribution company. This project automates the full reporting cycle: raw order data → cleaned dataset → KPI calculations → executive dashboard → email delivery, running hands-free every day via GitHub Actions.

---

## The Business Problem

The warehouse operations team had a reporting problem that nobody talked about.

Every morning, an analyst pulled CSVs from 5 warehouses, cleaned them in Excel, calculated on-time delivery rates by hand, and emailed a summary to management. It took 2–3 hours. The data was already stale by the time it landed. And because the process was manual, it only happened when someone had time — meaning some weeks, management was making decisions with no data at all.

Delayed shipments weren't being caught early. Nobody knew which warehouse was underperforming until a customer escalated. Nobody knew which product categories were eating into margin.

**This project fixes that with a fully automated pipeline.**

---

## What the Data Shows — and What to Do About It

These are the actual findings from running 12 months of order data (5,000 orders, 5 warehouses, 6 product categories) through the pipeline — with the business action each finding points to.

---

### Finding 1 — Galle-South is the network's weakest link

Across all 5 warehouses, Galle-South has the lowest on-time delivery rate at **68.92%** and the highest average delay at **0.494 days** — 13% worse than Kurunegala-West which leads the network at 71.07%. Galle-South also has the most cancellations: **60 orders cancelled** in 12 months, compared to just 38 at Colombo-Central.

| Warehouse | On-Time Rate | Avg Delay | Cancellations |
|-----------|-------------|-----------|---------------|
| Kurunegala-West | 71.07% ✅ | 0.438d | 53 |
| Colombo-Central | 70.77% | 0.441d | 38 ✅ |
| Jaffna-North | 70.19% | 0.430d | 54 |
| Kandy-Hub | 69.87% | 0.451d | 51 |
| Galle-South | 68.92% ❌ | 0.494d ❌ | 60 ❌ |

**What this means for the business:** Galle-South isn't just underperforming on one metric — it's the worst on all three: on-time rate, delay, and cancellations. That combination points to a systemic operations problem, not a one-off incident. Before management spends time trying to improve the network average, the highest-return action is a targeted audit of Galle-South alone. Fix one warehouse, move the whole network number.

---

### Finding 2 — Two hidden risks in the product mix

**Risk A — Meat & Seafood:** The highest-revenue category at **LKR 11.4M** — nearly double Frozen's LKR 7M and almost 6x Dry Goods. Every order averages **LKR 14,028**, which is 2.4x the network average of LKR 5,887. A delayed Meat & Seafood order isn't just a logistics failure — at that order value, it's a spoilage event, a customer loss, and a margin hit simultaneously.

**Risk B — Dairy:** The worst on-time rate of any category at **68.49%**, below the 70.14% network average, across 860 orders — the second highest volume category. Dairy is time-sensitive and perishable. High volume plus poor on-time performance is a silent, compounding risk that manual reporting never surfaced because nobody was looking at category-level trends consistently.

| Category | On-Time Rate | Avg Cost/Order | Total Revenue |
|----------|-------------|----------------|---------------|
| Meat & Seafood | 71.48% | LKR 14,028 | LKR 11.4M |
| Frozen | 71.58% | LKR 8,459 | LKR 7.1M |
| Dairy | 68.49% ❌ | LKR 4,295 | LKR 3.7M |
| Beverages | 70.10% | LKR 3,749 | LKR 3.0M |
| Produce | 70.04% | LKR 2,777 | LKR 2.3M |
| Dry Goods | 69.27% | LKR 2,256 | LKR 2.0M |

**What this means for the business:** These two categories need different solutions. Meat & Seafood needs priority routing and tighter SLA monitoring given its order value — one cancelled shipment costs more than 6 Dry Goods orders. Dairy needs a turnaround time investigation: why is the highest-volume perishable category consistently missing delivery targets? These are questions that only appear when you have automated, consistent category-level reporting.

---

### Finding 3 — The network has a seasonal rhythm nobody was managing

The monthly trend reveals a pattern invisible without 12 months of consistent automated data. On-time rates start low in January at **66.67%**, climb steadily to a peak of **72.13% in July**, then become unstable — dropping to 68.61% in August before recovering, then falling again to **68.89% in December**.

| Period | On-Time Rate | Signal |
|--------|-------------|--------|
| Jan 2024 | 66.67% | ⚠️ Year starts weak |
| Jul 2024 | 72.13% | ✅ Peak performance |
| Aug 2024 | 68.61% | ⚠️ Unexplained mid-year dip |
| Dec 2024 | 68.89% | ⚠️ Year ends weak |

**What this means for the business:** The January and December dips are likely seasonal — high festive order volumes straining warehouse capacity at year boundaries. The recommendation is to pre-position inventory and plan temporary staffing increases before January and December, not after the dip has already happened. The August dip is harder to explain and warrants investigation — it could be Q3 supplier delays or staffing patterns. Either way, this pattern only becomes visible when you have consistent automated reporting across the full year. A manual monthly report produced whenever someone has time would never surface it — and management would keep making the same capacity planning mistake every January.

---

## Dashboard

![KPI Dashboard](output/charts/kpi_dashboard.png)

---

## How the Pipeline Works

```
Raw CSV / S3  →  Clean with pandas  →  Calculate KPIs  →  Generate charts  →  Email report
```

1. **Ingest** — pulls order data from local CSV or AWS S3 via boto3
2. **Clean** — drops 50 duplicate rows, imputes 150 missing cost values with category median, parses dates
3. **Calculate** — on-time rate, avg delay, cost per order broken down by warehouse, region, category, and month
4. **Visualise** — 4-panel dark-mode dashboard saved as PNG
5. **Deliver** — HTML email report with embedded dashboard, sent automatically

The 2–3 hour manual process now runs in under 5 seconds.

---

## Project Structure

```
supply-chain-kpi/
├── scripts/
│   ├── generate_data.py      # 12 months synthetic order data — 5,000 rows with injected noise
│   ├── pipeline.py           # main orchestrator
│   ├── kpi_calculator.py     # KPI logic: overall, warehouse, monthly, category, regional
│   ├── chart_generator.py    # 4-panel matplotlib dashboard
│   ├── s3_utils.py           # AWS S3 upload/download via boto3
│   └── email_report.py       # HTML email via SMTP or SendGrid
├── tests/
│   └── test_pipeline.py      # 16 unit tests — all passing
├── output/
│   ├── charts/               # generated PNG dashboards
│   └── reports/kpi_summary.json
├── .github/workflows/
│   └── pipeline.yml          # GitHub Actions — runs daily 11:30 AM Sri Lanka time
├── .env.example              # credential template — never commit .env
├── Dockerfile                # multi-stage containerised pipeline
└── requirements.txt
```

---

## Run It Locally

```bash
git clone https://github.com/kavigamage-da/supply-chain-kpi.git
cd supply-chain-kpi
pip install -r requirements.txt

python scripts/generate_data.py   # generates data/orders_raw.csv
python scripts/pipeline.py        # full pipeline — cleans, calculates, charts
pytest tests/ -v                  # 16 unit tests
```

No AWS account needed. S3 is optional — set `USE_S3=false` in `.env`.

---

## GitHub Actions — Daily Automation

Runs on cron `0 6 * * *` — 06:00 UTC = 11:30 AM Sri Lanka time.

Every run is logged in the **Actions tab**. Dashboard PNGs are saved as downloadable artefacts for 30 days. To enable S3 and email, add secrets under **Settings → Secrets → Actions**:

| Secret | Purpose |
|--------|---------|
| `AWS_ACCESS_KEY_ID` | S3 read/write |
| `AWS_SECRET_ACCESS_KEY` | S3 read/write |
| `S3_BUCKET_NAME` | your bucket name |
| `EMAIL_USER` | Gmail address |
| `EMAIL_PASSWORD` | Gmail App Password |
| `EMAIL_TO` | report recipient |

---

## Tech Stack

`Python` `pandas` `numpy` `matplotlib` `boto3` `AWS S3` `GitHub Actions` `Docker` `pytest` `SendGrid`

---

## Why This Matters for Sysco LABS

Sysco LABS builds the data infrastructure for a company that ships millions of food orders every week. The analysts there don't just run pipelines — they find the Galle-South in the network, spot the Dairy category quietly underperforming, and catch the December degradation before it becomes a Q1 customer churn problem. That's what this project is built to demonstrate.

---

 
