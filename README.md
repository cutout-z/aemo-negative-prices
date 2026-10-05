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

- **Merchant revenue risk** for renewable energy assets (generators receive the spot price — if it's negative, they pay to generate). Since five-minute settlement began on 1 October 2021 that is the 5-minute dispatch price counted here; before then generators were paid the 30-minute trading price (the average of six dispatch prices), so for May 2019 – September 2021 these figures show how often the dispatch price was negative, not how often the price actually paid was
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
| **Intervention handling** | During an AEMO intervention, `DISPATCHPRICE` carries two rows per interval. The pricing-run row (`INTERVENTION = 0`), which sets the market price, is kept; the intervention-run row (`INTERVENTION = 1`) is dropped. Intervals under intervention are still counted, once, at the market price |
| **Regions** | NSW1, QLD1, VIC1, SA1, TAS1 (all five NEM mainland + Tasmania regions) |
| **History** | May 2019 to present |
| **Update frequency** | Daily monitor on the NAS runner; publishes when new/corrected monthly data changes `outputs/summary.csv` |

---

## Analysis Methodology

### 1. Time Window — Daylight Hours Only

The analysis is restricted to dispatch intervals that **start between 08:00 and 16:00 AEST** (08:00 inclusive, 16:00 exclusive), capturing the core solar generation window. AEMO stamps each interval with its end time (`SETTLEMENTDATE`), so the window runs from the interval stamped 08:05 (08:00–08:05) to the one stamped 16:00 (15:55–16:00). Each interval is assigned to the month in which it starts. The NEM operates on AEST year-round (no daylight saving adjustment), so no timezone conversion is needed.

This gives **96 five-minute dispatch intervals per day** (8 hours × 12 intervals/hour).

### 2. Threshold Counting

For each region and each calendar month, the tool counts how many of those daylight intervals had an RRP **strictly less than** each of the following thresholds, comparing the price **in whole cents**. `DISPATCHPRICE` publishes RRP to five decimal places; it is rounded to the cent (half away from zero, the same 2-dp prices AEMO publishes in `PRICE_AND_DEMAND`) before the comparison. So −$0.00002 or −$0.004 counts as $0.00 and is not below $0, while −$0.005 rounds to −$0.01 and is; likewise −$10.004 is not below −$10 and −$10.005 is. A price exactly at a threshold (e.g. −$10.00) is not below it.

| Threshold | What it captures |
|-----------|-----------------|
| < $0/MWh | Any negative price — generators paying to stay on (before October 2021, only if the 30-minute trading price was also negative) |
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
| `outputs/All_States_negative_prices.xlsx` | All five regions in one workbook, one Percentages sheet per region |
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

The dashboard auto-updates after each published data refresh.

### Excel Files (direct download)

Download directly from the repo:

- [NSW](https://github.com/cutout-z/aemo-negative-prices/raw/main/outputs/NSW_negative_prices.xlsx)
- [QLD](https://github.com/cutout-z/aemo-negative-prices/raw/main/outputs/QLD_negative_prices.xlsx)
- [VIC](https://github.com/cutout-z/aemo-negative-prices/raw/main/outputs/VIC_negative_prices.xlsx)
- [SA](https://github.com/cutout-z/aemo-negative-prices/raw/main/outputs/SA_negative_prices.xlsx)
- [TAS](https://github.com/cutout-z/aemo-negative-prices/raw/main/outputs/TAS_negative_prices.xlsx)
- [All States](https://github.com/cutout-z/aemo-negative-prices/raw/main/outputs/All_States_negative_prices.xlsx)

### Raw CSV

For programmatic access or custom analysis, use [`outputs/summary.csv`](outputs/summary.csv) — one row per region and month (five rows per month since May 2019).

---

## Update Schedule

Production updates run on the **NAS runner** (QNAP `ai-wif-runner` container) via the `nas-job aemo-negative-prices` lane documented in [`deploy/README.md`](deploy/README.md). A QNAP scheduled task fires the lane daily to check for newly published or corrected monthly `DISPATCHPRICE` archives. It:

1. Probes AEMO for the latest published month
2. Reprocesses the recent complete-month overlap window
3. Re-generates all Excel workbooks and the summary CSV
4. Refuses to publish if any settled month (outside the overlap window) differs from the committed `outputs/summary.csv`, unless the run is an audited rewrite given `--allow-history-rewrite "<reason>"` (recorded in the commit message)
5. Commits and pushes only when canonical `outputs/summary.csv` changes, as `aemo-nas-bot`
6. Triggers the GitHub Pages redeploy

No manual intervention required. GitHub Actions is kept as a manual verification/fallback runner; a full historical refresh can still be triggered manually via the GitHub Actions UI if needed.

*Historical:* this lane ran on a Hetzner VPS under the `aemo-negative-prices.timer` systemd timer before the 2026-09 NAS migration. That setup is retired and its unit files were deleted in the same cleanup.

### Full Refresh (audited rewrite)

A method change rewrites settled months, so the pipeline needs an explicit reason:

```bash
python -m src.main --full-refresh --allow-history-rewrite "<reason>" \
    [--cache-dir DIR] [--output-dir DIR]
```

`--cache-dir` points NEMOSIS at an existing raw cache (default `data/`). NEMOSIS reuses any month already there as feather, or as the extracted monthly MMSDM `DISPATCHPRICE` CSV under its own name (`PUBLIC_DVD_DISPATCHPRICE_YYYYMM010000.CSV` to July 2024, `PUBLIC_ARCHIVE#DISPATCHPRICE#FILE01#YYYYMM010000.CSV` from August 2024), so unzipping the archives into the directory avoids a re-download. `--output-dir` writes `summary.csv` and the workbooks somewhere other than `outputs/`. Without the reason the run stops before writing anything and lists every settled row it would have changed.

### Output Validation

After the pipeline runs and before committing, an automated validation step (`tests/validate_outputs.py`) checks, exactly:

- `summary.csv` exists, is non-empty and has every count/percentage column with no empty cells
- Exactly the 5 NEM regions are present, with no duplicate region/month rows
- Every region-month has exactly days-in-month × 96 daylight intervals
- Every count is within [0, total] and every percentage equals `round(count / total × 100, 2)`
- Threshold ordering is preserved (count at $0 >= count at -$10 >= ... >= count at -$80)
- Each region's months run without gaps from May 2019, every region has the same months, and the latest month is a complete past month
- All 5 regional Excel workbooks and the All States workbook exist

Unit tests for the pipeline and the validator run with `python -m pytest` (synthetic data, no network).

If any check fails, the NAS lane or manual fallback workflow exits before committing — preventing bad data from reaching the dashboard.

---

## Key Observations (data to August 2026)

Shares below are of daylight intervals priced below $0, over the 12 months to August of each year. Before October 2021 they describe the dispatch price, not the 30-minute price generators were paid (see Goal).

- **Mainland negative pricing grew several-fold to 2024–25:** from the 12 months to August 2020 to the 12 months to August 2025, SA rose from 8.4% to 57.5%, QLD from 7.7% to 48.9%, VIC from 2.7% to 47.2% and NSW from 0.2% to 28.4%.
- **It has not kept rising:** in the 12 months to August 2026, QLD fell to 39.9%, NSW to 27.3% and SA to 56.4%, while VIC edged up to 48.1%. August 2026 was well below August 2025 in QLD (34.0% vs 70.1%), NSW (6.8% vs 26.8%) and SA (29.3% vs 42.8%).
- **Strongly seasonal:** the highest months are in spring — SA 92.8% (Oct 2024), QLD 88.1% (Sep 2025), VIC 88.1% (Nov 2025), NSW 74.4% (Nov 2025) — with winter troughs far lower.
- **South Australia (SA1)** leads in deep negatives (< −$50): about 33,000 daylight intervals since May 2019, against about 21,000 in VIC. Deep negatives have become rarer since 2023 (VIC: 24.0% of daylight intervals in 2023, 6.7% in 2025; SA: 25.6% to 10.8%).
- **Tasmania (TAS1)** stays low and variable, reflecting its hydro-dominated mix.
