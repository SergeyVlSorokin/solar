import numpy as np
import pandas as pd
import pvlib
from typing import List, Tuple
from solar.config import SolarStringConfig

def calculate_solar_production(
    latitude: float,
    longitude: float,
    weather_data: dict,
    strings: List[SolarStringConfig],
    consumption: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calculates hourly solar production (P_solar) and net load (Net).
    
    Args:
        latitude: Station latitude.
        longitude: Station longitude.
        weather_data: Dict containing 'ghi', 'dni', 'dhi' (1D numpy arrays).
        strings: List of SolarStringConfig objects.
        consumption: 1D numpy array of hourly consumption (kWh).
        
    Returns:
        Tuple of (p_solar, net_load) as 1D numpy arrays (8760,).
    """
    # 1. Create DatetimeIndex for 2025 (8760 hours, non-leap year)
    # We use a fixed reference year for solar position calculations
    times = pd.date_range(
        start="2025-01-01 00:00:00",
        periods=len(consumption),
        freq="h",
        tz="Europe/Stockholm"
    )
    
    # 2. Calculate Solar Position
    # This is slightly computationally expensive but fits within the 100ms SLA for the whole pipeline
    solpos = pvlib.solarposition.get_solarposition(times, latitude, longitude)
    
    p_solar_total = np.zeros(len(consumption))
    
    # 3. Process each string
    for string in strings:
        # Calculate Plane of Array (POA) irradiance
        # Multi-model approach: get_total_irradiance handles beam, sky diffuse, and ground diffuse
        poa = pvlib.irradiance.get_total_irradiance(
            surface_tilt=string.tilt,
            surface_azimuth=string.azimuth,
            solar_zenith=solpos["apparent_zenith"],
            solar_azimuth=solpos["azimuth"],
            dni=weather_data["dni"],
            ghi=weather_data["ghi"],
            dhi=weather_data["dhi"]
        )
        
        # P_solar(t) = capacity_kw * (I_POA(t) / 1000) * pr
        # Normalize by 1000 W/m2 standard test condition
        # Extracting values to ensure we return pure numpy arrays, not pandas series
        p_solar_string = string.capacity_kw * (poa["poa_global"].values / 1000.0) * string.pr
        p_solar_total += p_solar_string
        
    # 4. Calculate Net Load: Net(t) = C(t) - P_solar(t)
    # Positive means load > solar (grid buy), negative means solar > load (excess)
    net_load = consumption - p_solar_total
        
    return p_solar_total, net_load
