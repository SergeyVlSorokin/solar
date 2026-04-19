import numpy as np
from dataclasses import dataclass
from typing import Tuple, Optional
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

def get_arbitrage_signals(prices: np.ndarray, n_low: int = 6, n_high: int = 6) -> Tuple[np.ndarray, np.ndarray]:
    """
    Identifies the n_low cheapest and n_high most expensive hours for EACH 24h window.
    Returns two boolean masks of the same length as prices.
    """
    num_steps = len(prices)
    if num_steps == 0:
        return np.array([], dtype=bool), np.array([], dtype=bool)

    num_days = num_steps // 24
    num_full_day_hours = num_days * 24
    
    is_low = np.zeros(num_steps, dtype=bool)
    is_high = np.zeros(num_steps, dtype=bool)

    # 1. Process full days
    if num_days > 0:
        full_day_prices = prices[:num_full_day_hours].reshape((num_days, 24))
        sorted_idx = np.argsort(full_day_prices, axis=1)
        
        is_low_2d = np.zeros((num_days, 24), dtype=bool)
        is_high_2d = np.zeros((num_days, 24), dtype=bool)
        
        rows = np.arange(num_days)[:, None]
        is_low_2d[rows, sorted_idx[:, :n_low]] = True
        is_high_2d[rows, sorted_idx[:, -n_high:]] = True
        
        is_low[:num_full_day_hours] = is_low_2d.flatten()
        is_high[:num_full_day_hours] = is_high_2d.flatten()
    
    # 2. Process remaining hours (partial day at the end)
    if num_steps > num_full_day_hours:
        remaining = prices[num_full_day_hours:]
        num_rem = len(remaining)
        sorted_rem = np.argsort(remaining)
        
        # Scale n_low/n_high for the partial day if needed, or just use raw n
        # Here we just use n_low/n_high capped by remaining length
        rem_low_idx = sorted_rem[:min(n_low, num_rem)]
        rem_high_idx = sorted_rem[-min(n_high, num_rem):]
        
        offset = num_full_day_hours
        is_low[offset + rem_low_idx] = True
        is_high[offset + rem_high_idx] = True
    
    return is_low, is_high

def simulate_battery_loop(
    net_load: np.ndarray,
    p_arb_kw: float,
    e_arb_kwh: float,
    eta_rt: float,
    spot_prices: Optional[np.ndarray] = None,
    n_charge_hours: int = 6,
    n_discharge_hours: int = 6
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

    # 2. Arbitrage Signal Pre-calculation
    # If prices are provided, we enable price-driven arbitrage.
    # Otherwise, we default to pure self-consumption (no price signals).
    is_low = np.zeros(num_steps, dtype=bool)
    is_high = np.zeros(num_steps, dtype=bool)
    if spot_prices is not None:
        is_low, is_high = get_arbitrage_signals(spot_prices, n_low=n_charge_hours, n_high=n_discharge_hours)

    # 3. State Initialization
    p_charge = np.zeros(num_steps)
    p_discharge = np.zeros(num_steps)
    soc = np.zeros(num_steps + 1)  # Including t=0
    
    # eta_c = eta_d = sqrt(eta_rt) per PRD
    # Validation above ensures eta_rt > 0, so sqrt(eta_rt) > 0.
    eta_eff = np.sqrt(eta_rt)
    
    for t in range(num_steps):
        current_net = net_load[t]
        prev_soc = soc[t]
        
        # Priority 1: Solar Self-Consumption (Charge if excess solar)
        if current_net < 0:
            p_charge[t] = min(abs(current_net), p_arb_kw, (e_arb_kwh - prev_soc) / eta_eff)
            soc[t+1] = prev_soc + (p_charge[t] * eta_eff)
            
        # Priority 2: Price Arbitrage (Charge if price is low, even if net_load > 0)
        elif is_low[t]:
            # Note: We still honor p_arb_kw and e_arb_kwh
            p_charge[t] = min(p_arb_kw, (e_arb_kwh - prev_soc) / eta_eff)
            soc[t+1] = prev_soc + (p_charge[t] * eta_eff)
            
        # Priority 3: Displacement/Discharge (Need power OR price is high)
        elif current_net > 0 or is_high[t]:
            # P_discharge targets either the load or max battery power
            target_discharge = current_net if (current_net > 0 and not is_high[t]) else p_arb_kw
            p_discharge[t] = min(target_discharge, p_arb_kw, prev_soc * eta_eff)
            soc[t+1] = prev_soc - (p_discharge[t] / eta_eff)
            
        else:  # Neutral
            soc[t+1] = prev_soc
            
    # Return arrays of length num_steps (dropping initial SOC for alignment)
    return p_charge, p_discharge, soc[1:]
