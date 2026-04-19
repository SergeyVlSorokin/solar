from dataclasses import dataclass, field
from typing import List

@dataclass
class SolarStringConfig:
    capacity_kw: float = 10.0
    tilt: float = 35.0
    azimuth: float = 180.0
    pr: float = 0.80


@dataclass
class SimulationConfig:
    battery_capacity_kwh: float = 0.0
    return_timeseries: bool = False
    
    # Solar Strings (Epic 2)
    pv_strings: List[SolarStringConfig] = field(default_factory=list)
    
    # Location (Default: Stockholm)
    latitude: float = 59.3293
    longitude: float = 18.0686
    
    # Financial primitives (Defaulting to SE1 - Northern Sweden values)
    grid_transfer_fee_sek: float = 0.18
    energy_tax_sek: float = 0.264
    vat_rate: float = 0.25
    utility_sell_compensation: float = 0.05
    tax_credit_rate: float = 0.60
    aggregator_fee_pct: float = 0.20
    aggregator_flat_fee_yearly: float = 0.0
