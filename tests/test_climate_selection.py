import pytest

from src.climate_selection import (
    ClimateSelectionError,
    FutureClimateSelection,
)


def make_config():
    return {
        "future": {
            "periods": [
                "2011-2040",
                "2041-2070",
                "2071-2100",
            ],
            "scenarios": [
                "ssp126",
                "ssp370",
                "ssp585",
            ],
        },
        "models": {
            "gcms": [],
        },
        "variables": {
            "core": [
                "tas",
                "tasmin",
                "tasmax",
                "pr",
            ],
            "optional": [
                "rsds",
                "pet",
                "cmi",
            ],
        },
        "pilot": {
            "region_type": "NUTS3",
            "region_name": "Douro",
            "variable": "tas",
            "scenario": "ssp370",
            "period": "2041-2070",
            "gcm": "",
        },
    }


def test_create_selection_from_pilot():
    config = make_config()

    selection = FutureClimateSelection.from_pilot(
        config,
        "MRI-ESM2-0",
    )

    assert selection.gcm == "MRI-ESM2-0"
    assert selection.scenario == "ssp370"
    assert selection.period == "2041-2070"
    assert selection.variable == "tas"
    assert selection.region_type == "NUTS3"
    assert selection.region_name == "Douro"


def test_experiment_id():
    config = make_config()

    selection = FutureClimateSelection.from_pilot(
        config,
        "MRI-ESM2-0",
    )

    assert (
        selection.experiment_id
        == "Douro_tas_MRI-ESM2-0_ssp370_2041-2070"
    )


def test_empty_gcm_raises_error():
    config = make_config()

    with pytest.raises(
        ClimateSelectionError,
        match="GCM cannot be empty",
    ):
        FutureClimateSelection.from_pilot(
            config,
            "",
        )


def test_invalid_scenario_raises_error():
    config = make_config()
    config["pilot"]["scenario"] = "ssp999"

    with pytest.raises(
        ClimateSelectionError,
        match="Scenario 'ssp999' is not configured",
    ):
        FutureClimateSelection.from_pilot(
            config,
            "MRI-ESM2-0",
        )


def test_invalid_period_raises_error():
    config = make_config()
    config["pilot"]["period"] = "2050-2090"

    with pytest.raises(
        ClimateSelectionError,
        match="Period '2050-2090' is not configured",
    ):
        FutureClimateSelection.from_pilot(
            config,
            "MRI-ESM2-0",
        )


def test_invalid_variable_raises_error():
    config = make_config()
    config["pilot"]["variable"] = "invalid_var"

    with pytest.raises(
        ClimateSelectionError,
        match="Variable 'invalid_var' is not configured",
    ):
        FutureClimateSelection.from_pilot(
            config,
            "MRI-ESM2-0",
        )


def test_unconfigured_gcm_is_rejected_when_list_exists():
    config = make_config()
    config["models"]["gcms"] = ["MRI-ESM2-0"]

    with pytest.raises(
        ClimateSelectionError,
        match="GCM 'Other-GCM' is not configured",
    ):
        FutureClimateSelection.from_pilot(
            config,
            "Other-GCM",
        )


def test_selection_is_immutable():
    config = make_config()

    selection = FutureClimateSelection.from_pilot(
        config,
        "MRI-ESM2-0",
    )

    with pytest.raises(Exception):
        selection.gcm = "Other-GCM"
