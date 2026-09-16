from pathlib import Path

import pytest

from src.climate_paths import (
    ClimatePathError,
    build_ensemble_directory,
    build_future_processed_directory,
    build_future_raw_directory,
    slugify,
)


def make_config():
    return {
        "future": {
            "dataset": "CHELSA-ISIMIP3b",
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
    }


def test_slugify_dataset_name():
    assert slugify("CHELSA-ISIMIP3b") == "chelsa_isimip3b"


def test_build_future_raw_directory():
    config = make_config()

    result = build_future_raw_directory(
        config=config,
        gcm="MRI-ESM2-0",
        scenario="ssp370",
        variable="tas",
    )

    assert result == Path(
        "data/raw/future/"
        "chelsa_isimip3b/"
        "MRI-ESM2-0/"
        "ssp370/"
        "tas"
    )


def test_build_future_processed_directory():
    config = make_config()

    result = build_future_processed_directory(
        config=config,
        gcm="MRI-ESM2-0",
        scenario="ssp370",
        period="2041-2070",
        variable="tas",
    )

    assert result == Path(
        "data/processed/future/"
        "2041-2070/"
        "ssp370/"
        "MRI-ESM2-0/"
        "tas"
    )


def test_build_ensemble_directory():
    config = make_config()

    result = build_ensemble_directory(
        config=config,
        scenario="ssp370",
        period="2041-2070",
        variable="tas",
    )

    assert result == Path(
        "data/processed/ensemble/"
        "2041-2070/"
        "ssp370/"
        "tas"
    )


def test_invalid_scenario_raises_error():
    config = make_config()

    with pytest.raises(
        ClimatePathError,
        match="Scenario 'ssp999' is not configured",
    ):
        build_future_processed_directory(
            config=config,
            gcm="MRI-ESM2-0",
            scenario="ssp999",
            period="2041-2070",
            variable="tas",
        )


def test_invalid_period_raises_error():
    config = make_config()

    with pytest.raises(
        ClimatePathError,
        match="Period '2050-2090' is not configured",
    ):
        build_future_processed_directory(
            config=config,
            gcm="MRI-ESM2-0",
            scenario="ssp370",
            period="2050-2090",
            variable="tas",
        )


def test_invalid_variable_raises_error():
    config = make_config()

    with pytest.raises(
        ClimatePathError,
        match="Variable 'invalid_var' is not configured",
    ):
        build_future_processed_directory(
            config=config,
            gcm="MRI-ESM2-0",
            scenario="ssp370",
            period="2041-2070",
            variable="invalid_var",
        )


def test_empty_gcm_raises_error():
    config = make_config()

    with pytest.raises(
        ClimatePathError,
        match="GCM cannot be empty",
    ):
        build_future_raw_directory(
            config=config,
            gcm="",
            scenario="ssp370",
            variable="tas",
        )


def test_configured_gcm_is_accepted():
    config = make_config()
    config["models"]["gcms"] = ["MRI-ESM2-0"]

    result = build_future_raw_directory(
        config=config,
        gcm="MRI-ESM2-0",
        scenario="ssp370",
        variable="tas",
    )

    assert "MRI-ESM2-0" in result.parts


def test_unconfigured_gcm_is_rejected_when_list_exists():
    config = make_config()
    config["models"]["gcms"] = ["MRI-ESM2-0"]

    with pytest.raises(
        ClimatePathError,
        match="GCM 'Other-GCM' is not configured",
    ):
        build_future_raw_directory(
            config=config,
            gcm="Other-GCM",
            scenario="ssp370",
            variable="tas",
        )
