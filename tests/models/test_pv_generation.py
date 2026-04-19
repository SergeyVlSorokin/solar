import numpy as np
import pytest
from solar.models.pv_generation import calculate_solar_production
from solar.config import SolarStringConfig

@pytest.fixture
def mock_weather():
    return {
        "ghi": np.ones(8760) * 500,
        "dni": np.ones(8760) * 400,
        "dhi": np.ones(8760) * 100
    }

@pytest.fixture
def mock_consumption():
    return np.ones(8760) * 1.5

def test_pv_generation_single_string(mock_weather, mock_consumption):
    # Setup single string: 10kWp, South-facing (180), 35 tilt
    string = SolarStringConfig(capacity_kw=10.0, tilt=35.0, azimuth=180.0, pr=0.80)
    
    p_solar, net_load = calculate_solar_production(
        latitude=59.3293,
        longitude=18.0686,
        weather_data=mock_weather,
        strings=[string],
        consumption=mock_consumption
    )
    
    assert len(p_solar) == 8760
    assert len(net_load) == 8760
    assert np.all(p_solar >= 0)
    # Check that net_load calculation is consistent
    assert np.allclose(net_load, mock_consumption - p_solar)
    # At least some hours should have production (depending on solpos, but in our constant mock it should be positive)
    # Note: pvlib will calculate 0 when sun is below horizon even with constant GHI input
    assert np.any(p_solar > 0)

def test_pv_generation_multi_string(mock_weather, mock_consumption):
    # Setup two strings: South and West
    s1 = SolarStringConfig(capacity_kw=5.0, tilt=35.0, azimuth=180.0, pr=0.80)
    s2 = SolarStringConfig(capacity_kw=5.0, tilt=35.0, azimuth=270.0, pr=0.80)
    
    p_solar_multi, _ = calculate_solar_production(
        latitude=59.3293,
        longitude=18.0686,
        weather_data=mock_weather,
        strings=[s1, s2],
        consumption=mock_consumption
    )
    
    p_solar_s1, _ = calculate_solar_production(
        latitude=59.3293,
        longitude=18.0686,
        weather_data=mock_weather,
        strings=[s1],
        consumption=mock_consumption
    )
    
    p_solar_s2, _ = calculate_solar_production(
        latitude=59.3293,
        longitude=18.0686,
        weather_data=mock_weather,
        strings=[s2],
        consumption=mock_consumption
    )
    
    # Linear superposition check
    assert np.allclose(p_solar_multi, p_solar_s1 + p_solar_s2)

def test_pv_generation_empty_strings(mock_weather, mock_consumption):
    p_solar, net_load = calculate_solar_production(
        latitude=59.3293,
        longitude=18.0686,
        weather_data=mock_weather,
        strings=[],
        consumption=mock_consumption
    )
    
    assert np.all(p_solar == 0)
    assert np.all(net_load == mock_consumption)
