"""Multi-GCM ensemble statistics for AquaHub future climate results.

Phase 4 of the roadmap (docs/04_roadmap_future_and_bioclimatic_indices.md):
aggregates the individual-GCM rows Phase 3 produces
(src/future_climate_processing.py's output shape) into one ensemble
statistic per municipality/month/variable/scenario/period, per
config/climate.toml's [ensemble] section. Testable entirely against a
synthetic multi-GCM fixture - it does not require real GCM data, only
Phase 3's output shape.
"""

import pandas as pd


class ClimateEnsembleError(ValueError):
    """Raised when ensemble computation cannot proceed as configured."""


SUPPORTED_ENSEMBLE_METHODS = {"equal_weight_mean"}
SUPPORTED_UNCERTAINTY_METRICS = {"min", "max", "std"}

# Grouping deliberately keeps scenario and period as separate axes -
# never averaged together. The whole point of the conservative/extreme
# bracket (docs/04 Section 3) is to show two distinct outcomes, not to
# blend them into one number.
GROUP_COLUMNS = ["municipality", "month", "variable", "scenario", "period"]

REQUIRED_COLUMNS = set(GROUP_COLUMNS) | {"mean_value", "unit", "gcm"}


def calculate_ensemble_climatology(
    gcm_results: pd.DataFrame,
    config: dict,
) -> pd.DataFrame:
    """
    Aggregate individual-GCM future climatology results into one
    ensemble statistic per municipality/month/variable/scenario/period.

    Parameters
    ----------
    gcm_results : pandas.DataFrame
        Output of calculate_future_monthly_climatology_for_gcm or
        calculate_future_monthly_climatology_for_all_gcms (one row per
        municipality/month/gcm), or the equivalent CSV loaded back in.

    config : dict
        AquaHub climate configuration. Uses config["ensemble"]:
        "method" (only "equal_weight_mean" is implemented) and
        "uncertainty_metrics" (any of "min"/"max"/"std").

    Returns
    -------
    pandas.DataFrame
        One row per municipality/month/variable/scenario/period, with
        ensemble_mean, n_gcms, the requested uncertainty columns
        (ensemble_min/ensemble_max/ensemble_std), and the unit and
        method carried through for traceability.

    Notes
    -----
    ensemble_std uses pandas' default sample standard deviation
    (ddof=1, "N-1"), the common convention for small multi-model GCM
    ensembles in the climate literature. With only 1 GCM present for a
    group, this is NaN (undefined for a single sample) rather than 0 -
    not expected to occur with the full 5-GCM set this project uses,
    but worth knowing if a filtered/partial gcm_results is passed in.
    """

    ensemble_config = config["ensemble"]

    method = ensemble_config.get("method", "")

    if method not in SUPPORTED_ENSEMBLE_METHODS:
        raise ClimateEnsembleError(
            f"Ensemble method '{method}' is not supported. "
            f"Supported: {sorted(SUPPORTED_ENSEMBLE_METHODS)}."
        )

    uncertainty_metrics = ensemble_config.get("uncertainty_metrics", [])

    unsupported_metrics = (
        set(uncertainty_metrics) - SUPPORTED_UNCERTAINTY_METRICS
    )

    if unsupported_metrics:
        raise ClimateEnsembleError(
            f"Uncertainty metric(s) {sorted(unsupported_metrics)} are "
            "not supported. Supported: "
            f"{sorted(SUPPORTED_UNCERTAINTY_METRICS)}."
        )

    missing_columns = REQUIRED_COLUMNS - set(gcm_results.columns)

    if missing_columns:
        raise ClimateEnsembleError(
            "gcm_results is missing required column(s): "
            f"{sorted(missing_columns)}."
        )

    aggregation = {
        "ensemble_mean": ("mean_value", "mean"),
        "n_gcms": ("gcm", "nunique"),
        "unit": ("unit", "first"),
    }

    if "min" in uncertainty_metrics:
        aggregation["ensemble_min"] = ("mean_value", "min")

    if "max" in uncertainty_metrics:
        aggregation["ensemble_max"] = ("mean_value", "max")

    if "std" in uncertainty_metrics:
        aggregation["ensemble_std"] = ("mean_value", "std")

    result = (
        gcm_results
        .groupby(GROUP_COLUMNS, as_index=False)
        .agg(**aggregation)
    )

    result["ensemble_method"] = method

    return result
