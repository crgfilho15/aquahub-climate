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
            "periods": ["2041-2070"],
            "scenarios": ["ssp585"],
        },
    }


def test_load_real_climate_config():
    config = load_climate_config()

    assert config["historical"]["period"] == "1981-2010"
    assert config["future"]["periods"] == ["2041-2070", "2071-2100"]
    assert config["future"]["scenarios"] == ["ssp126", "ssp585"]


def test_missing_required_section_raises_error():
    config = make_valid_config()
    del config["future"]

    with pytest.raises(
        ClimateConfigError,
        match="Missing configuration sections",
    ):
        _validate_climate_config(config)


def test_missing_future_periods_raises_error():
    config = make_valid_config()
    config["future"]["periods"] = []

    with pytest.raises(
        ClimateConfigError,
        match="At least one future period must be configured",
    ):
        _validate_climate_config(config)


def test_missing_future_scenarios_raises_error():
    config = make_valid_config()
    config["future"]["scenarios"] = []

    with pytest.raises(
        ClimateConfigError,
        match="At least one future scenario must be configured",
    ):
        _validate_climate_config(config)
