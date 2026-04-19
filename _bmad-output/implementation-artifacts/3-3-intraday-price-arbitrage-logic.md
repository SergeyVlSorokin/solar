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

## Implementation Plan Reference
[Implementation Plan](file:///c:/Users/Serge/.gemini/antigravity/brain/68a2dd66-6c1c-40a7-ba0a-7bfedd410fec/implementation_plan.md)

### Review Findings

#### Decision Needed
- [x] [Review][Decision] Solar Charge vs High Price Discharge — If current_net < 0 (excess solar) AND is_high[t] (peak price) is True, the code chooses to Charge (Priority 1). Resolved: Kept Solar Priority for realism.
- [x] [Review][Decision] Daily vs Global Arbitrage Strategy — Implementation picks the best hours per 24h block. Resolved: Kept Daily Strategy for realism and Nord Pool alignment.

#### Patch
- [x] [Review][Patch] Reshape Crash on Small Input [battery_logic.py:59] — Fixed.
- [x] [Review][Patch] Zero Efficiency Crash Guard [battery_logic.py:126] — Already handled.
- [x] [Review][Patch] Tail Data Price Signal Truncation [battery_logic.py:84] — Fixed.
- [x] [Review][Patch] Simulation Input Validation (spot_prices length) [simulation.py:90] — Fixed.

#### Defer
- [x] [Review][Defer] Array Allocation Inefficiency [battery_logic.py:59] — deferred, pre-existing
- [x] [Review][Defer] Hardcoded Defaults Consistency [battery_logic.py:54] — deferred, pre-existing
- [x] [Review][Defer] Priority Logic Maintainability Refactor [battery_logic.py:136] — deferred, pre-existing

