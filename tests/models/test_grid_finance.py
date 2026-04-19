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

def test_calculate_grid_flows():
    import numpy as np
    from solar.models.grid_finance import calculate_grid_flows
    
    # Residual = [5, 15, -5, -15, 0]
    # p_grid_max = 10
    residual = np.array([5.0, 15.0, -5.0, -15.0, 0.0])
    p_grid_max = 10.0
    
    gb, gs, ul, cr = calculate_grid_flows(residual, p_grid_max)
    
    # Expected:
    # 5.0 -> Buy 5, Sell 0, Unmet 0, Curt 0
    # 15.0 -> Buy 10, Sell 0, Unmet 5, Curt 0
    # -5.0 -> Buy 0, Sell 5, Unmet 0, Curt 0
    # -15.0 -> Buy 0, Sell 10, Unmet 0, Curt 5
    # 0.0 -> Buy 0, Sell 0, Unmet 0, Curt 0
    
    assert np.allclose(gb, [5, 10, 0, 0, 0])
    assert np.allclose(gs, [0, 0, 5, 10, 0])
    assert np.allclose(ul, [0, 5, 0, 0, 0])
    assert np.allclose(cr, [0, 0, 0, 5, 0])

def test_calculate_grid_flows_zero_limit():
    import numpy as np
    from solar.models.grid_finance import calculate_grid_flows
    
    residual = np.array([10.0, -10.0])
    p_grid_max = 0.0
    
    gb, gs, ul, cr = calculate_grid_flows(residual, p_grid_max)
    
    assert np.allclose(gb, [0, 0])
    assert np.allclose(gs, [0, 0])
    assert np.allclose(ul, [10, 0])
    assert np.allclose(cr, [0, 10])
