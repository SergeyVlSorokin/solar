import numpy as np
import pytest
from solar.models.battery_logic import simulate_battery_loop

def test_battery_loop_arbitrage():
    """Verify basic charge/discharge cycle with 100% efficiency."""
    # Hour 1: -10kW (Solar excess), Hour 2: +10kW (Load)
    net_load = np.array([-10.0, 10.0])
    p_arb_kw = 10.0
    e_arb_kwh = 10.0
    eta_rt = 1.0 # 100% efficiency
    
    p_charge, p_discharge, soc = simulate_battery_loop(net_load, p_arb_kw, e_arb_kwh, eta_rt)
    
    assert p_charge[0] == 10.0
    assert p_charge[1] == 0.0
    assert p_discharge[0] == 0.0
    assert p_discharge[1] == 10.0
    assert soc[0] == 10.0  # After hour 1
    assert soc[1] == 0.0   # After hour 2

def test_battery_loop_efficiency():
    """Verify that round-trip efficiency correctly impacts SOC and discharge power."""
    # 81% round-trip efficiency means eta_c = eta_d = 0.9
    net_load = np.array([-10.0, 10.0])
    p_arb_kw = 10.0
    e_arb_kwh = 10.0
    eta_rt = 0.81
    
    p_charge, p_discharge, soc = simulate_battery_loop(net_load, p_arb_kw, e_arb_kwh, eta_rt)
    
    # Hour 1: Charge
    # P_charge = 10kW. SOC gains 10kW * 0.9 = 9kWh
    assert p_charge[0] == 10.0
    assert soc[0] == 9.0
    
    # Hour 2: Discharge
    # Need 10kW. Max discharge from 9kWh SOC is 9 * 0.9 = 8.1kW
    assert p_discharge[1] == pytest.approx(8.1)
    assert soc[1] == 0.0

def test_battery_loop_power_limits():
    """Verify that charge/discharge is capped by p_arb_kw."""
    net_load = np.array([-100.0, 100.0])
    p_arb_kw = 5.0
    e_arb_kwh = 50.0
    eta_rt = 1.0
    
    p_charge, p_discharge, soc = simulate_battery_loop(net_load, p_arb_kw, e_arb_kwh, eta_rt)
    
    assert p_charge[0] == 5.0
    assert p_discharge[1] == 5.0
    assert soc[0] == 5.0

def test_battery_loop_capacity_limits():
    """Verify that charge stops when battery is full and discharge stops when empty."""
    # Charge 100kW into 10kWh battery
    net_load = np.array([-100.0, 100.0])
    p_arb_kw = 100.0
    e_arb_kwh = 10.0
    eta_rt = 1.0
    
    p_charge, p_discharge, soc = simulate_battery_loop(net_load, p_arb_kw, e_arb_kwh, eta_rt)
    
    # Hour 1: Charge
    # P_charge = min(100, 100, (10-0)/1) = 10.0
    assert p_charge[0] == 10.0
    assert soc[0] == 10.0
    
    # Hour 2: Discharge
    # P_discharge = min(100, 100, 10*1) = 10.0
    assert p_discharge[1] == 10.0
    assert soc[1] == 0.0

def test_battery_loop_soc_persistence():
    """Verify that SOC persists correctly across steps."""
    net_load = np.array([-2.0, -2.0, -2.0])
    p_arb_kw = 10.0
    e_arb_kwh = 10.0
    eta_rt = 1.0
    
    _, _, soc = simulate_battery_loop(net_load, p_arb_kw, e_arb_kwh, eta_rt)
    
    assert soc[0] == 2.0
    assert soc[1] == 4.0
    assert soc[2] == 6.0

def test_battery_loop_invalid_inputs():
    """Verify that invalid inputs raise ValueError."""
    net_load = np.array([10.0])
    
    # Efficiency out of bounds
    with pytest.raises(ValueError, match="round_trip_efficiency"):
        simulate_battery_loop(net_load, 10.0, 10.0, 0.0)
    
    with pytest.raises(ValueError, match="round_trip_efficiency"):
        simulate_battery_loop(net_load, 10.0, 10.0, 1.1)
        
    # Negative capacity
    with pytest.raises(ValueError, match="e_arb_kwh"):
        simulate_battery_loop(net_load, 10.0, -1.0, 0.8)

def test_battery_loop_zero_net_load():
    """Verify handling of neutral net load."""
    net_load = np.array([0.0])
    p_arb_kw = 10.0
    e_arb_kwh = 10.0
    eta_rt = 0.8
    
    p_charge, p_discharge, soc = simulate_battery_loop(net_load, p_arb_kw, e_arb_kwh, eta_rt)
    
    assert p_charge[0] == 0.0
    assert p_discharge[0] == 0.0
    assert soc[0] == 0.0
