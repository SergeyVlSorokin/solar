import pytest
from solar.config import SimulationConfig

def test_simulation_config_has_main_fuse_size_a():
    config = SimulationConfig()
    # This should fail if Task 1 is not implemented
    assert hasattr(config, "main_fuse_size_a")
    assert config.main_fuse_size_a == 20

def test_simulation_config_custom_fuse():
    config = SimulationConfig(main_fuse_size_a=25)
    assert config.main_fuse_size_a == 25

def test_calculate_grid_limit_standard_values():
    from solar.models.grid_finance import calculate_grid_limit
    
    # 16A: (16 * 400 * sqrt(3)) / 1000 = 11.085125...
    assert calculate_grid_limit(16) == pytest.approx(11.0851, rel=1e-5)
    
    # 20A: (20 * 400 * sqrt(3)) / 1000 = 13.856406...
    assert calculate_grid_limit(20) == pytest.approx(13.8564, rel=1e-5)
    
    # 25A: (25 * 400 * sqrt(3)) / 1000 = 17.320508...
    assert calculate_grid_limit(25) == pytest.approx(17.3205, rel=1e-5)

def test_calculate_grid_limit_invalid_inputs():
    from solar.models.grid_finance import calculate_grid_limit
    
    with pytest.raises(TypeError, match="must be an integer"):
        calculate_grid_limit(20.5)
        
    with pytest.raises(ValueError, match="must be positive"):
        calculate_grid_limit(0)
        
    with pytest.raises(ValueError, match="exceeds realistic residential limits"):
        calculate_grid_limit(2000)
