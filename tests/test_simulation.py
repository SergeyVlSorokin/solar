import unittest.mock as mock

import numpy as np
import pandas as pd
import pytest

from solar.config import SimulationConfig
from solar.simulation import run_simulation


def test_simulation_config_defaults():
    config = SimulationConfig(pv_capacity_kw=0, battery_capacity_kwh=0)
    assert config.pv_capacity_kw == 0
    assert config.battery_capacity_kwh == 0
    assert config.return_timeseries is False


@mock.patch("solar.simulation.pd.read_parquet")
def test_run_simulation_data_loading(mock_read_parquet):
    # Setup mock data with named columns matching expected schema
    load_df = pd.DataFrame({"consumption": np.ones(8760) * 2})
    spot_df = pd.DataFrame({"spot_prices": np.ones(8760) * 0.5})

    def mock_read(path, **kwargs):
        if "load_profile.parquet" in str(path):
            return load_df
        elif "spot_prices.parquet" in str(path):
            return spot_df
        raise FileNotFoundError(f"{path} not mock matched")

    mock_read_parquet.side_effect = mock_read

    config = SimulationConfig(pv_capacity_kw=0, battery_capacity_kwh=0)
    result = run_simulation(config, "mock_dir")

    assert "total_money_spent" in result
    # Deterministic value: 8760 hours × 2 kWh × 0.5 SEK/kWh = 8760.0 SEK
    assert result["total_money_spent"] == pytest.approx(8760 * 2 * 0.5)
    # read_parquet must be called exactly twice (load + spot)
    assert mock_read_parquet.call_count == 2


@mock.patch("solar.simulation.pd.read_parquet")
def test_run_simulation_timeseries(mock_read_parquet):
    load_df = pd.DataFrame({"consumption": np.ones(8760) * 2})
    spot_df = pd.DataFrame({"spot_prices": np.ones(8760) * 0.5})

    def mock_read(path, **kwargs):
        if "load_profile.parquet" in str(path):
            return load_df
        elif "spot_prices.parquet" in str(path):
            return spot_df
        raise FileNotFoundError(f"{path} not mock matched")

    mock_read_parquet.side_effect = mock_read

    config = SimulationConfig(pv_capacity_kw=0, battery_capacity_kwh=0, return_timeseries=True)
    metrics, ts_df = run_simulation(config, "mock_dir")

    assert "total_money_spent" in metrics
    assert isinstance(ts_df, pd.DataFrame)
    assert len(ts_df) == 8760
    assert list(ts_df.columns) == ["consumption", "grid_buy", "spot_prices"]
