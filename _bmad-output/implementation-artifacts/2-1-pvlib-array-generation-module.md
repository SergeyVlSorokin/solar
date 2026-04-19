# Story 2.1: Pvlib Array Generation Module

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Data Analyst,
I want to convert weather irradiance arrays into a standardized Solar Power array via `pvlib`,
so that I can model the physical output of complex, multi-sided roofs.

## Acceptance Criteria

1. **Given** localized weather GHI/DNI 1D arrays and a list of configuration dictionaries representing N solar strings
2. **When** the `src/solar/models/pv_generation.py` function is invoked
3. **Then** it iterates through each string configuration to calculate Plane of Array (POA) irradiance mathematically (FR3)
4. **And** sums the strings into a single 8,760-element restricted `P_solar(t)` 1D Numpy array
5. **And** explicitly avoids mutating any external parameters during the calculation (NFR2)
6. **And** returns purely the `P_solar(t)` array and a subsequent `Net(t) = C(t) - P_solar(t)` array.

## Tasks / Subtasks

- [x] Task 1 (AC: 1, 2): Implement `src/solar/models/pv_generation.py`
  - [x] Implement `calculate_solar_production(weather_data: dict, strings: list, pr: float) -> np.ndarray`
  - [x] Use `pvlib` to calculate POA irradiance for each string.
  - [x] Apply system losses via Performance Ratio (PR).
- [x] Task 2 (AC: 3, 4): Aggregate String Generation
  - [x] Sum the output of all strings into a single 1D numpy array of length 8,760.
  - [x] Ensure output shape is strictly `(8760,)`.
- [x] Task 3 (AC: 6): Calculate Net Load
  - [x] Implement calculation: `Net(t) = Consumption(t) - P_solar(t)`.
  - [x] Return both `P_solar` and `Net` arrays.
- [x] Task 4 (AC: 5): Statelessness & No Mutation
  - [x] Ensure functions are pure and do not modify input arrays in-place.
- [x] Task 5: Add unit tests
  - [x] Create `tests/models/test_pv_generation.py`.
  - [x] Verify POA math against known `pvlib` benchmarks.
  - [x] Test with multiple strings (different tilt/azimuth).
  - [x] Validate 8,760 length assertions.

## Dev Notes

- **Vector Boundaries**: Input arrays (GHI, DNI, DHI, Temp) must be 1D numpy arrays. The output must also be 1D numpy arrays as per the **Vector Boundary Rule** in `architecture.md`.
- **Library Requirements**: Leverage `pvlib-python`. Use the `pvlib.irradiance.get_total_irradiance` or similar high-level models for POA calculation.
- **Performance SLA**: Solar generation calculation must remain under the 100ms threshold for internal math logic.
- **Physical Defaults**: Use PR=0.80 if not specified (default from PRD 4.2).
- **Previous Story (1.3) Learnings**: Use the `SimulationConfig` dataclass patterns established in Story 1.3 for any parameter handling. Note that simulation.py currently holds the orchestration logic; you will be adding the first real physics module here.

### Project Structure Notes

- **Logic Module:** `src/solar/models/pv_generation.py`
- **Test Module:** `tests/models/test_pv_generation.py`
- **Standards:** Enforce snake_case and explicit array naming (`p_solar`, `net_load`).

### References

- Epic breakdown: [Source: _bmad-output/planning-artifacts/epics.md#Story 2.1: Pvlib Array Generation Module]
- Atmospheric physics requirements: [Source: docs/solar-prd.md#5.3. Solar Production Model]
- Vector restrictions: [Source: _bmad-output/planning-artifacts/architecture.md#Format Patterns]
- Stateless purity rule: [Source: _bmad-output/planning-artifacts/architecture.md#Communication Patterns]

## Dev Agent Record

### Agent Model Used

Gemini 3.1 Pro

### Debug Log References

### Completion Notes List

- Implemented `src/solar/models/pv_generation.py` using `pvlib` for POA irradiance.
- Updated `SimulationConfig` and `SolarStringConfig` in `src/solar/config.py` to support multiple strings and location coordinates.
- Integrated PV physics into `run_simulation` in `src/solar/simulation.py`.
- Fixed regressions in `tests/test_simulation.py` (missing `os` import and weather mocks).
- Added unit tests in `tests/models/test_pv_generation.py`.
- Verified that all 7 tests pass.

### File List

- [NEW] `src/solar/models/pv_generation.py`
- [NEW] `tests/models/test_pv_generation.py`
- [MODIFY] `src/solar/config.py`
- [MODIFY] `src/solar/simulation.py`
- [MODIFY] `tests/test_simulation.py`
+
+### Review Findings (2026-04-19)
+
+#### [Decision Needed]
+- [ ] [Review][Decision] Hardcoded Temporal Reference — The code hardcodes 2025 for PV position calculation. Specifies flexible length but PRD mentions "restricted 8760".
+- [ ] [Review][Decision] Missing Specified Parameter — Spec mentions `Temp` vector but simulation logic currently ignores it.
+- [ ] [Review][Decision] Timezone Alignment — Code assumes `Europe/Stockholm` for all inputs without verifying source data metadata.
+
+#### [Patch]
+- [ ] [Review][Patch] Duplicate Imports [src/solar/simulation.py:2]
+- [ ] [Review][Patch] Redundant Type-Hint Imports [src/solar/models/pv_generation.py:4]
+- [ ] [Review][Patch] Weather Data Integrity [src/solar/models/pv_generation.py:10] — Missing key validation, length checks, and NaN handling.
+- [ ] [Review][Patch] Missing Solpos Caching [src/solar/models/pv_generation.py:38]
+- [ ] [Review][Patch] Direct Dataframe Property Access [src/solar/models/pv_generation.py:59] — Use `.to_numpy()` instead of `.values`.

