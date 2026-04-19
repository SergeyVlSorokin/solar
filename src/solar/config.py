from dataclasses import dataclass

@dataclass
class SimulationConfig:
    pv_capacity_kw: float
    battery_capacity_kwh: float
    return_timeseries: bool = False
    
    # Financial primitives (Defaulting to SE1 - Northern Sweden values)
    grid_transfer_fee_sek: float = 0.18
    energy_tax_sek: float = 0.264
    vat_rate: float = 0.25
    utility_sell_compensation: float = 0.05
    tax_credit_rate: float = 0.60
    aggregator_fee_pct: float = 0.20
    aggregator_flat_fee_yearly: float = 0.0
