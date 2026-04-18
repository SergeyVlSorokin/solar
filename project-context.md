# Project Context — Solar & Battery Economic Simulation

> This file is loaded automatically by all BMad agents at workflow initialisation.
> Keep it up to date whenever the dev environment changes.

## Python Environment

This project uses a **project-local conda environment** located at:

```
{project-root}/.conda/
```

### Executable Paths (Windows)

| Tool | Path |
|---|---|
| Python | `.conda\python.exe` |
| pytest | `.conda\Scripts\pytest.exe` |
| pip | `.conda\Scripts\pip.exe` |

**Python version:** 3.10.20  
**pytest version:** 9.0.3

### Running Tests

Always use the project-local `.conda` environment. Do **not** use system `python`, `py`, or `poetry` — they are not available in this workspace.

```powershell
# Run the full test suite
.\.conda\Scripts\pytest.exe tests/ -v

# Run a specific test file
.\.conda\Scripts\pytest.exe tests/test_simulation.py -v
```

### Installing the Package

If the `solar` package is not importable (e.g. `ModuleNotFoundError: No module named 'solar'`), install it in editable mode:

```powershell
.\.conda\Scripts\pip.exe install -e .
```

> [!IMPORTANT]
> Always install with `.conda\Scripts\pip.exe`, not the system pip. The package must be installed
> in the project-local env for tests to resolve `from solar.xxx import ...` imports.

## Project Structure

```
solar/
├── .conda/              # Project-local conda Python 3.10 environment
├── src/solar/           # Source package (installed via pip install -e .)
├── tests/               # pytest test suite
├── data/
│   ├── raw/             # Raw heterogeneous input files
│   └── processed/       # Standardized .parquet outputs (Europe/Stockholm tz, 8760 rows)
├── docs/                # Project documentation
├── notebooks/           # Jupyter exploration
├── _bmad-output/        # BMad planning and implementation artifacts
└── pyproject.toml       # Project metadata and dependencies
```

## Architectural Constraints (critical for all agents)

- **1D numpy arrays only** — all simulation math uses `(8760,)` flat arrays; no Pandas in business logic.
- **8760-row invariant** — all parquet files must have exactly 8760 hourly rows. Enforce with `ValueError`.
- **Named column access** — always read parquet columns by name (e.g. `df["consumption"]`), not by position (`iloc[:, 0]`).
- **Fail-fast errors** — `FileNotFoundError` from pandas must be caught and re-raised as `ValueError` with a descriptive message.
- **Europe/Stockholm timezone** — all time-indexed data is anchored to this timezone in the data layer.
- **Mock targets** — when mocking `pd.read_parquet` in tests, patch `solar.simulation.pd.read_parquet` (or the relevant module's bound reference), not the bare `pandas.read_parquet`.
