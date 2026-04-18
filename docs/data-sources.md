# External Data Sources Guide

This document maps every external dataset the simulation requires to its authoritative
source, download instructions, and the final parquet files produced by the
`02-fetch-external-data.ipynb` pipeline.

The pipeline is configured for **Tore, Kalix (SE1)** and the year **2025** (to ensure FCR pricing reflects current marginal clearing logic).

---

## Data Requirements Summary

| Dataset | Parquet file | Source | Method |
|---|---|---|---|
| ✅ Solar irradiance & Weather (TMY) | `ghi_2025`, `dni_2025`, etc. | PVGIS EU API | Fully automatic |
| ✅ Spot electricity prices | `spot_prices_se1_2025.parquet` | elprisetjustnu.se API | Fully automatic |
| ✅ FCR-D clearing prices | `fcr_d_up_2025`, `fcr_d_down_2025` | SVK Mimer (CSV) | Automatic from raw CSV |
| ✅ Consumption load profile | `load_profile_2025.parquet` | Monthly totals | Automatic expansion |

All output parquet files strictly adhere to the 8,760-row architecture boundary and are saved in `data/processed/`.

---

## 1 — Solar Irradiance / Weather (for Epic 2 — PV generation)

**What the simulation needs:** 8,760 hourly arrays of GHI, DNI, and DHI (W/m²)
plus temperature (°C) and wind speed (m/s).

### Source: PVGIS — EU Joint Research Centre (free REST API, no login)

The notebook automatically calls the PVGIS API to fetch a **Typical Meteorological Year (TMY)** for the specified coordinates (Tore: 65.9172°N, 22.6501°E). 

> **API Request:** `https://re.jrc.ec.europa.eu/api/v5_3/tmy?lat=65.9172&lon=22.6501&outputformat=json`

The notebook processes this into 1D numpy arrays and drops any leap-day data to ensure an exact 8,760-row output, saving them as individual parquet files (`ghi_2025.parquet`, `temperature_2025.parquet`, etc.).

---

## 2 — Spot Electricity Prices

**What the simulation needs:** 8,760 hourly day-ahead prices in SEK/kWh for the
bidding zone (SE1).

### Source: elprisetjustnu.se (free REST API, no login)

Instead of manually downloading from ENTSO-E, the pipeline loops through all days of the year and queries this community API, which returns Nordpool prices already converted to SEK/kWh.

> **API Request:** `https://www.elprisetjustnu.se/api/v1/prices/{year}/{MM}-{DD}_{zone}.json`

**Exchange Rate Derivation:** The spot price API returns both `SEK_per_kWh` and `EUR_per_kWh`. The notebook automatically derives the **hourly EUR→SEK exchange rate** by taking the ratio. This exact hourly rate is saved and later used to accurately convert the FCR-D clearing prices from EUR to SEK.

---

## 3 — FCR-D Clearing Prices (for Epic 3 & 5)

**What the simulation needs:** 8,760 hourly FCR-D Up and Down clearing prices
in SEK/MW/h.

### Source: SVK Mimer Portal (free, no login required)

To get this data, a manual download is initially required, though the notebook fully automates the parsing.

**Download Steps:**
1. Go to https://mimer.svk.se → *Ancillary services* → *FCR* → *FCR-D*
2. Select **FCR-D Upp** (or Ned), Market = **Total**
3. Set **Time period**: 2025-01-01 to 2025-12-31
4. Click **Download CSV**
5. Save as `data/raw/fcr_d_up_prices_2025.csv` (and `down`)

**Data Characteristics & Processing:**
- **Granularity:** The data is already **hourly** (8760 rows).
- **Structure:** SVK actually exports the *entire matrix* of products (FCR-N, FCR-D up, FCR-D down) regardless of which product you selected to download. Both files contain identical columns.
- **Formatting:** UTF-8 with BOM, European decimals (commas), and a `Summa` summary row at the bottom.
- **Conversion:** The notebook parses the comma decimals, drops the summary row, and applies the hourly EUR→SEK exchange rate derived from the spot price data to produce exact SEK/MW/h arrays.

---

## 4 — Consumption Profile

**What the simulation needs:** 8,760 hourly consumption values in kWh.

**Implementation:**
The pipeline currently hardcodes monthly consumption totals (e.g., Jan: 2060 kWh, Feb: 1566 kWh) inside the notebook itself. It automatically expands these totals into an 8,760-hour flat profile by dividing each month's total uniformly across its hours (step-function).

---

## Recommended Year: 2025

The simulation year is set to **2025**.

> [!IMPORTANT]
> **Why not 2023? Pricing model overhaul.** 
> Prior to February 1, 2024, SVK operated FCR on a pay-as-bid basis. As of Feb 2024, they transitioned to **marginal pricing**, which significantly changes the revenue reality for battery assets. Using 2025 ensures the entire simulation period reflects the current and future market structure.
