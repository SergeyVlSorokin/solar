# Story 4.2: Grid Flow & Curtailment Vector Truncation

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Data Analyst,
I want to resolve the exact Grid Buy, Grid Sell, and Curtailment limits using fast vectorized logic,
so that I know how much power actually reached the meter.

## Acceptance Criteria

1. **Given** the complete array `Residual(t) = Net(t) + P_charge(t) - P_discharge(t)` resulting from the Battery loop, and the pre-calculated `P_grid_max`.
2. **When** the post-loop Grid module executes.
3. **Then** it calculates flow via parallel Numpy vector masking (avoiding Pandas/Loops or Numba).
4. **And** where `Residual(t) > 0`, restricts `Grid_buy(t)` to `P_grid_max` and logs the remainder as `Unmet_load(t)`.
5. **And** where `Residual(t) < 0`, restricts `Grid_sell(t)` to `P_grid_max` and isolates the remainder mathematically as `Curtailed(t)` (FR7).

## Tasks / Subtasks

- [x] **Task 1: Implement Grid Flow Logic in Models** (AC: 1, 2, 3)
    - [x] Add `calculate_grid_flows(residual: np.ndarray, p_grid_max: float) -> Tuple[np.ndarray, ...]` to `src/solar/models/grid_finance.py`.
    - [x] Ensure the function returns four arrays: `grid_buy`, `grid_sell`, `unmet_load`, and `curtailed`.
    - [x] Use strictly vectorized Numpy operations (no loops).
- [x] **Task 2: Integrate into Orchestration** (AC: 4, 5)
    - [x] Update `src/solar/simulation.py` to replace the placeholder grid balancing with `calculate_grid_flows`.
    - [x] Map the results to the financial Spend/Earn calculations.
    - [x] Update `metrics` dictionary to include `total_unmet_load_kwh` and `total_curtailed_kwh`.
    - [x] Update `ts_df` (if `return_timeseries` is True) to include `unmet_load` and `curtailed` columns.
- [x] **Task 3: Unit Testing for Grid Flows**
    - [x] Update `tests/models/test_grid_finance.py` with scenarios:
        - [x] Residual within limits (no truncation).
        - [x] Residual exceeding `P_grid_max` (positive and negative).
        - [x] Edge case: `P_grid_max` is zero (should result in full unmet load / curtailment).
- [x] **Task 4: Integration Testing**
    - [x] Verify `tests/test_simulation.py` to ensure the end-to-year metrics correctly reflect these new flows.

### Review Findings

- [x] [Review][Patch] Defensive Array Coercion: `calculate_grid_flows` should coerce `residual` to a numpy array to ensure vectorization performance and type consistency. [grid_finance.py:21]
- [x] [Review][Patch] Guard against invalid `p_grid_max`: Ensure `p_grid_max` is treatable as float and non-null to prevent propagation of `TypeError` or `NaN` in mathematical ops. [grid_finance.py:36]
- [x] [Review][Patch] Modern type hinting: Use `tuple` instead of `Tuple` for return type hinting in Python 3.10. [grid_finance.py:2]

## Dev Notes

- **Architecture Compliance**:
  - **The Vector Boundary Rule**: All inputs to `calculate_grid_flows` must be 1D Numpy arrays.
  - **Pure Functions**: Ensure `calculate_grid_flows` does not mutate the input `residual` array.
- **Physics Logic**:
  - `Residual(t) = Net(t) + P_charge(t) - P_discharge(t)`
  - `grid_buy = np.minimum(np.maximum(0, residual), p_grid_max)`
  - `unmet_load = np.maximum(0, np.maximum(0, residual) - p_grid_max)`
  - `grid_sell = np.minimum(np.maximum(0, -residual), p_grid_max)`
  - `curtailed = np.maximum(0, np.maximum(0, -residual) - p_grid_max)`
- **Dependencies**:
  - Requires `numpy` in `src/solar/models/grid_finance.py`. (Note: Story 4.1 review recommended removing overkill numpy, but here it is required for vectorization).

### Project Structure Notes

- `src/solar/models/grid_finance.py` currently only has `calculate_grid_limit`.
- `src/solar/simulation.py`: The placeholder at line 94-98 should be removed.

### References

- **Epic Breakdown**: [epics.md:L200-212](file:///c:/Users/Serge/source/solar/_bmad-output/planning-artifacts/epics.md#L200-212)
- **Architecture Guardrails**: [architecture.md:L196-211](file:///c:/Users/Serge/source/solar/_bmad-output/planning-artifacts/architecture.md#L196-211)
- **Previous Story**: [4-1-main-fuse-transmission-limits.md](file:///c:/Users/Serge/source/solar/_bmad-output/implementation-artifacts/4-1-main-fuse-transmission-limits.md)

## Dev Agent Record

### Agent Model Used

Gemini 3 Flash

### Debug Log References

- [Tests Passed] `.\.conda\Scripts\pytest.exe tests/models/test_grid_finance.py -v` -> 6 passed.
- [Regressions Checked] `.\.conda\Scripts\pytest.exe -v` -> 32 passed.

### Completion Notes List

- Implemented `calculate_grid_flows` in `src/solar/models/grid_finance.py` using vectorized Numpy masking to handle 8,760-hour arrays.
- Integrated the flow calculation into `run_simulation` in `src/solar/simulation.py`, replacing the previous naive grid balancing.
- Added `total_unmet_load_kwh` and `total_curtailed_kwh` to the summary metrics.
- Updated the timeseries output (`ts_df`) to include `unmet_load` and `curtailed` columns for detailed visual analysis.
- Verified physical constraint enforcement via unit tests for standard and zero-limit scenarios.
- Ensured architecture compliance: No Pandas used in model logic, stateless purity maintained.

### File List

- [MODIFY] `src/solar/models/grid_finance.py`
- [MODIFY] `src/solar/simulation.py`
- [MODIFY] `tests/models/test_grid_finance.py`
- [MODIFY] `tests/test_simulation.py`
