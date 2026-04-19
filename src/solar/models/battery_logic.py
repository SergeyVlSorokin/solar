import numpy as np
from dataclasses import dataclass
from typing import Tuple
from solar.config import BatteryConfig

@dataclass
class AllocationResult:
    """
    Structured container for battery capacity allocation outputs.
    All attributes include explicit units to prevent unit errors in simulation.
    """
    p_fcr_kw: float
    p_arb_kw: float
    e_arb_kwh: float

def allocate_battery_capacity(config: BatteryConfig) -> AllocationResult:
    """
    Splits physical battery capacity and power between FCR and Arbitrage buckets.
    Ensures fail-fast validation of allocation bounds and physical constraints.
    
    Args:
        config: BatteryConfig object containing physical and market parameters.
        
    Returns:
        AllocationResult: Dataclass containing p_fcr_kw, p_arb_kw, and e_arb_kwh.
        
    Raises:
        ValueError: If fcr_allocation_pct is outside [0, 1] or physical params are negative.
    """
    # 1. Validation
    fcr_pct = config.fcr_allocation_pct
    if not (0.0 <= fcr_pct <= 1.0):
        raise ValueError(
            f"fcr_allocation_pct must be strictly bounded between 0.0 and 1.0; got {fcr_pct}"
        )
    
    if config.max_power_kw < 0:
        raise ValueError(f"max_power_kw must be non-negative; got {config.max_power_kw}")
        
    if config.capacity_kwh < 0:
        raise ValueError(f"capacity_kwh must be non-negative; got {config.capacity_kwh}")
    
    # 2. Calculate splits according to PRD 5.4
    p_fcr_kw = config.max_power_kw * fcr_pct
    p_arb_kw = config.max_power_kw - p_fcr_kw
    e_arb_kwh = config.capacity_kwh * (1.0 - fcr_pct)
    
    return AllocationResult(
        p_fcr_kw=p_fcr_kw,
        p_arb_kw=p_arb_kw,
        e_arb_kwh=e_arb_kwh
    )

def simulate_battery_loop(
    net_load: np.ndarray,
    p_arb_kw: float,
    e_arb_kwh: float,
    eta_rt: float
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Sequential battery state-of-charge simulation loop (PRD 5.4).
    Calculates charge/discharge flows and state-of-charge over time.
    
    Args:
        net_load: 1D array of Net(t) = Consumption(t) - Solar(t).
        p_arb_kw: Maximum power limit for arbitrage/self-consumption (kW).
        e_arb_kwh: Usable energy capacity for arbitrage (kWh).
        eta_rt: Round-trip efficiency (fraction).
        
    Returns:
        Tuple of (p_charge_kw, p_discharge_kw, soc_kwh) as 1D arrays.
        Note: returning soc_kwh is an intended deviation from AC 6 for analytical visibility.
    """
    # 1. Validation (Fail-fast)
    if not (0.0 < eta_rt <= 1.0):
        raise ValueError(f"round_trip_efficiency must be in range (0, 1]; got {eta_rt}")
    
    if e_arb_kwh < 0:
        raise ValueError(f"e_arb_kwh must be non-negative; got {e_arb_kwh}")

    num_steps = len(net_load)
    p_charge = np.zeros(num_steps)
    p_discharge = np.zeros(num_steps)
    soc = np.zeros(num_steps + 1)  # Including t=0
    
    # eta_c = eta_d = sqrt(eta_rt) per PRD
    # Validation above ensures eta_rt > 0, so sqrt(eta_rt) > 0.
    eta_eff = np.sqrt(eta_rt)
    
    for t in range(num_steps):
        current_net = net_load[t]
        prev_soc = soc[t]
        
        if current_net < 0:  # Excess Solar (Charge)
            # P_charge(t) = min(abs(Net(t)), P_arb, (E_arb - SOC(t-1)) / eta_c)
            p_charge[t] = min(abs(current_net), p_arb_kw, (e_arb_kwh - prev_soc) / eta_eff)
            soc[t+1] = prev_soc + (p_charge[t] * eta_eff)
            
        elif current_net > 0:  # Need Power (Discharge)
            # P_discharge(t) = min(Net(t), P_arb, SOC(t-1) * eta_d)
            p_discharge[t] = min(current_net, p_arb_kw, prev_soc * eta_eff)
            soc[t+1] = prev_soc - (p_discharge[t] / eta_eff)
            
        else:  # Neutral
            soc[t+1] = prev_soc
            
    # Return arrays of length num_steps (dropping initial SOC for alignment)
    return p_charge, p_discharge, soc[1:]
