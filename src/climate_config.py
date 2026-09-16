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
        "models",
        "variables",
        "ensemble",
        "processing",
        "pilot",
    }

    missing_sections = required_sections - config.keys()

    if missing_sections:
        raise ClimateConfigError(
            "Missing configuration sections: "
            + ", ".join(sorted(missing_sections))
        )

    future = config["future"]
    variables = config["variables"]
    models = config["models"]
    pilot = config["pilot"]

    periods = future.get("periods", [])
    scenarios = future.get("scenarios", [])
    gcms = models.get("gcms", [])

    all_variables = (
        variables.get("core", [])
        + variables.get("optional", [])
    )

    if not periods:
        raise ClimateConfigError(
            "At least one future period must be configured."
        )

    if not scenarios:
        raise ClimateConfigError(
            "At least one future scenario must be configured."
        )

    if not variables.get("core"):
        raise ClimateConfigError(
            "At least one core climate variable must be configured."
        )

    if pilot.get("variable") not in all_variables:
        raise ClimateConfigError(
            f"Pilot variable '{pilot.get('variable')}' "
            "is not configured."
        )

    if pilot.get("scenario") not in scenarios:
        raise ClimateConfigError(
            f"Pilot scenario '{pilot.get('scenario')}' "
            "is not configured."
        )

    if pilot.get("period") not in periods:
        raise ClimateConfigError(
            f"Pilot period '{pilot.get('period')}' "
            "is not configured."
        )

    pilot_gcm = pilot.get("gcm", "")

    if pilot_gcm and pilot_gcm not in gcms:
        raise ClimateConfigError(
            f"Pilot GCM '{pilot_gcm}' is not configured."
        )
