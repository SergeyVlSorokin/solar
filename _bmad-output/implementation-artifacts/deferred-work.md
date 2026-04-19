# Deferred Work

## Deferred from: code review of 1-2-standardize-raw-input-profiles-to-parquet (2026-04-17)

- **No orchestrating pipeline function in loader.py** — `loader.py` exports three isolated utility functions but no top-level `load_profiles()` pipeline function. Downstream consumers must re-implement the pipeline themselves, risking future divergence. Pre-existing design choice not introduced by story 1.2.
- **Missing type annotations on all public functions** — `expand_slp`, `enforce_timezone_bounds`, and `save_to_parquet` have no PEP 484 type hints. Project-wide style gap not specific to this story.

## Deferred from: code review of 1-3-execute-baseline-orchestration-loop (2026-04-17)

- **`net_electricity_cost_sek` duplicates `total_money_spent`** — both keys hold the same scalar at baseline. Architecturally misleading for future epics when grid sell revenue is active. Address when Epic 5 revenue arrays are implemented. [simulation.py:39]
- **`SimulationConfig` and strings accept negative values** — no `__post_init__` guard exists. Low risk at baseline but should be hardened before Battery epics. [config.py]
