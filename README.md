# AEMO Negative Electricity Prices — NEM Daylight Hours Analysis

## Quick Links

| Resource | URL |
|----------|-----|
| **Live Dashboard** | [cutout-z.github.io/aemo-negative-prices](https://cutout-z.github.io/aemo-negative-prices/) |
| **GitHub Repo** | [github.com/cutout-z/aemo-negative-prices](https://github.com/cutout-z/aemo-negative-prices) |
| **Excel Downloads** | Available on the dashboard or directly from the [`outputs/`](outputs/) folder |

---

## Goal

This tool tracks how often wholesale electricity prices go negative during daylight hours across Australia's National Electricity Market (NEM). It answers the question: **what percentage of daytime dispatch intervals had a regional reference price (RRP) below zero (and at progressively deeper negative thresholds)?**

Negative prices occur when electricity supply exceeds demand — typically driven by high renewable generation (solar during daytime, wind) and inflexible baseload plant. The frequency and depth of negative pricing is a key indicator of:

- **Merchant revenue risk** for renewable energy assets (generators receive the spot price — if it's negative, they pay to generate)
- **Curtailment economics** — at what price level does it become rational to curtail output?
- **Battery/storage value** — deeper and more frequent negatives increase the arbitrage opportunity
- **Market structure shifts** — rising negative price frequency signals structural oversupply during solar hours

---

## Data Source

All data is sourced from **AEMO's public wholesale electricity market archive** via [NEMOSIS](https://github.com/UNSW-CEEM/NEMOSIS), an open-source Python library maintained by the UNSW Collaboration on Energy and Environmental Markets (CEEM).

| Parameter | Detail |
|-----------|--------|
| **Table** | `DISPATCHPRICE` — 5-minute dispatch interval pricing |
| **Source URL** | `nemweb.com.au/Data_Archive/Wholesale_Electricity/MMSDM/` |
| **Field used** | `RRP` (Regional Reference Price, $/MWh) |
| **Intervention filtering** | Rows where `INTERVENTION != 0` (AEMO intervention repricing events) are excluded — only normal market outcomes are counted |
| **Regions** | NSW1, QLD1, VIC1, SA1, TAS1 (all five NEM mainland + Tasmania regions) |
| **History** | May 2019 to present |
| **Update frequency** | Monthly — automated on the 16th of each month |

---

## Analysis Methodology

### 1. Time Window — Daylight Hours Only

The analysis is restricted to **08:00–16:00 AEST (exclusive)**, capturing the core solar generation window. The NEM operates on AEST year-round (no daylight saving adjustment), so no timezone conversion is needed.

This gives **96 five-minute dispatch intervals per day** (8 hours × 12 intervals/hour).

### 2. Threshold Counting

For each region and each calendar month, the tool counts how many of those daylight intervals had an RRP **strictly less than** each of the following thresholds:

| Threshold | What it captures |
|-----------|-----------------|
| < $0/MWh | Any negative price — generators paying to stay on |
| < -$10/MWh | Mild negative — may still be worth running for LGC/contract reasons |
| < -$20/MWh | Moderate negative |
| < -$30/MWh | Increasingly uneconomic for most plant |
| < -$40/MWh | Significant negative |
| < -$50/MWh | Deep negative — most plant would curtail here |
| < -$60/MWh | Severe |
| < -$70/MWh | Extreme |
| < -$80/MWh | Extreme — approaching market floor price territory |

### 3. Percentage Calculation

For each region–month–threshold combination:

```
percentage = (count of intervals below threshold / total daylight intervals in that month) × 100
```

A month with 31 days has 2,976 daylight intervals (31 × 96). A percentage of 50% means half of all daytime 5-minute intervals had a negative price at that threshold.

### 4. Outputs

| Output | Description |
|--------|-------------|
| `outputs/summary.csv` | Master dataset — all regions, all months, all thresholds (counts + percentages) |
| `outputs/{Region}_negative_prices.xlsx` | Per-region Excel workbook with three sheets (see below) |
| `index.html` | Interactive web dashboard (GitHub Pages) |

**Excel workbook sheets:**

1. **Percentages** — clean table of percentage values, months as rows, thresholds as columns
2. **Heatmap** — same data with conditional colour formatting (green → yellow → red) for visual pattern recognition
3. **Audit** — raw interval counts and total daylight intervals for verification/QA

---

## How to Access

### Web Dashboard (recommended)

Open **[cutout-z.github.io/aemo-negative-prices](https://cutout-z.github.io/aemo-negative-prices/)** in any browser. No login required.

- Use the **region tabs** (NSW, QLD, VIC, SA, TAS) to switch between regions
- The table is a colour-coded heatmap — green cells = low negative frequency, red = high
- **Download Excel** links at the bottom for offline analysis

The dashboard auto-updates after each monthly data refresh.

### Excel Files (direct download)

Download directly from the repo:

- [NSW](https://github.com/cutout-z/aemo-negative-prices/raw/main/outputs/NSW_negative_prices.xlsx)
- [QLD](https://github.com/cutout-z/aemo-negative-prices/raw/main/outputs/QLD_negative_prices.xlsx)
- [VIC](https://github.com/cutout-z/aemo-negative-prices/raw/main/outputs/VIC_negative_prices.xlsx)
- [SA](https://github.com/cutout-z/aemo-negative-prices/raw/main/outputs/SA_negative_prices.xlsx)
- [TAS](https://github.com/cutout-z/aemo-negative-prices/raw/main/outputs/TAS_negative_prices.xlsx)

### Raw CSV

For programmatic access or custom analysis, use [`outputs/summary.csv`](outputs/summary.csv) — 410+ rows covering all regions and months.

---

## Update Schedule

A GitHub Actions workflow runs automatically on the **16th of each month at 00:00 UTC (~10:00 AEST)**. It:

1. Probes AEMO for the latest published month
2. Downloads only new data (incremental — no re-downloading of historical months)
3. Re-generates all Excel workbooks and the summary CSV
4. Commits the updated outputs to the repo
5. Redeploys the GitHub Pages dashboard

No manual intervention required. A full historical refresh can be triggered manually via the GitHub Actions UI if needed.

---

## Key Observations (as of early 2026)

- **Victoria (VIC1)** has seen a dramatic surge in negative pricing — Feb 2026 hit **88.3%** of daylight intervals below $0, up from single digits in 2019–2020
- **South Australia (SA1)** leads in deep negatives (< -$50) — consistent with its high wind + solar penetration
- **Queensland (QLD1)** and **NSW (NSW1)** show accelerating trends through 2025, lagging VIC/SA by ~12–18 months
- **Tasmania (TAS1)** shows moderate and more variable patterns, reflecting its hydro-dominated mix
- The trend across all regions is clearly upward — negative daytime pricing is becoming structural, not episodic
