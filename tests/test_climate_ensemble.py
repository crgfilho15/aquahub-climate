import pandas as pd
import pytest

from src.climate_ensemble import (
    ClimateEnsembleError,
    calculate_ensemble_climatology,
)


def make_config():
    return {
        "ensemble": {
            "method": "equal_weight_mean",
            "uncertainty_metrics": ["min", "max", "std"],
        },
    }


def make_gcm_results():
    """
    Synthetic multi-GCM fixture, same pattern as the existing
    synthetic-raster tests - proves the ensemble arithmetic without
    needing real GCM data.
    """

    rows = []

    # Vila Real, January, 3 GCMs: 10, 12, 14 -> mean 12, std 2.0 (ddof=1)
    for gcm, value in [
        ("GFDL-ESM4", 10.0),
        ("MRI-ESM2-0", 12.0),
        ("UKESM1-0-LL", 14.0),
    ]:
        rows.append(
            {
                "municipality": "Vila Real",
                "month": 1,
                "mean_value": value,
                "unit": "celsius",
                "variable": "tas",
                "gcm": gcm,
                "scenario": "ssp585",
                "period": "2041-2070",
            }
        )

    # Vila Real, February, same 3 GCMs, different values
    for gcm, value in [
        ("GFDL-ESM4", 20.0),
        ("MRI-ESM2-0", 20.0),
        ("UKESM1-0-LL", 20.0),
    ]:
        rows.append(
            {
                "municipality": "Vila Real",
                "month": 2,
                "mean_value": value,
                "unit": "celsius",
                "variable": "tas",
                "gcm": gcm,
                "scenario": "ssp585",
                "period": "2041-2070",
            }
        )

    # Vila Real, January, same variable/period, DIFFERENT scenario -
    # must stay a separate group, not blended with ssp585.
    for gcm, value in [
        ("GFDL-ESM4", 8.0),
        ("MRI-ESM2-0", 9.0),
        ("UKESM1-0-LL", 10.0),
    ]:
        rows.append(
            {
                "municipality": "Vila Real",
                "month": 1,
                "mean_value": value,
                "unit": "celsius",
                "variable": "tas",
                "gcm": gcm,
                "scenario": "ssp126",
                "period": "2041-2070",
            }
        )

    # A second municipality, to prove groups don't leak across regions.
    for gcm, value in [
        ("GFDL-ESM4", 6.0),
        ("MRI-ESM2-0", 6.0),
        ("UKESM1-0-LL", 6.0),
    ]:
        rows.append(
            {
                "municipality": "Alijó",
                "month": 1,
                "mean_value": value,
                "unit": "celsius",
                "variable": "tas",
                "gcm": gcm,
                "scenario": "ssp585",
                "period": "2041-2070",
            }
        )

    return pd.DataFrame(rows)


def test_calculate_ensemble_climatology_basic_stats():
    result = calculate_ensemble_climatology(
        gcm_results=make_gcm_results(),
        config=make_config(),
    )

    vila_real_jan_ssp585 = result[
        (result["municipality"] == "Vila Real")
        & (result["month"] == 1)
        & (result["scenario"] == "ssp585")
    ].iloc[0]

    assert vila_real_jan_ssp585["ensemble_mean"] == pytest.approx(12.0)
    assert vila_real_jan_ssp585["ensemble_min"] == pytest.approx(10.0)
    assert vila_real_jan_ssp585["ensemble_max"] == pytest.approx(14.0)
    assert vila_real_jan_ssp585["ensemble_std"] == pytest.approx(2.0)
    assert vila_real_jan_ssp585["n_gcms"] == 3
    assert vila_real_jan_ssp585["unit"] == "celsius"
    assert vila_real_jan_ssp585["ensemble_method"] == "equal_weight_mean"


def test_calculate_ensemble_climatology_zero_spread():
    result = calculate_ensemble_climatology(
        gcm_results=make_gcm_results(),
        config=make_config(),
    )

    vila_real_feb = result[
        (result["municipality"] == "Vila Real")
        & (result["month"] == 2)
    ].iloc[0]

    assert vila_real_feb["ensemble_mean"] == pytest.approx(20.0)
    assert vila_real_feb["ensemble_min"] == pytest.approx(20.0)
    assert vila_real_feb["ensemble_max"] == pytest.approx(20.0)
    assert vila_real_feb["ensemble_std"] == pytest.approx(0.0)


def test_calculate_ensemble_climatology_keeps_scenarios_separate():
    result = calculate_ensemble_climatology(
        gcm_results=make_gcm_results(),
        config=make_config(),
    )

    vila_real_jan = result[
        (result["municipality"] == "Vila Real")
        & (result["month"] == 1)
    ]

    assert len(vila_real_jan) == 2

    scenarios = dict(
        zip(
            vila_real_jan["scenario"],
            vila_real_jan["ensemble_mean"],
        )
    )

    assert scenarios["ssp585"] == pytest.approx(12.0)
    assert scenarios["ssp126"] == pytest.approx(9.0)


def test_calculate_ensemble_climatology_keeps_municipalities_separate():
    result = calculate_ensemble_climatology(
        gcm_results=make_gcm_results(),
        config=make_config(),
    )

    alijo_jan = result[
        (result["municipality"] == "Alijó")
        & (result["month"] == 1)
    ].iloc[0]

    assert alijo_jan["ensemble_mean"] == pytest.approx(6.0)
    assert alijo_jan["ensemble_std"] == pytest.approx(0.0)


def test_calculate_ensemble_climatology_only_requested_uncertainty_metrics():
    config = make_config()
    config["ensemble"]["uncertainty_metrics"] = ["min"]

    result = calculate_ensemble_climatology(
        gcm_results=make_gcm_results(),
        config=config,
    )

    assert "ensemble_min" in result.columns
    assert "ensemble_max" not in result.columns
    assert "ensemble_std" not in result.columns


def test_unsupported_ensemble_method_raises_error():
    config = make_config()
    config["ensemble"]["method"] = "weighted_by_skill_score"

    with pytest.raises(
        ClimateEnsembleError,
        match="is not supported",
    ):
        calculate_ensemble_climatology(
            gcm_results=make_gcm_results(),
            config=config,
        )


def test_unsupported_uncertainty_metric_raises_error():
    config = make_config()
    config["ensemble"]["uncertainty_metrics"] = ["p90"]

    with pytest.raises(
        ClimateEnsembleError,
        match="are not supported",
    ):
        calculate_ensemble_climatology(
            gcm_results=make_gcm_results(),
            config=config,
        )


def test_missing_required_column_raises_error():
    gcm_results = make_gcm_results().drop(columns=["gcm"])

    with pytest.raises(
        ClimateEnsembleError,
        match="missing required column",
    ):
        calculate_ensemble_climatology(
            gcm_results=gcm_results,
            config=make_config(),
        )
