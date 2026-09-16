from pathlib import Path

import pytest

from src.climate_selection import (
    ClimateSelectionError,
    FutureClimateSelection,
)
from src.future_climate_experiment import (
    FutureClimateExperiment,
)


def make_config():
    return {
        "future": {
            "dataset": "CHELSA-climatologies-v2.1-CMIP6",
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


def test_create_future_climate_experiment():
    config = make_config()

    selection = FutureClimateSelection.from_pilot(
        config,
        "MRI-ESM2-0",
    )

    experiment = FutureClimateExperiment.from_selection(
        config,
        selection,
    )

    assert experiment.selection == selection

    assert experiment.raw_directory == Path(
        "data/raw/future/"
        "chelsa_climatologies_v2_1_cmip6/"
        "MRI-ESM2-0/"
        "ssp370/"
        "tas"
    )

    assert experiment.processed_directory == Path(
        "data/processed/future/"
        "2041-2070/"
        "ssp370/"
        "MRI-ESM2-0/"
        "tas"
    )

    assert experiment.ensemble_directory == Path(
        "data/processed/ensemble/"
        "2041-2070/"
        "ssp370/"
        "tas"
    )


def test_experiment_id_matches_selection():
    config = make_config()

    selection = FutureClimateSelection.from_pilot(
        config,
        "MRI-ESM2-0",
    )

    experiment = FutureClimateExperiment.from_selection(
        config,
        selection,
    )

    assert (
        experiment.experiment_id
        == "Douro_tas_MRI-ESM2-0_ssp370_2041-2070"
    )


def test_experiment_revalidates_selection():
    config = make_config()

    selection = FutureClimateSelection(
        gcm="MRI-ESM2-0",
        scenario="ssp999",
        period="2041-2070",
        variable="tas",
        region_type="NUTS3",
        region_name="Douro",
    )

    with pytest.raises(
        ClimateSelectionError,
        match="Scenario 'ssp999' is not configured",
    ):
        FutureClimateExperiment.from_selection(
            config,
            selection,
        )


def test_experiment_is_immutable():
    config = make_config()

    selection = FutureClimateSelection.from_pilot(
        config,
        "MRI-ESM2-0",
    )

    experiment = FutureClimateExperiment.from_selection(
        config,
        selection,
    )

    with pytest.raises(Exception):
        experiment.raw_directory = Path("other")
