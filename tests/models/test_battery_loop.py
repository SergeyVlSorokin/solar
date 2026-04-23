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

def test_battery_loop_price_arbitrage():
    """Verify that battery charges low, covers house load neutrally, and dumps at peak."""
    # 24 hours of constant 1kW load
    net_load = np.ones(24)
    # 24 hours of prices: first 6 are cheap (10), middle are neutral (50), last 6 are peak (100)
    prices = np.full(24, 50.0)
    prices[0:6] = 10.0
    prices[18:24] = 100.0

    p_arb_kw = 5.0
    e_arb_kwh = 20.0 # Large enough to survive neutral hours and test peak dumping
    eta_rt = 1.0

    p_charge, p_discharge, soc = simulate_battery_loop(
        net_load, p_arb_kw, e_arb_kwh, eta_rt, spot_prices=prices
    )

    # Should charge in hours 0-3 (reaching 20kWh capacity) during is_low
    assert p_charge[0] == 5.0
    assert p_charge[3] == 5.0
    assert p_charge[4] == 0.0
    assert soc[4] == 20.0

    # Should discharge during neutral hours to cover house load (Load Displacement)
    assert p_discharge[6] == 1.0
    assert soc[6] == 19.0

    # After 12 neutral hours (hours 6-17), it has discharged 12kWh. SOC at hr 17 is 8.0kWh
    assert soc[17] == 8.0

    # Should discharge maximally during peak hours (hour 18)
    assert p_discharge[18] == 5.0
    assert soc[18] == 3.0
    assert p_discharge[19] == 3.0 # Only 3kWh left
    assert p_discharge[20] == 0.0 # Empty

def test_arbitrage_signals_robustness():
    """Verify that arbitrage signals handle edge cases (empty, small, partial days)."""
    from solar.models.battery_logic import get_arbitrage_signals
    
    # 1. Small input (<24h)
    prices = np.array([10.0, 50.0, 100.0])
    is_low, is_high = get_arbitrage_signals(prices, n_low=1, n_high=1)
    assert is_low.tolist() == [True, False, False]
    assert is_high.tolist() == [False, False, True]
    
    # 2. Empty input
    is_low_e, is_high_e = get_arbitrage_signals(np.array([]))
    assert len(is_low_e) == 0
    
    # 3. Exactly 24h
    prices_24 = np.arange(24)
    is_low_24, is_high_24 = get_arbitrage_signals(prices_24, n_low=1, n_high=1)
    assert is_low_24[0] == True
    assert is_high_24[23] == True
    assert np.sum(is_low_24) == 1
    
    # 4. 25h (Full day + 1h)
    prices_25 = np.zeros(25)
    prices_25[24] = 100.0 # High price in the "tail" hour
    is_low_25, is_high_25 = get_arbitrage_signals(prices_25, n_low=1, n_high=1)
    assert is_high_25[24] == True

def test_battery_loop_invalid_efficiency():
    """Verify that battery loop fails on zero or negative efficiency."""
    import pytest
    from solar.models.battery_logic import simulate_battery_loop
    
    with pytest.raises(ValueError, match="round_trip_efficiency"):
        simulate_battery_loop(np.zeros(10), 1.0, 1.0, 0.0)
