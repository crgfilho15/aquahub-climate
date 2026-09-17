import pandas as pd
import pytest

from src.bioclimatic_indices import (
    BioclimaticIndexError,
    DAYS_PER_MONTH,
    calculate_growing_degree_days,
    calculate_growing_season_precipitation,
    calculate_winkler_index,
)


def make_monthly_climatology():
    """
    Synthetic monthly climatology for one municipality, constant 15°C
    every month. April-October (7 months: 30+31+30+31+31+30+31 = 214
    days) at (15-10)=5 degree-days/day gives GDD = 214 * 5 = 1070.
    """

    return pd.DataFrame(
        {
            "municipality": ["Vila Real"] * 12,
            "month": range(1, 13),
            "mean_value": [15.0] * 12,
        }
    )


def test_growing_degree_days_basic():
    result = calculate_growing_degree_days(
        monthly_climatology=make_monthly_climatology(),
    )

    assert len(result) == 1

    row = result.iloc[0]

    assert row["municipality"] == "Vila Real"
    assert row["growing_degree_days"] == pytest.approx(1070.0)
    assert row["base_temperature"] == pytest.approx(10.0)


def test_growing_degree_days_clips_below_base_to_zero():
    monthly = make_monthly_climatology()
    monthly.loc[monthly["month"] == 4, "mean_value"] = 5.0

    result = calculate_growing_degree_days(
        monthly_climatology=monthly,
    )

    # April (30 days) contributes 0 instead of a negative value.
    expected = (
        1070.0 - (15.0 - 10.0) * DAYS_PER_MONTH[4]
    )

    assert result.iloc[0]["growing_degree_days"] == pytest.approx(
        expected
    )


def test_growing_degree_days_custom_base_and_season():
    monthly = make_monthly_climatology()

    result = calculate_growing_degree_days(
        monthly_climatology=monthly,
        base_temperature=0.0,
        season_months=[1, 2],
    )

    expected = 15.0 * (DAYS_PER_MONTH[1] + DAYS_PER_MONTH[2])

    assert result.iloc[0]["growing_degree_days"] == pytest.approx(
        expected
    )


def test_winkler_index_matches_gdd_with_fixed_parameters():
    monthly = make_monthly_climatology()

    winkler = calculate_winkler_index(monthly_climatology=monthly)
    gdd = calculate_growing_degree_days(
        monthly_climatology=monthly,
        base_temperature=10.0,
        season_months=range(4, 11),
    )

    assert "winkler_index" in winkler.columns
    assert "growing_degree_days" not in winkler.columns

    assert winkler.iloc[0]["winkler_index"] == pytest.approx(
        gdd.iloc[0]["growing_degree_days"]
    )


def test_growing_season_precipitation_sums_only_season_months():
    monthly = pd.DataFrame(
        {
            "municipality": ["Vila Real"] * 12,
            "month": range(1, 13),
            "mean_value": [100.0] * 12,
        }
    )

    result = calculate_growing_season_precipitation(
        monthly_climatology=monthly,
    )

    # April-October = 7 months of 100 mm each.
    assert result.iloc[0][
        "growing_season_precipitation"
    ] == pytest.approx(700.0)


def test_indices_keep_groups_separate_for_ensemble_input():
    monthly = pd.DataFrame(
        [
            {
                "municipality": "Vila Real",
                "month": month,
                "scenario": scenario,
                "period": "2041-2070",
                "ensemble_mean": value,
            }
            for month in range(1, 13)
            for scenario, value in [("ssp126", 12.0), ("ssp585", 20.0)]
        ]
    )

    result = calculate_growing_degree_days(
        monthly_climatology=monthly,
        value_column="ensemble_mean",
        group_columns=["municipality", "scenario", "period"],
    )

    assert len(result) == 2

    by_scenario = dict(
        zip(result["scenario"], result["growing_degree_days"])
    )

    assert by_scenario["ssp585"] > by_scenario["ssp126"]


def test_missing_required_column_raises_error():
    monthly = make_monthly_climatology().drop(columns=["month"])

    with pytest.raises(
        BioclimaticIndexError,
        match="missing required column",
    ):
        calculate_growing_degree_days(monthly_climatology=monthly)


def test_invalid_season_month_raises_error():
    with pytest.raises(
        BioclimaticIndexError,
        match="invalid month",
    ):
        calculate_growing_degree_days(
            monthly_climatology=make_monthly_climatology(),
            season_months=[0, 13],
        )


def test_empty_season_selection_raises_error():
    monthly = make_monthly_climatology()
    monthly = monthly[monthly["month"] <= 3]

    with pytest.raises(
        BioclimaticIndexError,
        match="No rows",
    ):
        calculate_growing_degree_days(
            monthly_climatology=monthly,
            season_months=range(4, 11),
        )
