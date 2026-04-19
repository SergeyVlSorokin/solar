import os
import numpy as np
import pandas as pd
from solar.config import SimulationConfig
from solar.models.pv_generation import calculate_solar_production
from solar.models.battery_logic import allocate_battery_capacity, simulate_battery_loop
from solar.models.grid_finance import calculate_grid_limit, calculate_grid_flows, calculate_financials

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
        fcr_df = pd.read_parquet(os.path.join(parquet_dir, f"fcr_d_up_{year}.parquet"))
    except FileNotFoundError as exc:
        raise ValueError(f"Missing required parquet file: {exc}") from exc

    # Extract by named column as flattened 1D arrays (N,)
    consumption = load_df["consumption"].values.flatten()
    spot_prices = spot_df["spot_prices"].values.flatten()
    fcr_prices = fcr_df["fcr_d_up_prices"].values.flatten()

    # Fast Assertions — enforce expected 8760-hour shape
    if len(consumption) != EXPECTED_HOURS:
        raise ValueError(
            f"load_profile.parquet has {len(consumption)} rows; expected {EXPECTED_HOURS}."
        )
    if len(spot_prices) != len(consumption):
        raise ValueError(
            f"spot_prices length ({len(spot_prices)}) does not match consumption length ({len(consumption)})."
        )
    if len(fcr_prices) != len(consumption):
        raise ValueError(
            f"fcr_prices length ({len(fcr_prices)}) does not match consumption length ({len(consumption)})."
        )
    # 2. Load Weather Data (GHI, DNI, DHI)
    # Support both standard names and raw PVGIS names (G(h), Gb(n), Gd(h))
    def _extract_col(df, aliases):
        for a in aliases:
            if a in df.columns:
                return df[a].values.flatten()
        raise KeyError(f"Required columns {aliases} not found in {list(df.columns)}")

    try:
        ghi_path = os.path.join(parquet_dir, f"ghi_{year}.parquet")
        dni_path = os.path.join(parquet_dir, f"dni_{year}.parquet")
        dhi_path = os.path.join(parquet_dir, f"dhi_{year}.parquet")

        ghi = _extract_col(pd.read_parquet(ghi_path), ["ghi", "G(h)"])
        dni = _extract_col(pd.read_parquet(dni_path), ["dni", "Gb(n)"])
        dhi = _extract_col(pd.read_parquet(dhi_path), ["dhi", "Gd(h)"])
    except (FileNotFoundError, KeyError) as exc:
        raise ValueError(f"Missing required weather data: {exc}") from exc

    weather_data = {"ghi": ghi, "dni": dni, "dhi": dhi}

    # 3. Physics & Logic Simulation
    p_solar = np.zeros_like(consumption)
    net_load = consumption.copy()  # Default to 0-PV baseline
    
    # 3.1. Battery Parameters Initialization
    p_charge = np.zeros_like(consumption)
    p_discharge = np.zeros_like(consumption)
    soc_kwh = np.zeros_like(consumption)
    p_fcr_kw = 0.0
    battery_allocation = None

    if config.battery:
        battery_allocation = allocate_battery_capacity(config.battery)
        p_fcr_kw = battery_allocation.p_fcr_kw

    # 3.2. Grid Limits (Epic 4.1)
    p_grid_max_kw = calculate_grid_limit(config.main_fuse_size_a)


    # 3.2. Solar Production
    if config.pv_strings:
        p_solar, net_load = calculate_solar_production(
            latitude=config.latitude,
            longitude=config.longitude,
            weather_data=weather_data,
            strings=config.pv_strings,
            consumption=consumption
        )

    # 3.3. Sequential Battery Loop
    if config.battery and battery_allocation:
        p_charge, p_discharge, soc_kwh = simulate_battery_loop(
            net_load=net_load,
            p_arb_kw=battery_allocation.p_arb_kw,
            e_arb_kwh=battery_allocation.e_arb_kwh,
            eta_rt=config.battery.round_trip_efficiency,
            spot_prices=spot_prices
        )

    # 4. Grid Balancing
    # Residual(t) = Net(t) + P_charge(t) - P_discharge(t)
    residual = net_load + p_charge - p_discharge
    
    grid_buy, grid_sell, unmet_load, curtailed = calculate_grid_flows(
        residual=residual,
        p_grid_max=p_grid_max_kw
    )
    
    # Financials (Epic 5.1 Modularized)
    fin_results = calculate_financials(
        grid_buy=grid_buy,
        grid_sell=grid_sell,
        p_fcr_kw=p_fcr_kw,
        price_spot_hourly=spot_prices,
        price_fcr_hourly=fcr_prices,
        grid_transfer_fee_sek=config.grid_transfer_fee_sek,
        energy_tax_sek=config.energy_tax_sek,
        vat_rate=config.vat_rate,
        utility_sell_compensation=config.utility_sell_compensation,
        aggregator_fee_pct=config.aggregator_fee_pct
    )
    
    hourly_spend = fin_results["hourly_spend"]
    hourly_earn_spot = fin_results["hourly_earn_spot"]
    hourly_revenue_fcr = fin_results["hourly_revenue_fcr"]

    # 5. Yearly Aggregations
    total_money_spent = float(np.sum(hourly_spend))
    total_money_earned_spot = float(np.sum(hourly_earn_spot))
    total_money_earned_fcr = float(np.sum(hourly_revenue_fcr))

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
        "total_money_earned_fcr_sek": total_money_earned_fcr,
        "total_tax_credit_sek": total_tax_credit_sek,
        "net_electricity_cost_sek": net_cost,
        "total_battery_charge_kwh": float(np.sum(p_charge)),
        "total_battery_discharge_kwh": float(np.sum(p_discharge)),
        "p_grid_max_kw": p_grid_max_kw,
        "total_unmet_load_kwh": float(np.sum(unmet_load)),
        "total_curtailed_kwh": float(np.sum(curtailed)),
    }

    # 6. Memory footprint toggle
    if config.return_timeseries:
        ts_df = pd.DataFrame({
            "consumption": consumption,
            "p_solar": p_solar,
            "net_load": net_load,
            "battery_charged_kwh": p_charge,
            "battery_discharged_kwh": p_discharge,
            "battery_soc_kwh": soc_kwh,
            "grid_buy": grid_buy,
            "grid_sell": grid_sell,
            "unmet_load": unmet_load,
            "curtailed": curtailed,
            "spot_prices": spot_prices,
            "hourly_spend": hourly_spend,
            "hourly_earn_spot": hourly_earn_spot,
            "hourly_revenue_fcr": hourly_revenue_fcr,
        })
        return metrics, ts_df

    return metrics
