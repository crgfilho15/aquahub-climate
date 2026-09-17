"""Climate-change anomalies (future minus historical baseline) for AquaHub.

Phase 5 of the roadmap (docs/04_roadmap_future_and_bioclimatic_indices.md):
these are the numbers the platform should actually display - "how much
warmer/wetter/drier will it get" is what matters for adaptation
planning, not the raw future absolute value alone. Depends on Phase 4's
ensemble output and Phase 1's historical baseline output; testable
entirely against synthetic fixtures, like both of those.
"""

import numpy as np
import pandas as pd


class ClimateAnomalyError(ValueError):
    """Raised when anomaly computation cannot proceed as given."""


# Variables whose anomaly is also expressed as a percentage of the
# historical baseline. Only makes sense for quantities that don't
# cross zero in a way that makes "% change" meaningless - temperature
# anomalies stay absolute-only (a "% warmer" reading near 0 °C is not
# meaningful), precipitation gets both.
PERCENT_ANOMALY_VARIABLES = {"pr"}

MERGE_COLUMNS = ["municipality", "month", "variable"]


def calculate_climate_anomalies(
    ensemble_climatology: pd.DataFrame,
    historical_climatology: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute future-minus-baseline anomalies for every row of
    ensemble_climatology, against historical_climatology's baseline.

    Parameters
    ----------
    ensemble_climatology : pandas.DataFrame
        Output of calculate_ensemble_climatology (Phase 4): one row
        per municipality/month/variable/scenario/period, with
        "ensemble_mean" as the future value.

    historical_climatology : pandas.DataFrame
        Output of calculate_monthly_climatology_for_regions (Phase 1):
        one row per municipality/month/variable, with "mean_value" as
        the 1981-2010 baseline. Must contain exactly one baseline row
        per municipality/month/variable - the same baseline is used
        for every future scenario/period.

    Returns
    -------
    pandas.DataFrame
        ensemble_climatology's rows, with baseline_value,
        anomaly_absolute (future - baseline) and anomaly_percent
        (NaN except for PERCENT_ANOMALY_VARIABLES) added.
    """

    required_ensemble_columns = set(
        MERGE_COLUMNS + ["ensemble_mean", "scenario", "period"]
    )

    missing_ensemble_columns = (
        required_ensemble_columns - set(ensemble_climatology.columns)
    )

    if missing_ensemble_columns:
        raise ClimateAnomalyError(
            "ensemble_climatology is missing required column(s): "
            f"{sorted(missing_ensemble_columns)}."
        )

    required_historical_columns = set(MERGE_COLUMNS + ["mean_value"])

    missing_historical_columns = (
        required_historical_columns - set(historical_climatology.columns)
    )

    if missing_historical_columns:
        raise ClimateAnomalyError(
            "historical_climatology is missing required column(s): "
            f"{sorted(missing_historical_columns)}."
        )

    baseline = (
        historical_climatology[MERGE_COLUMNS + ["mean_value"]]
        .rename(columns={"mean_value": "baseline_value"})
    )

    duplicate_baseline_keys = baseline.duplicated(subset=MERGE_COLUMNS)

    if duplicate_baseline_keys.any():
        raise ClimateAnomalyError(
            "historical_climatology has more than one baseline row "
            "for the same municipality/month/variable combination - "
            "pass a single 1981-2010 baseline, not multiple periods."
        )

    merged = ensemble_climatology.merge(
        baseline,
        on=MERGE_COLUMNS,
        how="left",
    )

    missing_baseline = merged["baseline_value"].isna()

    if missing_baseline.any():
        missing_examples = (
            merged.loc[missing_baseline, MERGE_COLUMNS]
            .drop_duplicates()
            .head(5)
            .to_dict("records")
        )
        raise ClimateAnomalyError(
            "No historical baseline found for "
            f"{int(missing_baseline.sum())} row(s), e.g. "
            f"{missing_examples}."
        )

    merged["anomaly_absolute"] = (
        merged["ensemble_mean"] - merged["baseline_value"]
    )

    is_percent_variable = merged["variable"].isin(
        PERCENT_ANOMALY_VARIABLES
    )

    nonzero_baseline = merged["baseline_value"] != 0

    merged["anomaly_percent"] = np.where(
        is_percent_variable & nonzero_baseline,
        merged["anomaly_absolute"] / merged["baseline_value"] * 100,
        np.nan,
    )

    return merged
