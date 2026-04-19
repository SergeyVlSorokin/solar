# Acceptance Auditor Review Prompt

You are an **Acceptance Auditor**. Review this diff against the spec and context docs provided below. 

## Check For
1. **Violations of Acceptance Criteria**: Does it do what the AC says?
2. **Deviations from Spec Intent**: Does it follow the strategy described?
3. **Missing Implementation**: Is something in the spec not in the code?
4. **Physical Constraints**: Does it obey p_arb, e_arb, and eta_rt?

## Expected Output
Output your findings as a Markdown list. Each finding must include:
- A one-line title.
- Which AC or constraint it violates.
- Evidence from the diff.

## Spec: Story 3.3
```markdown
# Story 3.3: Intraday Price Arbitrage Logic

## Status: `done`

## Context
The current battery simulation logic (Story 3.2) only handles self-consumption (charging from excess solar). In winter months or high-price periods, the battery remains underutilized because it cannot charge from the grid. This story implements price-driven arbitrage to allow the battery to buy energy when it is cheap and sell/displace load when it is expensive.

## Requirements
- **Price Sensitivity**: The battery loop must accept Nord Pool spot prices as an input.
- **Daily Strategy**: For each 24-hour day, identify the $N$ cheapest hours for charging and $M$ most expensive hours for discharging.
- **Solar Priority**: Physical availability of excess solar (`net_load < 0`) always takes precedence over price-driven grid charging to ensure maximum zero-marginal-cost energy utilization.
- **Efficiency**: Maintain the 100ms SLA by using vectorized pre-calculation for price rankings outside the sequential loop.

## Acceptance Criteria
- **Given** accurate 8,760 hourly spot prices.
- **When** the simulation runs for a winter day (e.g., Dec 30).
- **Then** the battery shows charging activity during the cheapest night hours.
- **And** the battery shows discharging activity during the morning/evening price peaks.
- **And** all physical constraints (`p_arb`, `e_arb`, `eta_rt`) are strictly respected.
```

## Diff to Review
```diff
+++ b/_bmad-output/implementation-artifacts/sprint-status.yaml
@@ -53,6 +53,7 @@ development_status:
   epic-3: done
   3-1-fcr-dynamic-capacity-bounds-allocation: done
   3-2-battery-soc-sequential-mathematical-loop: done
+  3-3-intraday-price-arbitrage-logic: done
   epic-3-retrospective: optional
   epic-4: in-progress
   4-1-main-fuse-transmission-limits: done
diff --git a/_bmad-output/planning-artifacts/epics.md b/_bmad-output/planning-artifacts/epics.md
index 8fa44cb..7d76d6b 100644
--- a/_bmad-output/planning-artifacts/epics.md
+++ b/_bmad-output/planning-artifacts/epics.md
@@ -180,6 +180,22 @@ So that I can accurately calculate hour-by-hour physical arbitrage limits.
 **And** it strictly clamps the resulting `SOC(t)` between `[0, E_arb]` bounds
 **And** returns purely the 1D arrays for `P_charge` and `P_discharge`.
 
+### Story 3.3: Intraday Price Arbitrage Logic
+
+As a Data Analyst,
+I want the battery to charge from the grid during cheap hours and discharge during expensive hours,
+So that I can model realistic intraday arbitrage economics beyond simple solar self-consumption.
+
+**Acceptance Criteria:**
+
+**Given** the 1D numpy array `spot_prices` and the pre-calculated boundaries `P_arb`, `E_arb`
+**When** the sequential timeline loop executes
+**Then** it identifies the $N$ cheapest hours of each day (e.g., 6 hours) to permit Grid-to-Battery charging
+**And** it identifies the $M$ most expensive hours of each day (e.g., 6 hours) to prioritize discharging
+**And** it maintains "Solar Priority" (excess solar always charges the battery regardless of price)
+**And** it strictly obeys physical inverter power and energy capacity limits
+**And** returns the updated `P_charge` and `P_discharge` vectors including arbitrage flows.
+
 ## Epic 4: Grid Fuses & Curtailment Constraints
 
 Enforce maximum grid transmission limits based on the property's main fuse (Amperes), mathematically guaranteeing that excess solar is properly curtailed if the battery is full and the fuse is maxed.
diff --git a/src/solar/models/battery_logic.py b/src/solar/models/battery_logic.py
index df55a4a..435fae0 100644
--- a/src/solar/models/battery_logic.py
+++ b/src/solar/models/battery_logic.py
@@ -1,6 +1,6 @@
 import numpy as np
 from dataclasses import dataclass
-from typing import Tuple
+from typing import Tuple, Optional
 from solar.config import BatteryConfig
 
 @dataclass
@@ -51,11 +51,46 @@ def allocate_battery_capacity(config: BatteryConfig) -> AllocationResult:
         e_arb_kwh=e_arb_kwh
     )
 
+def get_arbitrage_signals(prices: np.ndarray, n_low: int = 6, n_high: int = 6) -> Tuple[np.ndarray, np.ndarray]:
+    """
+    Identifies the n_low cheapest and n_high most expensive hours for EACH 24h window.
+    Returns two boolean masks of the same length as prices.
+    """
+    num_steps = len(prices)
+    num_days = num_steps // 24
+    
+    # We only operate on full days for the ranking. 
+    # Remaining hours (if any) will have False signals.
+    full_day_prices = prices[:num_days*24].reshape((num_days, 24))
+    
+    # Get argument sorts per day (axis 1)
+    sorted_idx = np.argsort(full_day_prices, axis=1)
+    
+    # Create masks
+    is_low_2d = np.zeros((num_days, 24), dtype=bool)
+    is_high_2d = np.zeros((num_days, 24), dtype=bool)
+    
+    # Row-wise indexing to set True
+    rows = np.arange(num_days)[:, None]
+    is_low_2d[rows, sorted_idx[:, :n_low]] = True
+    is_high_2d[rows, sorted_idx[:, -n_high:]] = True
+    
+    # Flatten and pad if needed
+    is_low = np.zeros(num_steps, dtype=bool)
+    is_high = np.zeros(num_steps, dtype=bool)
+    is_low[:num_days*24] = is_low_2d.flatten()
+    is_high[:num_days*24] = is_high_2d.flatten()
+    
+    return is_low, is_high
+
 def simulate_battery_loop(
     net_load: np.ndarray,
     p_arb_kw: float,
     e_arb_kwh: float,
-    eta_rt: float
+    eta_rt: float,
+    spot_prices: Optional[np.ndarray] = None,
+    n_charge_hours: int = 6,
+    n_discharge_hours: int = 6
 ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
     """
     Sequential battery state-of-charge simulation loop (PRD 5.4).
@@ -79,6 +114,16 @@ def simulate_battery_loop(
         raise ValueError(f"e_arb_kwh must be non-negative; got {e_arb_kwh}")
 
     num_steps = len(net_load)
+
+    # 2. Arbitrage Signal Pre-calculation
+    # If prices are provided, we enable price-driven arbitrage.
+    # Otherwise, we default to pure self-consumption (no price signals).
+    is_low = np.zeros(num_steps, dtype=bool)
+    is_high = np.zeros(num_steps, dtype=bool)
+    if spot_prices is not None:
+        is_low, is_high = get_arbitrage_signals(spot_prices, n_low=n_charge_hours, n_high=n_discharge_hours)
+
+    # 3. State Initialization
     p_charge = np.zeros(num_steps)
     p_discharge = np.zeros(num_steps)
     soc = np.zeros(num_steps + 1)  # Including t=0
@@ -91,14 +136,22 @@ def simulate_battery_loop(
         current_net = net_load[t]
         prev_soc = soc[t]
         
-        if current_net < 0:  # Excess Solar (Charge)
-            # P_charge(t) = min(abs(Net(t)), P_arb, (E_arb - SOC(t-1)) / eta_c)
+        # Priority 1: Solar Self-Consumption (Charge if excess solar)
+        if current_net < 0:
             p_charge[t] = min(abs(current_net), p_arb_kw, (e_arb_kwh - prev_soc) / eta_eff)
             soc[t+1] = prev_soc + (p_charge[t] * eta_eff)
             
-        elif current_net > 0:  # Need Power (Discharge)
-            # P_discharge(t) = min(Net(t), P_arb, SOC(t-1) * eta_d)
-            p_discharge[t] = min(current_net, p_arb_kw, prev_soc * eta_eff)
+        # Priority 2: Price Arbitrage (Charge if price is low, even if net_load > 0)
+        elif is_low[t]:
+            # Note: We still honor p_arb_kw and e_arb_kwh
+            p_charge[t] = min(p_arb_kw, (e_arb_kwh - prev_soc) / eta_eff)
+            soc[t+1] = prev_soc + (p_charge[t] * eta_eff)
+            
+        # Priority 3: Displacement/Discharge (Need power OR price is high)
+        elif current_net > 0 or is_high[t]:
+            # P_discharge targets either the load or max battery power
+            target_discharge = current_net if (current_net > 0 and not is_high[t]) else p_arb_kw
+            p_discharge[t] = min(target_discharge, p_arb_kw, prev_soc * eta_eff)
             soc[t+1] = prev_soc - (p_discharge[t] / eta_eff)
             
         else:  # Neutral
diff --git a/src/solar/simulation.py b/src/solar/simulation.py
index bb916f8..c1cd88e 100644
--- a/src/solar/simulation.py
+++ b/src/solar/simulation.py
@@ -87,7 +87,8 @@ def run_simulation(config: SimulationConfig, parquet_dir: str, year: str = "2025
             net_load=net_load,
             p_arb_kw=battery_allocation.p_arb_kw,
             e_arb_kwh=battery_allocation.e_arb_kwh,
-            eta_rt=config.battery.round_trip_efficiency
+            eta_rt=config.battery.round_trip_efficiency,
+            spot_prices=spot_prices
         )
 
     # 4. Grid Balancing
diff --git a/tests/models/test_battery_loop.py b/tests/models/test_battery_loop.py
index eb1753e..8eec9c3 100644
--- a/tests/models/test_battery_loop.py
+++ b/tests/models/test_battery_loop.py
@@ -112,3 +112,29 @@ def test_battery_loop_zero_net_load():
     assert p_charge[0] == 0.0
     assert p_discharge[0] == 0.0
     assert soc[0] == 0.0
+
+def test_battery_loop_price_arbitrage():
+    """Verify that battery charges during low prices even if net_load > 0."""
+    # 24 hours of constant 1kW load
+    net_load = np.ones(24)
+    # 24 hours of prices: first 6 are 10, others are 100
+    prices = np.full(24, 100.0)
+    prices[0:6] = 10.0
+    
+    p_arb_kw = 5.0
+    e_arb_kwh = 10.0
+    eta_rt = 1.0
+    
+    p_charge, p_discharge, soc = simulate_battery_loop(
+        net_load, p_arb_kw, e_arb_kwh, eta_rt, spot_prices=prices
+    )
+    
+    # Should charge in hour 0, 1 (reaching 10kWh capacity)
+    assert p_charge[0] == 5.0
+    assert p_charge[1] == 5.0
+    assert p_charge[2] == 0.0
+    assert soc[1] == 10.0
+    
+    # Should discharge in hour 6 (first hour not low-price, with load > 0)
+    assert p_discharge[6] == 1.0
+    assert soc[6] == 9.0
```
