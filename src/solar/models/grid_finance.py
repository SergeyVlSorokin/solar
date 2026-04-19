import math

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
