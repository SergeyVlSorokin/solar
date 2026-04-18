import os
import warnings

import numpy as np
import pandas as pd


def expand_slp(monthly_kwh, slp_weights):
    """
    Expands a 12-element monthly energy consumption array into an 8760-element
    hourly array based on the Swedish Standard Load Profile (SLP).

    Uses Europe/Stockholm timezone for month boundary alignment, correctly
    accounting for DST transitions in March and October.

    Formula: C(t) = C_m * (W_SLP(t) / sum(W_SLP(t) for t in m))

    Args:
        monthly_kwh: list or array of 12 non-negative floats (Jan-Dec, kWh)
        slp_weights: list or array of 8760 non-negative normalized hourly weights

    Returns:
        1D numpy array of length 8760

    Raises:
        ValueError: if inputs have wrong length, are negative, or weights sum to zero.
    """
    monthly_kwh = np.asarray(monthly_kwh, dtype=float)
    slp_weights = np.asarray(slp_weights, dtype=float)

    if len(monthly_kwh) != 12:
        raise ValueError("monthly_kwh must have exactly 12 elements")
    if np.any(monthly_kwh < 0):
        raise ValueError("monthly_kwh values must be non-negative")
    if len(slp_weights) != 8760:
        raise ValueError("slp_weights must have exactly 8760 elements")
    if np.isnan(slp_weights).any():
        raise ValueError("slp_weights contains NaN values")

    # Use Europe/Stockholm so month boundaries align with DST (March/October transitions)
    time_idx = pd.date_range(
        "2023-01-01 00:00:00", periods=8760, freq="h", tz="Europe/Stockholm"
    )

    c_t = np.zeros(8760)

    for month in range(1, 13):
        month_mask = time_idx.month == month
        month_slp = slp_weights[month_mask]
        month_slp_sum = month_slp.sum()

        if month_slp_sum == 0:
            raise ValueError(f"SLP weights sum to zero for month {month}")

        c_m = monthly_kwh[month - 1]
        # C(t) = C_m * (W_SLP(t) / sum(W_SLP(t) for t in m))
        c_t[month_mask] = c_m * (month_slp / month_slp_sum)

    return c_t


def enforce_timezone_bounds(df, datetime_col=None):
    """
    Enforces the Europe/Stockholm timezone on a DataFrame and ensures exactly
    8760 rows.

    Behavior:
    - If the source timezone is not Europe/Stockholm, emits a UserWarning before
      converting (coerce-and-warn). Only naive (tz-unaware) DataFrames are
      localized silently.
    - NaT rows introduced by DST fall-back ambiguity are removed.
    - If 8784 rows remain (leap year), emits a UserWarning and drops Feb 29
      (calendar-based truncation) to align with the non-leap SLP grid.

    Args:
        df: pandas DataFrame with a DatetimeIndex or a datetime column.
        datetime_col: optional column name containing datetime values. If
            provided, the column is promoted to the index and dropped.

    Returns:
        DataFrame with a Europe/Stockholm DatetimeIndex and exactly 8760 rows.

    Raises:
        ValueError: if row count is not 8760 or 8784 after NaT filtering, or if
            calendar-based truncation does not yield exactly 8760 rows.
    """
    df = df.copy()

    if datetime_col:
        dt_index = pd.DatetimeIndex(pd.to_datetime(df[datetime_col]))
        df = df.drop(columns=[datetime_col])
    else:
        dt_index = pd.DatetimeIndex(df.index)

    # Localize naive index or convert aware index to Europe/Stockholm
    if dt_index.tz is None:
        dt_index = dt_index.tz_localize(
            "Europe/Stockholm", ambiguous="NaT", nonexistent="shift_forward"
        )
    else:
        if str(dt_index.tz) != "Europe/Stockholm":
            warnings.warn(
                f"Input timezone is '{dt_index.tz}', converting to 'Europe/Stockholm'. "
                "Verify alignment with other input arrays.",
                UserWarning,
                stacklevel=2,
            )
        dt_index = dt_index.tz_convert("Europe/Stockholm")

    df.index = dt_index

    # Remove NaT rows that appear during DST fall-back (ambiguous='NaT')
    df = df[df.index.notna()]

    n = len(df)

    if n == 8784:
        warnings.warn(
            "Leap year detected (8784 hours): dropping Feb 29 to produce 8760-hour array.",
            UserWarning,
            stacklevel=2,
        )
        # Calendar-based truncation: drop Feb 29 to preserve alignment with non-leap SLP
        feb29_mask = ~((df.index.month == 2) & (df.index.day == 29))
        df = df[feb29_mask]
    elif n != 8760:
        raise ValueError(f"Expected 8760 hourly steps, but got {n}")

    if len(df) != 8760:
        raise ValueError(
            f"After leap-year truncation, expected 8760 hourly steps, but got {len(df)}"
        )

    return df


def save_to_parquet(df, filepath):
    """
    Saves a single-column (1D) DataFrame to Parquet using pyarrow.

    Enforces the architectural boundary that physics modules only exchange 1D
    arrays. Parent directories are created automatically if they do not exist.

    Args:
        df: single-column pandas DataFrame
        filepath: destination path for the Parquet file

    Raises:
        ValueError: if df contains more than one column.
    """
    if df.shape[1] != 1:
        raise ValueError(
            f"save_to_parquet expects a single-column (1D) DataFrame, "
            f"but received {df.shape[1]} columns: {list(df.columns)}"
        )
    parent_dir = os.path.dirname(filepath)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    df.to_parquet(filepath, engine="pyarrow")
