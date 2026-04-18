# Story 1.2: Standardize Raw Input Profiles to Parquet

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Data Analyst,
I want the Data Loader script to assert timezones and export standardized Parquet arrays,
so that I am mathematically guaranteed exactly 8,760 aligned hourly steps for the simulation.

## Acceptance Criteria

1. **Given** heterogenous input data (Spot Prices, Monthly Load totals)
   **When** the `src/solar/data/loader.py` script is executed
   **Then** it expands monthly consumption via SLP into an 8,760-element array
2. **And** strictly asserts the `Europe/Stockholm` timezone across all arrays
3. **And** fails and truncates if leap year data (8784) is found
4. **And** saves the output strictly as 1D arrays into `.parquet` files.

## Tasks / Subtasks

- [x] Task 1: Initialize SLP array expansion logic (AC: 1)
  - [x] Implement SLP weights mechanism to explode 12 monthly values to 8760 hourly values mathematically aligned with Swedish standards.
- [x] Task 2: Implement timezone validation and bounds checking (AC: 2, 3)
  - [x] Apply `Europe/Stockholm` timezone assertion for Dataframes before extracting numpy arrays.
  - [x] Implement logic to truncate lengths from 8784 to 8760 if leap year is detected (or raise exact exception based on product requirement details).
- [x] Task 3: Setup Parquet saving utility (AC: 4)
  - [x] Serialize strictly 1D arrays to `data/processed/*.parquet` (e.g. `spot_prices.parquet`, `load_profile.parquet`).
- [x] Task 4: Add Unit Tests
  - [x] Create `tests/data/test_loader.py`.
  - [x] Test timezone assertions and truncation logic.
  - [x] Test SLP expansion math for correct sums.

### Review Findings

- [x] [Review][Decision] Leap year truncation strategy ambiguous → resolved: calendar-based drop of Feb 29 [loader.py]
- [x] [Review][Decision] `enforce_timezone_bounds` silent tz coercion → resolved: coerce-and-warn with `warnings.warn` [loader.py]
- [x] [Review][Decision] AC 3 "fails and truncates" ambiguous → resolved: warn + truncate (no raise on 8784) [loader.py]
- [x] [Review][Patch] Remove unused `pytz` import [loader.py:3]
- [x] [Review][Patch] Add `.copy()` in all paths to prevent silent caller mutation [loader.py]
- [x] [Review][Patch] Add non-negative validation for `monthly_kwh` elements [loader.py]
- [x] [Review][Patch] Enforce single-column (1D) constraint in `save_to_parquet` [loader.py]
- [x] [Review][Patch] Add `os.makedirs` for missing parent directory in `save_to_parquet` [loader.py]
- [x] [Review][Patch] Replace UTC-based internal index in `expand_slp` with `Europe/Stockholm` [loader.py]
- [x] [Review][Patch] Fix `.tz.zone` deprecated attribute → `str(processed_df.index.tz)` [test_loader.py]
- [x] [Review][Patch] Improve `test_slp_expansion` with non-uniform weights + per-month assertions [test_loader.py]
- [x] [Review][Patch] Coerce `slp_weights` to `np.asarray` at function entry [loader.py]
- [x] [Review][Patch] Filter NaT rows after `tz_localize(ambiguous='NaT')` [loader.py]
- [x] [Review][Patch] Fix `datetime_col` path: wrap in `pd.DatetimeIndex` before tz ops [loader.py]
- [x] [Review][Defer] No orchestrating pipeline function in loader.py — deferred, pre-existing
- [x] [Review][Defer] Missing type annotations on all public functions — deferred, pre-existing

**Review resolved 2026-04-17. All patches applied. 5/5 tests pass.**

## Dev Notes

- **Architecture Rules:** 
  - **The Outer Data Boundary (`src/solar/data/loader.py`)**: This is the ONLY place where `pandas.DataFrame` and `DatetimeIndex` structures are permitted. Once data is cleaned here, it must be saved to Parquet. Deep internal physics modules will *only* exchange 1D flattened `numpy.ndarray` variables.
  - **Data Structure**: `pandas.DataFrame.to_parquet(..., engine='pyarrow')` should be used. 
- **Timezone Integrity**: Assert `Europe/Stockholm`. Ensure DST gaps/overlaps (which happen natively) are handled so a strict `8760` array length emerges.
- **Previous Story (1.1) Learnings**:
  - The project structure uses Cookiecutter Data Science (CCDS) V2. Make sure to place the loader logic in `src/solar/data/loader.py`.
  - Ensure that tests go into `tests/data/`.
  - The `Makefile` exists and will later rely on `data/loader.py` to move data from `raw/` to `processed/`.
- **Dependencies**: The `pyproject.toml` already includes `pandas` and `numpy`. Ensure `pyarrow` is available for parquet capabilities.

### Project Structure Notes

- **Input files expected:** Assume external CSV/raw data will be modeled from `data/raw/`. Mocks should be utilized for testing if real data is missing.
- **Target destination:** `data/processed/`
- **Logic Module:** `src/solar/data/loader.py`
- **Test Module:** `tests/data/test_loader.py`

### References

- Epic breakdown for ACs: [Source: _bmad-output/planning-artifacts/epics.md#Story 1.2: Standardize Raw Input Profiles to Parquet]
- Parquet & Boundary constraints: [Source: _bmad-output/planning-artifacts/architecture.md#Architectural Boundaries]
- PRD SLP weights constraint: [Source: docs/solar-prd.md#5.2. Hourly Consumption Profiling]

## Dev Agent Record

### Agent Model Used

Gemini 3.1 Pro

### Debug Log References

### Completion Notes List
- Successfully implemented SLP math calculation to expand monthly weights using numpy masking.
- Implemented `Europe/Stockholm` timezone assertions using pandas `tz_localize` and `tz_convert`.
- Created robust Leap Year truncations from 8784 -> 8760 records.
- Completed Pytest unit tests for all functions in `tests/data/test_loader.py`.

### File List
- `pyproject.toml` (Modified)
- `src/solar/data/loader.py` (New)
- `tests/data/test_loader.py` (New)
