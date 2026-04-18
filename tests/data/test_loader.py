import os
import tempfile

import numpy as np
import pandas as pd
import pytest

from solar.data.loader import expand_slp, enforce_timezone_bounds, save_to_parquet


def test_slp_expansion():
    """
    Validates SLP redistribution math using non-uniform weights.

    Uniform weights trivially satisfy the per-month sum constraint; non-uniform
    weights require the implementation to correctly normalize per-month. The
    invariant is: sum(C(t) for t in month m) == monthly_kwh[m] for all m.
    """
    rng = np.random.default_rng(42)
    slp_weights = rng.uniform(0.5, 2.0, size=8760)  # Non-trivial variation
    monthly_kwh = [100.0 * (m + 1) for m in range(12)]  # 100..1200 kWh

    hourly_kwh = expand_slp(monthly_kwh, slp_weights)

    assert len(hourly_kwh) == 8760
    assert np.isclose(np.sum(hourly_kwh), sum(monthly_kwh))

    # Per-month sums must equal monthly_kwh[m] (invariant of the SLP formula)
    time_idx = pd.date_range(
        "2023-01-01", periods=8760, freq="h", tz="Europe/Stockholm"
    )
    for m in range(12):
        mask = time_idx.month == (m + 1)
        assert np.isclose(hourly_kwh[mask].sum(), monthly_kwh[m]), (
            f"Month {m + 1}: expected {monthly_kwh[m]:.2f}, "
            f"got {hourly_kwh[mask].sum():.2f}"
        )


def test_timezone_leap_year_truncation():
    """
    Verifies that a UTC leap-year input (8784 rows) is converted to
    Europe/Stockholm, issues warnings, and produces exactly 8760 rows
    with Feb 29 removed (calendar-based truncation).
    """
    index = pd.date_range("2024-01-01 00:00:00", periods=8784, freq="h", tz="UTC")
    df = pd.DataFrame({"spot_price": np.random.rand(8784)}, index=index)

    # Expect both a tz-conversion warning and a leap-year truncation warning
    with pytest.warns(UserWarning):
        processed_df = enforce_timezone_bounds(df)

    assert len(processed_df) == 8760
    assert str(processed_df.index.tz) == "Europe/Stockholm"

    # Calendar-based: Feb 29 must be absent from the result
    is_feb29 = (processed_df.index.month == 2) & (processed_df.index.day == 29)
    assert not is_feb29.any(), "Feb 29 should have been dropped by calendar-based truncation"


def test_timezone_warn_on_non_stockholm():
    """
    Verifies that passing a non-Stockholm timezone triggers a UserWarning
    and still produces a correctly converted 8760-row Stockholm-indexed result.
    """
    index = pd.date_range("2023-01-01", periods=8760, freq="h", tz="UTC")
    df = pd.DataFrame({"spot_price": np.ones(8760)}, index=index)

    with pytest.warns(UserWarning, match="converting to 'Europe/Stockholm'"):
        processed_df = enforce_timezone_bounds(df)

    assert len(processed_df) == 8760
    assert str(processed_df.index.tz) == "Europe/Stockholm"


def test_save_to_parquet():
    index = pd.date_range(
        "2023-01-01 00:00:00", periods=8760, freq="h", tz="Europe/Stockholm"
    )
    df = pd.DataFrame({"spot_price": np.random.rand(8760)}, index=index)

    with tempfile.TemporaryDirectory() as tmpdirname:
        filepath = os.path.join(tmpdirname, "test.parquet")
        save_to_parquet(df, filepath)

        assert os.path.exists(filepath)

        loaded = pd.read_parquet(filepath, engine="pyarrow")
        assert len(loaded) == 8760
        assert "spot_price" in loaded.columns


def test_save_to_parquet_rejects_multi_column():
    """Verifies the 1D architectural boundary: multi-column frames are rejected."""
    index = pd.date_range(
        "2023-01-01", periods=8760, freq="h", tz="Europe/Stockholm"
    )
    df = pd.DataFrame({"a": np.ones(8760), "b": np.ones(8760)}, index=index)

    with pytest.raises(ValueError, match="single-column"):
        save_to_parquet(df, os.path.join(tempfile.gettempdir(), "should_not_create.parquet"))
