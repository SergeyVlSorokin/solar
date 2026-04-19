import math
import numpy as np

def calculate_grid_limit(main_fuse_size_a: int) -> float:
    """
    Calculate the maximum power (kW) for a standard Swedish 3-phase 400V connection.
    Formula: P_grid_max = (main_fuse_size_a * 400 * sqrt(3)) / 1000
    """
    if not isinstance(main_fuse_size_a, int):
        raise TypeError(f"main_fuse_size_a must be an integer, got {type(main_fuse_size_a).__name__}")
    
    if main_fuse_size_a <= 0:
        raise ValueError(f"main_fuse_size_a must be positive, got {main_fuse_size_a}")
        
    if main_fuse_size_a > 1000:
        raise ValueError(f"main_fuse_size_a {main_fuse_size_a}A exceeds realistic residential limits (>1000A)")

    return (main_fuse_size_a * 400 * math.sqrt(3)) / 1000.0

def calculate_grid_flows(
    residual: np.ndarray, 
    p_grid_max: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Calculate Grid Buy, Grid Sell, Unmet Load, and Curtailed power flows.
    Residual(t) = Net(t) + P_charge(t) - P_discharge(t)
    
    Returns: (grid_buy, grid_sell, unmet_load, curtailed)
    """
    # 0. Defensive coercion and validation
    residual = np.asarray(residual)
    if p_grid_max is None or np.isnan(p_grid_max):
        p_grid_max = 0.0
    
    # 1. Split into positive (import) and negative (export) components
    residual_positive = np.maximum(0, residual)
    residual_negative_abs = np.maximum(0, -residual)
    
    # 2. Apply Grid Buy limits
    grid_buy = np.minimum(residual_positive, p_grid_max)
    unmet_load = np.maximum(0, residual_positive - p_grid_max)
    
    # 3. Apply Grid Sell (Export) limits
    grid_sell = np.minimum(residual_negative_abs, p_grid_max)
    curtailed = np.maximum(0, residual_negative_abs - p_grid_max)
    
    return grid_buy, grid_sell, unmet_load, curtailed
