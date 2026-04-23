import numpy as np
import scipy.sparse as sp
from scipy.optimize import linprog
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

def optimize_battery_loop(
    net_load: np.ndarray,
    p_arb_kw: float,
    e_arb_kwh: float,
    eta_rt: float,
    cost_buy: np.ndarray,
    cost_sell: np.ndarray,
    p_grid_max: float = 14.0
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Linear Programming (LP) optimization for battery schedule with perfect foresight.
    """
    num_steps = len(net_load)
    eta_eff = np.sqrt(eta_rt)
    
    # Variables: 0..N-1: GridBuy, N..2N-1: GridSell, 2N..3N-1: P_Charge, 3N..4N-1: P_Discharge, 4N..5N-1: SOC
    c = np.zeros(5 * num_steps)
    c[0:num_steps] = cost_buy
    c[num_steps:2*num_steps] = -cost_sell
    
    # Bounds
    bounds = []
    for _ in range(num_steps): bounds.append((0, p_grid_max))      # GridBuy
    for _ in range(num_steps): bounds.append((0, p_grid_max))      # GridSell
    for _ in range(num_steps): bounds.append((0, p_arb_kw))        # P_charge
    for _ in range(num_steps): bounds.append((0, p_arb_kw))        # P_discharge
    for _ in range(num_steps): bounds.append((0, e_arb_kwh))       # SOC
    
    # A_eq
    rows = []
    cols = []
    data = []
    b_eq = np.zeros(2 * num_steps)
    
    N = num_steps
    for t in range(N):
        # 1. Power balance: Buy - Sell - Charge + Discharge = NetLoad
        rows.extend([t, t, t, t])
        cols.extend([t, N+t, 2*N+t, 3*N+t])
        data.extend([1.0, -1.0, -1.0, 1.0])
        b_eq[t] = net_load[t]
        
        # 2. SOC update: SOC[t] - Charge*eta + Discharge/eta - SOC[t-1] = 0
        rows.extend([N+t, N+t, N+t])
        cols.extend([4*N+t, 2*N+t, 3*N+t])
        data.extend([1.0, -eta_eff, 1.0/eta_eff])
        if t > 0:
            rows.append(N+t)
            cols.append(4*N+t-1)
            data.append(-1.0)
            
    A_eq = sp.csr_matrix((data, (rows, cols)), shape=(2*N, 5*N))
    
    res = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
    
    if not res.success:
        raise RuntimeError(f"Optimizer failed: {res.message}")
        
    x = res.x
    p_charge = x[2*N:3*N]
    p_discharge = x[3*N:4*N]
    soc = x[4*N:5*N]
    
    return p_charge, p_discharge, soc

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
        
        max_discharge_p = min(p_arb_kw, prev_soc * eta_eff)
        max_charge_p = min(p_arb_kw, (e_arb_kwh - prev_soc) / eta_eff)

        # 1. Price Arbitrage Charge (Buy low from grid or solar)
        if is_low[t]:
            p_charge[t] = max_charge_p
            soc[t+1] = prev_soc + (p_charge[t] * eta_eff)

        # 2. Price Arbitrage Export (Sell high AND cover load)
        elif is_high[t]:
            p_discharge[t] = max_discharge_p
            soc[t+1] = prev_soc - (p_discharge[t] / eta_eff)

        # 3. Neutral hours (Maximize Self-Consumption)
        else:
            if current_net < 0:
                # Excess solar -> Charge battery
                p_charge[t] = min(abs(current_net), max_charge_p)
                soc[t+1] = prev_soc + (p_charge[t] * eta_eff)
            elif current_net > 0:
                # House needs power -> Discharge to cover load ONLY
                p_discharge[t] = min(current_net, max_discharge_p)
                soc[t+1] = prev_soc - (p_discharge[t] / eta_eff)
            else:
                soc[t+1] = prev_soc
            
    # Return arrays of length num_steps (dropping initial SOC for alignment)
    return p_charge, p_discharge, soc[1:]
