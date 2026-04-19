# Story 5.2: Skattereduktion Tax Rebate Dynamic Capping

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Data Analyst,
I want to calculate the correct Skattereduktion tax credit rebate limit,
so that I model Swedish operational savings legally without accidentally over-inflating my solar returns.

## Acceptance Criteria

1. **Given** the globally summed yearly totals for Grid Buy and Grid Sell.
2. **When** the Financial post-loop summary calculation executes.
3. **Then** it bounds the max creditable electricity via `Max_tax_kwh = min(sum(Grid_sell), sum(Grid_buy), 30000)` ensuring no more than 30k kWh or actual-purchased kWh is credited (FR10).
4. **And** applies the `0.60 SEK` multiplier (from `config.tax_credit_rate`) to calculate `Total_tax_credit_sek`.
5. **And** compiles these summaries, including the `aggregator_flat_fee_yearly`, to yield the final `net_electricity_cost_sek` scalar.

## Tasks / Subtasks

- [x] **Task 1: Modularize Yearly Financial Summary**
    - [x] Create `calculate_yearly_metrics` in `src/solar/models/grid_finance.py`.
    - [x] Move the tax credit and net cost calculation logic from `simulation.py` to this new pure function.
    - [x] Ensure the function accepts scalars (totals) and configuration parameters.
- [x] **Task 2: Refactor Orchestration**
    - [x] Update `src/solar/simulation.py` to call `calculate_yearly_metrics`.
    - [x] Ensure all required fields are passed to the metrics dictionary.
- [x] **Task 3: Unit Testing for Tax Capping**
    - [x] Create `tests/models/test_tax_logic.py` (or update `test_grid_finance.py`).
    - [x] Test scenarios: 
        - [x] Sell < Buy < 30k (Capped by Sell).
        - [x] Buy < Sell < 30k (Capped by Buy).
        - [x] Both > 30k (Capped by 30k).
        - [x] Buy = 0 (Total tax credit should be 0).

## Dev Notes

- **Architecture Compliance**:
  - **Pure Functions**: The tax logic must be a pure function in `grid_finance.py`.
  - **Statelessness**: Do not store state; calculate everything from the passed yearly totals.
- **Physics/Tax Logic**:
  - `max_tax_kwh = min(total_grid_sell_kwh, total_grid_buy_kwh, 30000.0)`
  - `total_tax_credit_sek = max_tax_kwh * config.tax_credit_rate`
  - `net_cost = total_spend - (total_earn_spot + total_earn_fcr + total_tax_credit_sek) + flat_fee`
- **Configuration**:
  - Use `config.tax_credit_rate` (default in PRD is 0.60).
  - Use `config.aggregator_flat_fee_yearly`.

### Project Structure Notes

- Logic currently lives in `src/solar/simulation.py` (lines 136-161). It should be extracted to `grid_finance.py` to match the architectural pattern of modular physics/finance functions.

### References

- **Epic Breakdown**: [epics.md:L248-261](file:///c:/Users/Serge/source/solar/_bmad-output/planning-artifacts/epics.md#L248-261)
- **Architecture Guardrails**: [architecture.md:L178-185](file:///c:/Users/Serge/source/solar/_bmad-output/planning-artifacts/architecture.md#L178-185)
- **Previous Story**: [5-1-spot-market-and-aggregator-revenue-arrays.md](file:///c:/Users/Serge/source/solar/_bmad-output/implementation-artifacts/5-1-spot-market-and-aggregator-revenue-arrays.md)

## Dev Agent Record

### Agent Model Used

Gemini 3 Flash

### Completion Notes List

- (To be filled by Dev Agent)

### File List

- [MODIFY] `src/solar/simulation.py`
- [NEW] `tests/models/test_tax_logic.py`

### Review Findings

- [ ] [Review][Decision] "Subtract" vs "Add" Fee Conflict — AC 19 says "subtracting" the fee, while code does `+ aggregator_flat_fee_yearly`. Logically `Spend - Revenue + Fee` is correct for cost, but the spec wording is ambiguous.
- [ ] [Review][Patch] Hardcoded 30,000 kWh Limit [src/solar/models/grid_finance.py:29]
- [ ] [Review][Patch] Redundant Float Casting [src/solar/models/grid_finance.py:40-46]
- [ ] [Review][Patch] Inefficient Dictionary Mapping [src/solar/simulation.py:100-109]
- [ ] [Review][Patch] Missing Docstring Types [src/solar/models/grid_finance.py:10-18]
- [ ] [Review][Patch] Negative Grid Buy/Sell Guards [src/solar/models/grid_finance.py:29]
- [ ] [Review][Patch] Negative Tax Credit Rate Guard [src/solar/models/grid_finance.py:30]
- [ ] [Review][Patch] NaN Handling in Sums [src/solar/models/grid_finance.py:29]
