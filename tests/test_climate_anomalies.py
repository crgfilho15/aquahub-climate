import pandas as pd
import pytest

from src.climate_anomalies import (
    ClimateAnomalyError,
    calculate_climate_anomalies,
)


def make_ensemble_climatology():
    """
    Synthetic Phase 4 output: 2 scenarios x 1 period, temperature and
    precipitation, for a single municipality/month each.
    """

    return pd.DataFrame(
        [
            {
                "municipality": "Vila Real",
                "month": 1,
                "variable": "tas",
                "scenario": "ssp585",
                "period": "2041-2070",
                "ensemble_mean": 12.0,
                "unit": "celsius",
            },
            {
                "municipality": "Vila Real",
                "month": 1,
                "variable": "tas",
                "scenario": "ssp126",
                "period": "2041-2070",
                "ensemble_mean": 9.0,
                "unit": "celsius",
            },
            {
                "municipality": "Vila Real",
                "month": 1,
                "variable": "pr",
                "scenario": "ssp585",
                "period": "2041-2070",
                "ensemble_mean": 90.0,
                "unit": "mm",
            },
        ]
    )


def make_historical_climatology():
    """Synthetic Phase 1 output: a single 1981-2010 baseline."""

    return pd.DataFrame(
        [
            {
                "municipality": "Vila Real",
                "month": 1,
                "variable": "tas",
                "mean_value": 8.0,
                "unit": "celsius",
                "period": "1981-2010",
            },
            {
                "municipality": "Vila Real",
                "month": 1,
                "variable": "pr",
                "mean_value": 100.0,
                "unit": "mm",
                "period": "1981-2010",
            },
        ]
    )


def test_temperature_anomaly_is_absolute_only():
    result = calculate_climate_anomalies(
        ensemble_climatology=make_ensemble_climatology(),
        historical_climatology=make_historical_climatology(),
    )

    ssp585 = result[
        (result["variable"] == "tas")
        & (result["scenario"] == "ssp585")
    ].iloc[0]

    assert ssp585["baseline_value"] == pytest.approx(8.0)
    assert ssp585["anomaly_absolute"] == pytest.approx(4.0)
    assert pd.isna(ssp585["anomaly_percent"])


def test_precipitation_anomaly_has_percent_too():
    result = calculate_climate_anomalies(
        ensemble_climatology=make_ensemble_climatology(),
        historical_climatology=make_historical_climatology(),
    )

    pr_row = result[result["variable"] == "pr"].iloc[0]

    assert pr_row["baseline_value"] == pytest.approx(100.0)
    assert pr_row["anomaly_absolute"] == pytest.approx(-10.0)
    assert pr_row["anomaly_percent"] == pytest.approx(-10.0)


def test_same_baseline_used_for_both_scenarios():
    result = calculate_climate_anomalies(
        ensemble_climatology=make_ensemble_climatology(),
        historical_climatology=make_historical_climatology(),
    )

    tas_rows = result[result["variable"] == "tas"]

    assert set(tas_rows["baseline_value"]) == {8.0}

    anomalies = dict(
        zip(tas_rows["scenario"], tas_rows["anomaly_absolute"])
    )

    assert anomalies["ssp585"] == pytest.approx(4.0)
    assert anomalies["ssp126"] == pytest.approx(1.0)


def test_missing_ensemble_column_raises_error():
    ensemble = make_ensemble_climatology().drop(columns=["scenario"])

    with pytest.raises(
        ClimateAnomalyError,
        match="ensemble_climatology is missing",
    ):
        calculate_climate_anomalies(
            ensemble_climatology=ensemble,
            historical_climatology=make_historical_climatology(),
        )


def test_missing_historical_column_raises_error():
    historical = make_historical_climatology().drop(
        columns=["mean_value"]
    )

    with pytest.raises(
        ClimateAnomalyError,
        match="historical_climatology is missing",
    ):
        calculate_climate_anomalies(
            ensemble_climatology=make_ensemble_climatology(),
            historical_climatology=historical,
        )


def test_duplicate_baseline_raises_error():
    historical = pd.concat(
        [
            make_historical_climatology(),
            make_historical_climatology(),
        ],
        ignore_index=True,
    )

    with pytest.raises(
        ClimateAnomalyError,
        match="more than one baseline row",
    ):
        calculate_climate_anomalies(
            ensemble_climatology=make_ensemble_climatology(),
            historical_climatology=historical,
        )


def test_missing_baseline_raises_error():
    historical = make_historical_climatology()
    historical = historical[historical["variable"] != "pr"]

    with pytest.raises(
        ClimateAnomalyError,
        match="No historical baseline found",
    ):
        calculate_climate_anomalies(
            ensemble_climatology=make_ensemble_climatology(),
            historical_climatology=historical,
        )
