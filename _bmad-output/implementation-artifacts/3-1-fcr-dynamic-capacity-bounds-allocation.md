# Story 3.1: FCR Dynamic Capacity Bounds Allocation

Status: done

## Story

As a Data Analyst,
I want the system to mathematically split the battery parameters into Virtual FCR and Virtual Arbitrage buckets prior to looping,
so that I don't simulate illegal battery market volumes or waste compute time on invalid parameters.

## Acceptance Criteria

1. **Given** the static parameter `fcr_allocation_pct` (`FCR_pct`) in the configuration
2. **When** the battery module is initialized or the simulation begins
3. **Then** it throws an immediate fail-fast `ValueError` if `FCR_pct < 0.0` or `FCR_pct > 1.0`
4. **And** it splits `max_power_kw` into `P_FCR` and `P_arb` constraints mathematically (FR5)
   - `P_FCR = P_max * FCR_pct`
   - `P_arb = P_max - P_FCR`
5. **And** it splits `capacity_kwh` into `E_arb` constraints dynamically.
   - `E_arb = E_max * (1 - FCR_pct)`
6. **And** it ensures these variables are available for the subsequent sequential loop but kept strictly separated.

## Tasks / Subtasks

- [x] Task 1: Update `src/solar/config.py` with Battery parameters
  - [x] Add `BatteryConfig` dataclass and move `battery_capacity_kwh` to it.
  - [x] Fields: `capacity_kwh`, `max_power_kw`, `round_trip_efficiency`, `fcr_allocation_pct`.
- [x] Task 2: Implement Allocation Logic in `src/solar/models/battery_logic.py`
  - [x] Implement validation for `fcr_allocation_pct` (ValueError on out-of-bounds).
  - [x] Implement the mathematical split of Power and Energy capacity per PRD 5.4.
  - [x] Ensure the function returns the split parameters as a dictionary.
- [x] Task 3: Add unit tests
  - [x] Create `tests/models/test_battery_logic.py`.
  - [x] Test valid and invalid `fcr_allocation_pct` boundaries.
  - [x] Verify correct math for splitting P and E across various percentages.
- [x] Task 4: Integrate into Orchestration
  - [x] Update `src/solar/simulation.py` to call the allocation logic before the loop.

## Dev Notes

- **Architecture Compliance**:
  - Keep the logic in a pure function in `src/solar/models/battery_logic.py`.
  - Do not use Pandas or iterative loops for this step (it's a scalar calculation).
  - Use the `SimulationConfig` dataclass for inputs.
- **Library Requirements**: Pure Python/Numpy.
- **Previous Story (2.1) Learnings**:
  - Maintain the "Vector Boundary" rule for any 1D arrays, though this story is primarily about scalar parameter initialization.
  - Follow the structural patterns established in `pv_generation.py` for input/output purity.
- **Fail-Fast**: The `ValueError` must be raised *before* any 8,760-hour arrays are processed to save compute.

## References

- Epic breakdown: [Source: _bmad-output/planning-artifacts/epics.md#Story 3.1: FCR Dynamic Capacity Bounds Allocation]
- Battery Model Requirements: [Source: docs/solar-prd.md#5.4. Battery & Energy Management Logic]
- Error Handling Patterns: [Source: _bmad-output/planning-artifacts/architecture.md#Process Patterns]
- Battery Parameters: [Source: docs/solar-prd.md#4.3. Battery Parameters]

## Dev Agent Record

### Agent Model Used

Gemini 3.1 Pro

### Debug Log References

- [Tests Passed] 9 tests total (5 new battery logic tests, 4 regression tests in simulation).
- [Environment Fix] Used absolute path to project-local conda python to run pytest.

### Completion Notes List

- Refactored `SimulationConfig` to include a nested `BatteryConfig` object.
- Implemented `allocate_battery_capacity` in `src/solar/models/battery_logic.py`.
- Integrated fail-fast `ValueError` for `fcr_allocation_pct`.
- Verified all mathematical splits against PRD formulas.
- Updated `docs/solar-prd.md` to version 1.1.

### File List

- [NEW] `src/solar/models/battery_logic.py`
- [NEW] `tests/models/test_battery_logic.py`
- [MODIFY] `src/solar/config.py`
- [MODIFY] `src/solar/simulation.py`
- [MODIFY] `tests/test_simulation.py`
- [MODIFY] `docs/solar-prd.md`

### Review Findings

#### Decision Needed
- [ ] [Review][Decision] Efficiency Usage — `round_trip_efficiency` is defined in `BatteryConfig` but unused. Should it be applied now (affecting reservation) or in the future loop (Story 3.2)?
- [ ] [Review][Decision] Implicit Units — Variable names like `p_fcr`, `p_arb`, and `e_arb` lack units. Should they be renamed to `p_fcr_kw`, `p_arb_kw`, `e_arb_kwh` for safety?
- [ ] [Review][Decision] Hardcoded Defaults — `SimulationConfig` battery defaults to `None`, but `BatteryConfig` has defaults. Should we remove defaults to force explicit config?
- [ ] [Review][Decision] PRD Context — Version 1.1 update dropped the "Deterministic Baseline" subtitle. Restore for context stability?

#### Patches
- [ ] [Review][Patch] Use Dataclass for Returns — Return a dedicated `AllocationResult` dataclass instead of a raw `dict`. [battery_logic.py:64]
- [ ] [Review][Patch] Utilize Allocation Results — `simulation.py` calculates `battery_params` but doesn't use it in any logic yet. [simulation.py:115]
- [ ] [Review][Patch] Add Physical Bounds Validation — Add non-negative checks for `max_power_kw` and `capacity_kwh`. [battery_logic.py:81]
- [ ] [Review][Patch] Precise Docstrings — Update documentation to reflect all implemented physical validations. [battery_logic.py:65]
- [ ] [Review][Patch] Deepen Simulation Metrics Tests — `test_simulation.py` misses verification of battery effects on financial metrics. [test_simulation.py:204]

