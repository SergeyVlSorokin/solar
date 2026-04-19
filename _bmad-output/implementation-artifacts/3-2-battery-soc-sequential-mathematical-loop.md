# Story 3.2: Battery SOC Sequential Mathematical Loop

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Data Analyst,
I want the battery to sequentially iterate charge/discharge dynamics over exactly 8,760 hours based on Net Energy,
so that I can accurately calculate hour-by-hour physical arbitrage limits.

## Acceptance Criteria

1. **Given** the 1D numpy array `Net(t)` (`Load(t) - Solar(t)`) and the pre-calculated boundaries `P_arb`, `E_arb`, and `eta_rt`.
2. **When** the sequential timeline loop executes (`1 to 8760`).
3. **Then** it dynamically calculates instantaneous `P_charge(t)` and `P_discharge(t)` constrained strictly by available `SOC(t-1)` (FR8).
4. **And** it applies `eta_c` / `eta_d` explicitly during state calculations where `eta_c = eta_d = sqrt(eta_rt)`.
5. **And** it strictly clamps the resulting `SOC(t)` between `[0, E_arb]` bounds.
6. **And** returns the 1D arrays for `P_charge`, `P_discharge`, and `SOC` (analytical enhancement).

## Tasks / Subtasks

- [x] Task 1: Implement Sequential Loop in `src/solar/models/battery_logic.py` (AC: 1, 2, 3, 5)
  - [x] Implement `simulate_battery_loop(net_load, p_arb_kw, e_arb_kwh, eta_rt)` function.
  - [x] Enforce the `eta_c = eta_d = sqrt(eta_rt)` logic.
  - [x] Implement the branching logic for `Net(t) < 0` (charge) and `Net(t) > 0` (discharge).
  - [x] Ensure `SOC` is updated sequentially and clamped.
- [x] Task 2: Return Physical Flow Arrays (AC: 6)
  - [x] Ensure the function returns `p_charge_kw_array` and `p_discharge_kw_array`.
- [x] Task 3: Unit Testing for SOC Dynamics (AC: 3, 4, 5)
  - [x] Create `tests/models/test_battery_loop.py`.
  - [x] Test charging from empty to full.
  - [x] Test discharging from full to empty.
  - [x] Test round-trip efficiency losses (e.g. 10kWh in -> 9kWh usable if eta_rt=0.81).
- [x] Task 4: Integrate into Orchestration (AC: 1, 2)
  - [x] Update `src/solar/simulation.py` to invoke the loop after capacity allocation.

## Dev Notes

- **Architecture Compliance**:
  - The Battery Loop is the ONLY permitted sequential loop (PRD 3.2).
  - Must remain in `src/solar/models/battery_logic.py` as a pure function.
  - Keep the "Vector Boundary" rule for outputs (1D arrays).
- **Performance**:
  - Target < 100ms for 8,760 hours. Effectively tested with plain Python `for` loops meeting the performance SLA.
- **Library Requirements**: 
  - `numpy` for array handling.
- **Previous Story (3.1) Learnings**:
  - Use `AllocationResult` dataclass to pass parameters into the loop.
  - Ensure variable names include units (`_kw`, `_kwh`).
  - `eta_rt` was defined but unused in 3.1; it is critical here.

### Project Structure Notes

- Keep `battery_logic.py` focused on the physical state-of-charge math.
- Grid-level curtailment and fuse limits happen *after* this loop in Story 4.2.

### References

- Epic breakdown: [Source: _bmad-output/planning-artifacts/epics.md#Story 3.2: Battery SOC Sequential Mathematical Loop]
- Battery Model Requirements: [Source: docs/solar-prd.md#5.4. Battery & Energy Management Logic]
- Sequential Loop Exception: [Source: docs/solar-prd.md#3. System Architecture & MC Readiness Constraints]
- Battery Parameters: [Source: docs/solar-prd.md#4.3. Battery Parameters]

## Dev Agent Record

### Agent Model Used

Gemini 3 Flash

### Debug Log References

- [Tests Passed] `pytest tests/models/test_battery_loop.py` -> 5 passed.
- [Regressions Checked] `pytest` -> 24 passed (after minor update to `tests/test_simulation.py` for new columns).

### Completion Notes List

- Implemented `simulate_battery_loop` with sequential SOC tracking and efficiency handling.
- Integrated the loop into `src/solar/simulation.py` to accurately reflect battery arbitrage in grid flows.
- Updated `metrics` and `ts_df` output schema to include `battery_charged_kwh`, `battery_discharged_kwh`, and `battery_soc_kwh`.
- Verified round-trip efficiency logic ($\eta_c = \eta_d = \sqrt{\eta_{rt}}$) against PRD requirements.

### File List

- [MODIFY] `src/solar/models/battery_logic.py`
- [NEW] `tests/models/test_battery_loop.py`
- [MODIFY] `src/solar/simulation.py`
- [MODIFY] `tests/test_simulation.py`
