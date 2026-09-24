"""Loading and validation of AquaHub climate configuration."""

from pathlib import Path
import tomllib


DEFAULT_CONFIG_PATH = Path("config/climate.toml")


class ClimateConfigError(ValueError):
    """Raised when the climate configuration is invalid."""


def load_climate_config(
    config_path: str | Path = DEFAULT_CONFIG_PATH,
) -> dict:
    """Load and validate the AquaHub climate TOML configuration."""

    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Climate configuration file not found: {path}"
        )

    with path.open("rb") as file:
        config = tomllib.load(file)

    _validate_climate_config(config)

    return config


def _validate_climate_config(config: dict) -> None:
    """Validate required sections and cross-references."""

    required_sections = {
        "project",
        "historical",
        "future",
    }

    missing_sections = required_sections - config.keys()

    if missing_sections:
        raise ClimateConfigError(
            "Missing configuration sections: "
            + ", ".join(sorted(missing_sections))
        )

    future = config["future"]
    periods = future.get("periods", [])
    scenarios = future.get("scenarios", [])

    if not periods:
        raise ClimateConfigError(
            "At least one future period must be configured."
        )

    if not scenarios:
        raise ClimateConfigError(
            "At least one future scenario must be configured."
        )
