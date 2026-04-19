# Deferred Work

## Deferred from: code review of 1-2-standardize-raw-input-profiles-to-parquet (2026-04-17)

- **No orchestrating pipeline function in loader.py** — `loader.py` exports three isolated utility functions but no top-level `load_profiles()` pipeline function. Downstream consumers must re-implement the pipeline themselves, risking future divergence. Pre-existing design choice not introduced by story 1.2.
- **Missing type annotations on all public functions** — `expand_slp`, `enforce_timezone_bounds`, and `save_to_parquet` have no PEP 484 type hints. Project-wide style gap not specific to this story.

## Deferred from: code review of 1-3-execute-baseline-orchestration-loop (2026-04-17)

- **`net_electricity_cost_sek` duplicates `total_money_spent`** — both keys hold the same scalar at baseline. Architecturally misleading for future epics when grid sell revenue is active. Address when Epic 5 revenue arrays are implemented. [simulation.py:39]
- **`SimulationConfig` and strings accept negative values** — no `__post_init__` guard exists. Low risk at baseline but should be hardened before Battery epics. [config.py]
+
+## Deferred from: code review of 4-1-main-fuse-transmission-limits.md (2026-04-19)
+
+- **Hardcoded 400V grid voltage** — Formula in `grid_finance.py` is hardcoded for 400V. While specified in FR6, parameterizing it would improve future-proofing. [src/solar/models/grid_finance.py:11]

## Deferred from: code review of 3-3-intraday-price-arbitrage-logic.md (2026-04-19)

- **Array Allocation Inefficiency** — Multiple intermediate copies and reshapes in ranking logic. Could be optimized for memory. [battery_logic.py:59]
- **Hardcoded Defaults Consistency** — `n_low=6` and `n_high=6` are repeated in multiple signatures instead of using constants or config. [battery_logic.py:54]
- **Priority Logic Maintainability Refactor** — The five-way branching logic (`if/elif/elif/else`) is becoming brittle for future features. [battery_logic.py:136]
