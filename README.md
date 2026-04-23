# Residential Solar & Battery Economic Simulation Model (Sweden)

Hourly simulation model to assess the economic feasibility of residential solar PV and Battery Energy Storage Systems (BESS) in the Swedish market.

## Project Structure

```text
├── data/               # Raw and processed datasets
├── docs/               # Project documentation (PRD, architecture)
├── notebooks/          # Exploratory analysis and visualizations
├── src/                # Core simulation logic
│   └── solar/          # Python modules for PV/Battery modelling
├── tests/              # Unit tests
├── Makefile            # Project orchestration (lint, clean, install)
└── pyproject.toml      # Dependency management and metadata
```

## Getting Started

1. Ensure Python 3.9+ is installed.
2. Install dependencies:
   ```bash
   make requirements
   ```
3. Run linting:
   ```bash
   make lint
   ```

## Key Features

- Hourly resolution (8,760 hours/year).
- Vectorized performance (Numpy/Pandas).
- Swedish market economics (Nord Pool prices, retail tax & grid fees).
- Linear Programming (LP) battery optimization with perfect foresight.
- FCR-D Ancillary Services modeling.
