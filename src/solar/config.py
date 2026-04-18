from dataclasses import dataclass

@dataclass
class SimulationConfig:
    pv_capacity_kw: float
    battery_capacity_kwh: float
    return_timeseries: bool = False
