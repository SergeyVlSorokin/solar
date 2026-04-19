# Story 4.1: Main Fuse Transmission Limits

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Data Analyst,
I want the system to calculate physical main fuse transmission limits based on Ampere inputs,
so that the simulation obeys safety fuses and grid operator connection agreements.

## Acceptance Criteria

1. **Given** the `main_fuse_size_a` standard parameter (Default: 20 per PRD).
2. **When** the grid module initializes before simulation.
3. **Then** it calculates $P_{grid\_max} = (main\_fuse\_size\_a \times 400 \times \sqrt{3}) \div 1000$ specifically for 3-phase 400V grids (FR6).
4. **And** strictly saves it as the static maximum transmission limit constraint for the simulation.

## Tasks / Subtasks

- [x] **Task 1: Update Configuration to include Grid Parameters**
    - [x] Add `main_fuse_size_a: int = 20` to `src/solar/config.py`.
    - [x] (Optional) Group grid parameters if more are expected, following the `BatteryConfig` pattern.
- [x] **Task 2: Implement Grid Logic Module**
    - [x] Create `src/solar/models/grid_finance.py`.
    - [x] Implement `calculate_grid_limit(fuse_size_a: int) -> float` as a pure function.
- [x] **Task 3: Integrate into Orchestration**
    - [x] Update `src/solar/simulation.py` to calculate `p_grid_max` during the initialization/parameter phase.
- [x] **Task 4: Unit Testing for Grid Limits**
    - [x] Create `tests/models/test_grid_finance.py`.
    - [x] Verify standard Swedish fuse values (16A $\approx$ 11.08 kW, 20A $\approx$ 13.85 kW, 25A $\approx$ 17.32 kW).

## Dev Notes

- **Architecture Compliance**:
  - Purity: Logic must be in `src/solar/models/grid_finance.py` as a pure stateless function.
  - Performance: Calculation is a scalar and should be extremely fast.
  - Pattern: Consistent with Epic 4's goal of enforcing transmission limits.
- **Library Requirements**: 
  - `math.sqrt` or `numpy.sqrt` for the 3-phase calculation.
- **Previous Story Learnings**:
  - Integration in `simulation.py` should happen before any flow calculations to ensure the limit is available for both Battery and Grid modules.
  - In Story 3.2, we established the `soc_kwh` sequential loop; Story 4.1 sets the physical stage for the curtailment logic in 4.2.

### Project Structure Notes

- `src/solar/models/grid_finance.py` will eventually house both transmission limits (Epic 4) and Swedish tax/revenue math (Epic 5).

### References

- Epic Breakdown: [epics.md:L187-199](file:///c:/Users/Serge/source/solar/_bmad-output/planning-artifacts/epics.md#L187-199)
- Grid Requirements: [solar-prd.md:L99-103](file:///c:/Users/Serge/source/solar/docs/solar-prd.md#L99-103)
- Architecture Guardrails: [architecture.md:L156-160](file:///c:/Users/Serge/source/solar/_bmad-output/planning-artifacts/architecture.md#L156-160)

## Dev Agent Record

### Agent Model Used

Gemini 3 Flash

### Debug Log References

- [Tests Passed] `C:\Users\Serge\anaconda3\python.exe -m pytest tests/models/test_grid_finance.py` -> 3 passed.
- [Regressions Checked] `C:\Users\Serge\anaconda3\python.exe -m pytest` -> 29 passed.

### Completion Notes List

- Updated `SimulationConfig` to include `main_fuse_size_a` (Default: 20A).
- Created `src/solar/models/grid_finance.py` with `calculate_grid_limit` based on the 3-phase 400V formula.
- Integrated `p_grid_max_kw` calculation into `run_simulation` and added it to the global metrics output.
- Verified calculations for standard fuse sizes (16A, 20A, 25A) via unit tests.

### File List

- [MODIFY] `src/solar/config.py`
- [MODIFY] `src/solar/simulation.py`
- [NEW] `src/solar/models/grid_finance.py`
- [NEW] `tests/models/test_grid_finance.py`
- [MODIFY] `tests/test_simulation.py`

### Review Findings

- [x] [Review][Decision] Results Dict Visibility — `p_grid_max_kw` is added to results. Should this be visible to the user or internal?
- [x] [Review][Patch] Redundant float cast [src/solar/models/grid_finance.py:12]
- [x] [Review][Patch] Overkill numpy dependency [src/solar/models/grid_finance.py:1]
- [x] [Review][Patch] Missing upper bound on fuse size [src/solar/models/grid_finance.py:6]
- [x] [Review][Patch] Missing type validation for fuse_size_a [src/solar/models/grid_finance.py:3]
- [x] [Review][Patch] Inconsistent parameter naming [src/solar/config.py]
- [x] [Review][Patch] Loose test precision [tests/models/test_grid_finance.py]
- [x] [Review][Patch] Integration placement [src/solar/simulation.py:77]
- [x] [Review][Defer] Hardcoded 400V grid voltage [src/solar/models/grid_finance.py:11] — deferred, pre-existing (specified in FR6).
