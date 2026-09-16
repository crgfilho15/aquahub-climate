"""Path construction utilities for AquaHub climate datasets."""

from pathlib import Path
import re


RAW_FUTURE_ROOT = Path("data/raw/future")
PROCESSED_FUTURE_ROOT = Path("data/processed/future")
ENSEMBLE_ROOT = Path("data/processed/ensemble")


class ClimatePathError(ValueError):
    """Raised when a climate data path cannot be constructed safely."""


def slugify(value: str) -> str:
    """Convert a configuration label into a filesystem-safe slug."""

    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)

    return value.strip("_")


def build_future_raw_directory(
    config: dict,
    gcm: str,
    scenario: str,
    variable: str,
    root: str | Path = RAW_FUTURE_ROOT,
) -> Path:
    """Build the directory for original future climate files."""

    _validate_future_selection(
        config=config,
        gcm=gcm,
        scenario=scenario,
        variable=variable,
    )

    dataset = slugify(config["future"]["dataset"])

    return (
        Path(root)
        / dataset
        / gcm
        / scenario
        / variable
    )


def build_future_processed_directory(
    config: dict,
    gcm: str,
    scenario: str,
    period: str,
    variable: str,
    root: str | Path = PROCESSED_FUTURE_ROOT,
) -> Path:
    """Build the directory for processed future climate products."""

    _validate_future_selection(
        config=config,
        gcm=gcm,
        scenario=scenario,
        period=period,
        variable=variable,
    )

    return (
        Path(root)
        / period
        / scenario
        / gcm
        / variable
    )


def build_ensemble_directory(
    config: dict,
    scenario: str,
    period: str,
    variable: str,
    root: str | Path = ENSEMBLE_ROOT,
) -> Path:
    """Build the directory for multimodel ensemble products."""

    _validate_future_selection(
        config=config,
        scenario=scenario,
        period=period,
        variable=variable,
    )

    return (
        Path(root)
        / period
        / scenario
        / variable
    )


def _validate_future_selection(
    config: dict,
    scenario: str,
    variable: str,
    period: str | None = None,
    gcm: str | None = None,
) -> None:
    """Validate a future climate processing selection."""

    future = config["future"]
    variables = config["variables"]
    configured_gcms = config["models"].get("gcms", [])

    all_variables = (
        variables.get("core", [])
        + variables.get("optional", [])
    )

    if scenario not in future["scenarios"]:
        raise ClimatePathError(
            f"Scenario '{scenario}' is not configured."
        )

    if variable not in all_variables:
        raise ClimatePathError(
            f"Variable '{variable}' is not configured."
        )

    if period is not None and period not in future["periods"]:
        raise ClimatePathError(
            f"Period '{period}' is not configured."
        )

    if gcm is not None:
        if not gcm.strip():
            raise ClimatePathError(
                "GCM cannot be empty when building a model-specific path."
            )

        if configured_gcms and gcm not in configured_gcms:
            raise ClimatePathError(
                f"GCM '{gcm}' is not configured."
            )
