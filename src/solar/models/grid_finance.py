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

def calculate_financials(
    grid_buy: np.ndarray,
    grid_sell: np.ndarray,
    p_fcr_kw: float,
    price_spot_hourly: np.ndarray,
    price_fcr_hourly: np.ndarray,
    grid_transfer_fee_sek: float,
    energy_tax_sek: float,
    vat_rate: float,
    utility_sell_compensation: float,
    aggregator_fee_pct: float
) -> dict[str, np.ndarray]:
    """
    Calculate hourly financial flows (SEK).
    
    Formulas:
    Spend(t) = Grid_buy(t) * ((price_spot + transfer + tax) * (1 + vat))
    Earn_spot(t) = Grid_sell(t) * (price_spot + utility_compensation)
    Rev_FCR(t) = (P_FCR / 1000) * price_fcr_hourly(t) * (1 - aggregator_fee_pct)
    """
    # Ensure inputs are numpy arrays
    grid_buy = np.asarray(grid_buy)
    grid_sell = np.asarray(grid_sell)
    price_spot_hourly = np.asarray(price_spot_hourly)
    price_fcr_hourly = np.asarray(price_fcr_hourly)

    # 0. Defensive Validation
    if not (grid_buy.shape == grid_sell.shape == price_spot_hourly.shape == price_fcr_hourly.shape):
        raise ValueError("All input arrays (grid_buy, grid_sell, price_spot, price_fcr) must have the same shape.")

    if not 0 <= aggregator_fee_pct <= 1:
        raise ValueError(f"aggregator_fee_pct must be between 0 and 1, got {aggregator_fee_pct}")

    # 1. Hourly Spend (VAT-inclusive)
    # Wrap in np.maximum(0, ...) to prevent negative costs per user request
    energy_stack = np.maximum(0, price_spot_hourly + grid_transfer_fee_sek + energy_tax_sek)
    hourly_spend = grid_buy * (energy_stack * (1 + vat_rate))

    # 2. Hourly Earn Spot
    # Wrap utility compensation stack in np.maximum(0, ...)
    combined_sell_price = np.maximum(0, price_spot_hourly + utility_sell_compensation)
    hourly_earn_spot = grid_sell * combined_sell_price

    # 3. Hourly FCR Revenue
    # Convert p_fcr_kw to MW (division by 1000) to match price scale (SEK/MW/h)
    fcr_mw = p_fcr_kw / 1000.0
    hourly_revenue_fcr = fcr_mw * price_fcr_hourly * (1 - aggregator_fee_pct)

    return {
        "hourly_spend": hourly_spend,
        "hourly_earn_spot": hourly_earn_spot,
        "hourly_revenue_fcr": hourly_revenue_fcr
    }
