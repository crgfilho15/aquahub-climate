"""General (Tier 1) bioclimatic indices for AquaHub.

Phase 6 of the roadmap (docs/04_roadmap_future_and_bioclimatic_indices.md):
indices computable for any crop or none, from monthly climatology alone
(no daily data required, unlike frost-day counts or chilling hours,
which the project's monthly-data decision explicitly cannot support -
see docs/04 Section 3). Deliberately generic over its input: the same
functions work on Phase 1's historical monthly climatology, Phase 4's
ensemble output, or Phase 5's anomaly output, since all three share the
same (municipality, month, ...) row shape - only the column holding the
temperature/precipitation value differs (value_column), and Phase 4/5
outputs additionally carry gcm/scenario/period as extra group_columns.

Crop-specific thresholds (Phase 7) are explicitly out of scope here -
per the roadmap's own rule, a threshold is implemented only once the
agronomy team confirms it, never invented. This module computes the
raw index values only.
"""

from collections.abc import Iterable

import pandas as pd


class BioclimaticIndexError(ValueError):
    """Raised when a bioclimatic index cannot be computed as given."""


# Standard (non-leap) calendar days per month - the conventional
# assumption for monthly-climatology-based degree-day approximations
# in the agroclimatology literature (CHELSA's own monthly climatologies
# are 30-year averages with no per-year leap adjustment either).
DAYS_PER_MONTH = {
    1: 31,
    2: 28,
    3: 31,
    4: 30,
    5: 31,
    6: 30,
    7: 31,
    8: 31,
    9: 30,
    10: 31,
    11: 30,
    12: 31,
}

# Northern-hemisphere growing season (April-October) - the standard
# window for GDD/Winkler Index and growing-season precipitation in the
# viticulture/agroclimatology literature for this latitude.
DEFAULT_SEASON_MONTHS = range(4, 11)

DEFAULT_GROUP_COLUMNS = ["municipality"]


def _filter_and_validate_season(
    monthly_climatology: pd.DataFrame,
    season_months: Iterable[int] | None,
    value_column: str,
    group_columns: list[str] | None,
) -> tuple[pd.DataFrame, list[str], list[int]]:
    """Shared validation/filtering for the index functions below."""

    if group_columns is None:
        group_columns = list(DEFAULT_GROUP_COLUMNS)

    required_columns = set(group_columns) | {"month", value_column}
    missing_columns = required_columns - set(monthly_climatology.columns)

    if missing_columns:
        raise BioclimaticIndexError(
            "monthly_climatology is missing required column(s): "
            f"{sorted(missing_columns)}."
        )

    season = sorted(
        set(season_months)
        if season_months is not None
        else set(DEFAULT_SEASON_MONTHS)
    )

    invalid_months = set(season) - set(range(1, 13))

    if invalid_months:
        raise BioclimaticIndexError(
            f"season_months contains invalid month(s): "
            f"{sorted(invalid_months)}. Months must be 1-12."
        )

    season_rows = monthly_climatology[
        monthly_climatology["month"].isin(season)
    ].copy()

    if season_rows.empty:
        raise BioclimaticIndexError(
            f"No rows in monthly_climatology fall within season_months "
            f"{season}."
        )

    return season_rows, group_columns, season


def calculate_growing_degree_days(
    monthly_climatology: pd.DataFrame,
    base_temperature: float = 10.0,
    season_months: Iterable[int] | None = None,
    value_column: str = "mean_value",
    group_columns: list[str] | None = None,
) -> pd.DataFrame:
    """
    Growing Degree Days (GDD), approximated from monthly climatology.

    Daily GDD is sum(max(0, T_mean_day - base_temperature)) over the
    season. Without daily data, this approximates each day in a month
    by that month's mean: max(0, T_mean_month - base_temperature) *
    days_in_month, summed over season_months. This is the standard
    monthly approximation used when only monthly climatologies are
    available (see docs/04 Section 3's monthly-vs-daily trade-off).

    Parameters
    ----------
    monthly_climatology : pandas.DataFrame
        Any monthly climatology table with a "month" column (1-12) and
        a temperature value column - e.g. Phase 1's historical output
        (value_column="mean_value", group_columns=["municipality"]) or
        Phase 4's ensemble output (value_column="ensemble_mean",
        group_columns=["municipality", "scenario", "period"]).

    base_temperature : float
        Degrees above which heat accumulates (°C). Default 10.0, the
        conventional base for viticulture (see
        calculate_winkler_index, a named case of this function).

    season_months : Iterable[int] | None
        Calendar months (1-12) to sum over. Default: April-October
        (DEFAULT_SEASON_MONTHS), the standard Northern-Hemisphere
        growing season.

    value_column : str
        Column holding the temperature value to accumulate.

    group_columns : list[str] | None
        Columns identifying one climatology series - default
        ["municipality"]. Pass e.g. ["municipality", "scenario",
        "period"] for ensemble/anomaly input, so GDD is computed
        separately per scenario/period rather than blended together.

    Returns
    -------
    pandas.DataFrame
        One row per group_columns combination, with
        "growing_degree_days", plus base_temperature and
        season_months carried through for traceability.
    """

    season_rows, group_columns, season = _filter_and_validate_season(
        monthly_climatology=monthly_climatology,
        season_months=season_months,
        value_column=value_column,
        group_columns=group_columns,
    )

    season_rows["_days_in_month"] = season_rows["month"].map(
        DAYS_PER_MONTH
    )

    season_rows["_monthly_degree_days"] = (
        (season_rows[value_column] - base_temperature).clip(lower=0)
        * season_rows["_days_in_month"]
    )

    result = (
        season_rows
        .groupby(group_columns, as_index=False)["_monthly_degree_days"]
        .sum()
        .rename(
            columns={"_monthly_degree_days": "growing_degree_days"}
        )
    )

    result["base_temperature"] = base_temperature
    result["season_months"] = str(season)

    return result


def calculate_winkler_index(
    monthly_climatology: pd.DataFrame,
    value_column: str = "mean_value",
    group_columns: list[str] | None = None,
) -> pd.DataFrame:
    """
    Winkler Index (Growing Season Degree Days) - the classic
    viticulture heat-summation index (Amerine & Winkler, 1944): GDD
    with a 10°C base temperature over the April-October growing
    season. A named, fixed-parameter case of
    calculate_growing_degree_days - the Winkler region classification
    (I-V) is not implemented here, since that is a specific threshold
    scheme and this module deliberately stops at raw index values (see
    module docstring).
    """

    result = calculate_growing_degree_days(
        monthly_climatology=monthly_climatology,
        base_temperature=10.0,
        season_months=range(4, 11),
        value_column=value_column,
        group_columns=group_columns,
    )

    return result.rename(
        columns={"growing_degree_days": "winkler_index"}
    )


def calculate_growing_season_precipitation(
    monthly_climatology: pd.DataFrame,
    season_months: Iterable[int] | None = None,
    value_column: str = "mean_value",
    group_columns: list[str] | None = None,
) -> pd.DataFrame:
    """
    Total precipitation over the growing season - a Tier 1 general
    index, relevant to water-balance/dryness assessment for any crop.

    Parameters mirror calculate_growing_degree_days, except there is
    no base_temperature (monthly precipitation values are summed
    directly, not thresholded).
    """

    season_rows, group_columns, season = _filter_and_validate_season(
        monthly_climatology=monthly_climatology,
        season_months=season_months,
        value_column=value_column,
        group_columns=group_columns,
    )

    result = (
        season_rows
        .groupby(group_columns, as_index=False)[value_column]
        .sum()
        .rename(
            columns={
                value_column: "growing_season_precipitation",
            }
        )
    )

    result["season_months"] = str(season)

    return result
