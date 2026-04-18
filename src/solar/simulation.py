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

    # 3. Financial Metrics
    total_money_spent = float(np.sum(grid_buy * spot_prices))

    metrics = {
        "total_money_spent": total_money_spent,
        "net_electricity_cost_sek": total_money_spent,
        "total_money_earned_spot_sek": 0.0,
    }

    # 4. Memory footprint toggle
    if config.return_timeseries:
        ts_df = pd.DataFrame({
            "consumption": consumption,
            "grid_buy": grid_buy,
            "spot_prices": spot_prices,
        })
        return metrics, ts_df

    return metrics
