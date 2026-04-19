import os
import pandas as pd
import numpy as np
from solar.config import SimulationConfig

EXPECTED_HOURS = 8760


def run_simulation(config: SimulationConfig, parquet_dir: str, year: str = "2025"):
    """
    Primary simulation function.
    Reads standardized parquet fields and operates via 1D Numpy arrays.
    """

    # 1. Load Data as pure 1D NumPy arrays (fail-fast on missing files)
    try:
        load_df = pd.read_parquet(os.path.join(parquet_dir, f"load_profile_{year}.parquet"))
        spot_df = pd.read_parquet(os.path.join(parquet_dir, f"spot_prices_se1_{year}.parquet"))
    except FileNotFoundError as exc:
        raise ValueError(f"Missing required parquet file: {exc}") from exc

    # Extract by named column as flattened 1D arrays (N,)
    consumption = load_df["consumption"].values.flatten()
    spot_prices = spot_df["spot_prices"].values.flatten()

    # Fast Assertions — enforce expected 8760-hour shape
    if len(consumption) != EXPECTED_HOURS:
        raise ValueError(
            f"load_profile.parquet has {len(consumption)} rows; expected {EXPECTED_HOURS}."
        )
    if len(spot_prices) != EXPECTED_HOURS:
        raise ValueError(
            f"spot_prices.parquet has {len(spot_prices)} rows; expected {EXPECTED_HOURS}."
        )

    # 2. Physics & Logic Simulation
    # 0-Baseline handling
    if config.pv_capacity_kw == 0 and config.battery_capacity_kwh == 0:
        grid_buy = consumption
        grid_sell = np.zeros_like(consumption)
    else:
        raise NotImplementedError(
            "PV/Battery not yet implemented — set pv_capacity_kw=0 and "
            "battery_capacity_kwh=0 for the baseline run."
        )

    # 3. Financial Metrics (Hourly vectors)
    # Spend(t) = Grid_buy(t) * ((price_spot + transfer + tax) * (1 + vat))
    energy_stack = spot_prices + config.grid_transfer_fee_sek + config.energy_tax_sek
    hourly_spend = grid_buy * (energy_stack * (1 + config.vat_rate))
    
    # Earn_spot(t) = Grid_sell(t) * (price_spot + utility_compensation)
    hourly_earn_spot = grid_sell * (spot_prices + config.utility_sell_compensation)

    # 4. Yearly Aggregations
    total_money_spent = float(np.sum(hourly_spend))
    total_money_earned_spot = float(np.sum(hourly_earn_spot))
    total_money_earned_fcr = 0.0 # Bypassed in baseline

    # Skattereduktion (Tax Credit)
    # Capped at min(exported_kwh, imported_kwh, 30,000 kWh)
    total_grid_buy_kwh = float(np.sum(grid_buy))
    total_grid_sell_kwh = float(np.sum(grid_sell))
    max_tax_kwh = min(total_grid_sell_kwh, total_grid_buy_kwh, 30000.0)
    total_tax_credit_sek = max_tax_kwh * config.tax_credit_rate

    # Net Electricity Cost (SEK)
    net_cost = (
        total_money_spent
        - (total_money_earned_spot + total_money_earned_fcr + total_tax_credit_sek)
        + config.aggregator_flat_fee_yearly
    )

    metrics = {
        "total_money_spent": total_money_spent,
        "total_money_earned_spot_sek": total_money_earned_spot,
        "total_tax_credit_sek": total_tax_credit_sek,
        "net_electricity_cost_sek": net_cost,
    }

    # 4. Memory footprint toggle
    if config.return_timeseries:
        ts_df = pd.DataFrame({
            "consumption": consumption,
            "grid_buy": grid_buy,
            "spot_prices": spot_prices,
            "hourly_spend": hourly_spend,
            "hourly_earn_spot": hourly_earn_spot,
        })
        return metrics, ts_df

    return metrics
