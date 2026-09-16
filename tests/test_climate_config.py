import pytest

from src.climate_config import (
    ClimateConfigError,
    _validate_climate_config,
    load_climate_config,
)


def make_valid_config():
    return {
        "project": {
            "name": "AquaHub Climate",
        },
        "historical": {
            "dataset": "CHELSA-W5E5",
            "period": "1981-2010",
        },
        "future": {
            "dataset": "CHELSA-ISIMIP3b",
            "periods": ["2041-2070"],
            "scenarios": ["ssp370"],
        },
        "models": {
            "gcms": [],
        },
        "variables": {
            "core": ["tas", "tasmin", "tasmax", "pr"],
            "optional": ["rsds"],
        },
        "ensemble": {
            "method": "equal_weight_mean",
        },
        "processing": {
            "calculate_anomalies": True,
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


def test_load_real_climate_config():
    config = load_climate_config()

    assert config["historical"]["period"] == "1981-2010"
    assert config["pilot"]["region_name"] == "Douro"
    assert config["pilot"]["variable"] == "tas"
    assert config["pilot"]["scenario"] == "ssp370"
    assert config["pilot"]["period"] == "2041-2070"
    assert config["pilot"]["gcm"] == ""


def test_missing_required_section_raises_error():
    config = make_valid_config()
    del config["future"]

    with pytest.raises(
        ClimateConfigError,
        match="Missing configuration sections",
    ):
        _validate_climate_config(config)


def test_invalid_pilot_variable_raises_error():
    config = make_valid_config()
    config["pilot"]["variable"] = "invalid_variable"

    with pytest.raises(
        ClimateConfigError,
        match="is not configured",
    ):
        _validate_climate_config(config)


def test_invalid_pilot_scenario_raises_error():
    config = make_valid_config()
    config["pilot"]["scenario"] = "ssp999"

    with pytest.raises(
        ClimateConfigError,
        match="is not configured",
    ):
        _validate_climate_config(config)


def test_invalid_pilot_period_raises_error():
    config = make_valid_config()
    config["pilot"]["period"] = "2050-2090"

    with pytest.raises(
        ClimateConfigError,
        match="is not configured",
    ):
        _validate_climate_config(config)


def test_empty_pilot_gcm_is_allowed():
    config = make_valid_config()

    _validate_climate_config(config)


def test_unconfigured_pilot_gcm_raises_error():
    config = make_valid_config()
    config["pilot"]["gcm"] = "Example-GCM"

    with pytest.raises(
        ClimateConfigError,
        match="is not configured",
    ):
        _validate_climate_config(config)
