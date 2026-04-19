import pytest
from solar.models.battery_logic import allocate_battery_capacity
from solar.config import BatteryConfig

def test_allocate_battery_capacity_normal():
    """Test allocation with 80% FCR split (PRD defaults)."""
    config = BatteryConfig(
        capacity_kwh=10.0,
        max_power_kw=5.0,
        round_trip_efficiency=0.90,
        fcr_allocation_pct=0.80
    )
    params = allocate_battery_capacity(config)
    
    # P_fcr = 5.0 * 0.8 = 4.0
    assert params.p_fcr_kw == pytest.approx(4.0)
    # P_arb = 5.0 - 4.0 = 1.0
    assert params.p_arb_kw == pytest.approx(1.0)
    # E_arb = 10.0 * (1 - 0.8) = 2.0
    assert params.e_arb_kwh == pytest.approx(2.0)

def test_allocate_battery_capacity_zero_fcr():
    """Test 100% arbitrage allocation."""
    config = BatteryConfig(
        capacity_kwh=10.0,
        max_power_kw=5.0,
        round_trip_efficiency=0.90,
        fcr_allocation_pct=0.0
    )
    params = allocate_battery_capacity(config)
    
    assert params.p_fcr_kw == 0.0
    assert params.p_arb_kw == 5.0
    assert params.e_arb_kwh == 10.0

def test_allocate_battery_capacity_full_fcr():
    """Test 100% FCR allocation."""
    config = BatteryConfig(
        capacity_kwh=10.0,
        max_power_kw=5.0,
        round_trip_efficiency=0.90,
        fcr_allocation_pct=1.0
    )
    params = allocate_battery_capacity(config)
    
    assert params.p_fcr_kw == 5.0
    assert params.p_arb_kw == 0.0
    assert params.e_arb_kwh == 0.0

def test_allocate_battery_capacity_validation_fail_low():
    """Test fail-fast on negative percentage."""
    config = BatteryConfig(
        capacity_kwh=10.0,
        max_power_kw=5.0,
        round_trip_efficiency=0.90,
        fcr_allocation_pct=-0.01
    )
    with pytest.raises(ValueError, match="fcr_allocation_pct must be strictly bounded"):
        allocate_battery_capacity(config)

def test_allocate_battery_capacity_validation_fail_high():
    """Test fail-fast on >100% percentage."""
    config = BatteryConfig(
        capacity_kwh=10.0,
        max_power_kw=5.0,
        round_trip_efficiency=0.90,
        fcr_allocation_pct=1.01
    )
    with pytest.raises(ValueError, match="fcr_allocation_pct must be strictly bounded"):
        allocate_battery_capacity(config)

def test_allocate_battery_capacity_validation_negative_power():
    """Test fail-fast on negative power."""
    config = BatteryConfig(
        capacity_kwh=10.0,
        max_power_kw=-5.0,
        round_trip_efficiency=0.90,
        fcr_allocation_pct=0.80
    )
    with pytest.raises(ValueError, match="max_power_kw must be non-negative"):
        allocate_battery_capacity(config)

def test_allocate_battery_capacity_validation_negative_capacity():
    """Test fail-fast on negative capacity."""
    config = BatteryConfig(
        capacity_kwh=-10.0,
        max_power_kw=5.0,
        round_trip_efficiency=0.90,
        fcr_allocation_pct=0.80
    )
    with pytest.raises(ValueError, match="capacity_kwh must be non-negative"):
        allocate_battery_capacity(config)
