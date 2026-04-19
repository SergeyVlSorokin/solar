import unittest.mock as mock

import numpy as np
import pandas as pd
import pytest

from solar.config import SimulationConfig, BatteryConfig, SolarStringConfig
from solar.simulation import run_simulation


def test_simulation_config_defaults():
    config = SimulationConfig()
    assert config.battery is None
    assert config.return_timeseries is False


@mock.patch("solar.simulation.pd.read_parquet")
def test_run_simulation_data_loading(mock_read_parquet):
    # Setup mock data with named columns matching expected schema
    load_df = pd.DataFrame({"consumption": np.ones(8760) * 2})
    spot_df = pd.DataFrame({"spot_prices": np.ones(8760) * 0.5})

    def mock_read(path, **kwargs):
        path_str = str(path)
        if "load_profile" in path_str and ".parquet" in path_str:
            return load_df
        elif "spot_prices" in path_str and ".parquet" in path_str:
            return spot_df
        elif "fcr_d_up" in path_str and ".parquet" in path_str:
            return pd.DataFrame({"fcr_d_up_prices": np.zeros(8760)})
        elif any(x in path_str for x in ["ghi", "dni", "dhi"]) and ".parquet" in path_str:
            col = "ghi" if "ghi" in path_str else ("dni" if "dni" in path_str else "dhi")
            return pd.DataFrame({col: np.zeros(8760)})
        raise FileNotFoundError(f"{path} not mock matched")

    mock_read_parquet.side_effect = mock_read

    config = SimulationConfig()
    result = run_simulation(config, "mock_dir")

    assert "total_money_spent" in result
    # Formula: Hours(8760) * Load(2) * ((Spot(0.5) + Trans(0.18) + Tax(0.264)) * VAT(1.25))
    # (0.5 + 0.18 + 0.264) * 1.25 = 1.18
    # 8760 * 2 * 1.18 = 20673.6
    expected = 8760 * 2 * 1.18
    assert result["total_money_spent"] == pytest.approx(expected)
    assert "p_grid_max_kw" in result
    assert result["p_grid_max_kw"] == pytest.approx(13.8564, rel=1e-3)
    # read_parquet must be called exactly 6 times (load + spot + fcr + 3 weather)
    assert mock_read_parquet.call_count == 6


@mock.patch("solar.simulation.pd.read_parquet")
def test_run_simulation_timeseries(mock_read_parquet):
    load_df = pd.DataFrame({"consumption": np.ones(8760) * 2})
    spot_df = pd.DataFrame({"spot_prices": np.ones(8760) * 0.5})

    def mock_read(path, **kwargs):
        path_str = str(path)
        if "load_profile" in path_str and ".parquet" in path_str:
            return load_df
        elif "spot_prices" in path_str and ".parquet" in path_str:
            return spot_df
        elif "fcr_d_up" in path_str and ".parquet" in path_str:
            return pd.DataFrame({"fcr_d_up_prices": np.zeros(8760)})
        elif any(x in path_str for x in ["ghi", "dni", "dhi"]) and ".parquet" in path_str:
            col = "ghi" if "ghi" in path_str else ("dni" if "dni" in path_str else "dhi")
            return pd.DataFrame({col: np.zeros(8760)})
        raise FileNotFoundError(f"{path} not mock matched")

    mock_read_parquet.side_effect = mock_read

    config = SimulationConfig(return_timeseries=True)
    metrics, ts_df = run_simulation(config, "mock_dir")

    assert "total_money_spent" in metrics
    assert isinstance(ts_df, pd.DataFrame)
    assert len(ts_df) == 8760
    assert list(ts_df.columns) == [
        "consumption", "p_solar", "net_load", "battery_charged_kwh", "battery_discharged_kwh", 
        "battery_soc_kwh", "grid_buy", "grid_sell", "unmet_load", "curtailed", 
        "spot_prices", "hourly_spend", "hourly_earn_spot", "hourly_revenue_fcr"
    ]


@mock.patch("solar.simulation.pd.read_parquet")
def test_financial_math_accuracy(mock_read_parquet):
    # Test specific financial stack: Spot=1.0, Trans=0.2, Tax=0.3, VAT=0.25 (1.25x)
    # Expected cost per kWh = (1.0 + 0.2 + 0.3) * 1.25 = 1.5 * 1.25 = 1.875
    load_df = pd.DataFrame({"consumption": np.ones(8760) * 10})
    spot_df = pd.DataFrame({"spot_prices": np.ones(8760) * 1.0})
    fcr_df = pd.DataFrame({"fcr_d_up_prices": np.zeros(8760)})
    ghi_df = pd.DataFrame({"ghi": np.zeros(8760)})
    dni_df = pd.DataFrame({"dni": np.zeros(8760)})
    dhi_df = pd.DataFrame({"dhi": np.zeros(8760)})
    mock_read_parquet.side_effect = [load_df, spot_df, fcr_df, ghi_df, dni_df, dhi_df]

    config = SimulationConfig(
        battery=BatteryConfig(
            capacity_kwh=10.0,
            max_power_kw=5.0,
            round_trip_efficiency=0.90,
            fcr_allocation_pct=1.0
        ),
        grid_transfer_fee_sek=0.2,
        energy_tax_sek=0.3,
        vat_rate=0.25
    )
    # The battery is now used in the loop equations (Story 3.2).
    # Since Net load is constant +10kW and p_arb is only 1.0kW (0.2 * 5.0),
    # the battery will attempt to discharge until empty. But it starts empty (0.0).
    # So p_discharge will be 0.
    metrics = run_simulation(config, "mock_dir")
    expected_total = 8760 * 10 * 1.875
    assert metrics["total_money_spent"] == pytest.approx(expected_total)
    assert metrics["net_electricity_cost_sek"] == pytest.approx(expected_total)
    assert metrics["total_tax_credit_sek"] == 0.0 # No export in baseline

@mock.patch("solar.simulation.pd.read_parquet")
def test_fcr_scaling_split_allocation(mock_read_parquet):
    # Verify that if fcr_allocation_pct = 0.5, only 50% of max_power is sold as FCR
    size = 8760
    load_df = pd.DataFrame({"consumption": np.zeros(size)}) # No consumption
    spot_df = pd.DataFrame({"spot_prices": np.zeros(size)})
    fcr_df = pd.DataFrame({"fcr_d_up_prices": np.ones(size) * 1000.0}) # 1000 SEK/MW/h
    ghi_df = pd.DataFrame({"ghi": np.zeros(size)})
    dni_df = pd.DataFrame({"dni": np.zeros(size)})
    dhi_df = pd.DataFrame({"dhi": np.zeros(size)})
    mock_read_parquet.side_effect = [load_df, spot_df, fcr_df, ghi_df, dni_df, dhi_df]

    config = SimulationConfig(
        battery=BatteryConfig(
            capacity_kwh=10.0,
            max_power_kw=10.0,
            fcr_allocation_pct=0.5, # 50% for FCR -> 5 kW
            round_trip_efficiency=0.95
        ),
        aggregator_fee_pct=0.0
    )
    # Expected FCR revenue:
    # P_FCR = 10kW * 0.5 = 5 kW
    # Revenue/hour = (5 / 1000) * 1000 * (1 - 0) = 5 SEK
    # Total = 8760 * 5 = 43800.0
    metrics = run_simulation(config, "mock_dir")
    assert metrics["total_money_earned_fcr_sek"] == pytest.approx(8760 * 5.0)
