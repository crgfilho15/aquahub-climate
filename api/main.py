"""FastAPI backend for the AquaHub interactive pilot platform.

Serves the pre-generated pilot GeoJSON/metadata (produced locally by
scripts/build_pilot_region.py, where CHELSA and CAOP data are
available) and the static frontend in web/.

Regions are driven by config/climate.toml's
[[pilot_platform.regions]] list - never trust the 'region' path
parameter directly for filesystem access; only configured slugs are
ever used to build a file path.
"""

import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.climate_config import load_climate_config

APP_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = APP_ROOT / "web"

BUILD_HINT_TEMPLATE = (
    "Pilot data for '{region}' not found. Run "
    "'python -m scripts.build_pilot_region --region {region}' locally "
    "(where data/raw/chelsa and data/raw/boundaries are "
    "available), then restart this API."
)

app = FastAPI(title="AquaHub Climate Pilot API")


def get_pilot_data_dir() -> Path:
    """
    Directory containing the generated pilot artefacts.

    Overridable via AQUAHUB_PILOT_DATA_DIR, primarily for tests.
    """

    override = os.environ.get("AQUAHUB_PILOT_DATA_DIR")

    if override:
        return Path(override)

    return APP_ROOT / "data" / "processed" / "pilot"


def get_configured_regions() -> list[dict]:
    """Regions declared in config/climate.toml, regardless of
    whether their pilot data has been built yet."""

    config = load_climate_config()

    return config["pilot_platform"]["regions"]


def _region_slug_or_404(region: str) -> str:
    configured_slugs = {
        r["slug"] for r in get_configured_regions()
    }

    if region not in configured_slugs:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Unknown pilot region: '{region}'. "
                f"Configured regions: {sorted(configured_slugs)}"
            ),
        )

    return region


def _read_pilot_json(region: str, suffix: str) -> dict:
    path = get_pilot_data_dir() / f"{region}_{suffix}"

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=BUILD_HINT_TEMPLATE.format(region=region),
        )

    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/pilot")
def list_available_pilot_regions() -> JSONResponse:
    """Regions that are both configured and have built pilot data."""

    data_dir = get_pilot_data_dir()

    available = [
        {"slug": region["slug"], "label": region["label"]}
        for region in get_configured_regions()
        if (data_dir / f"{region['slug']}_pilot.geojson").exists()
    ]

    return JSONResponse(available)


ZONES_BUILD_HINT = (
    "Zone overview not found. Run "
    "'python -m scripts.build_zone_overview' locally, then restart "
    "this API."
)


@app.get("/api/pilot/zones")
def get_zone_overview() -> JSONResponse:
    """
    All configured zones with known geometry, for the single all-zones
    map (see scripts/build_zone_overview.py). Zones without built
    climate data (e.g. Castilla y León/Extremadura today) are still
    included if their outline is known, marked "built": false.
    """

    path = get_pilot_data_dir() / "zones_overview.geojson"

    if not path.exists():
        raise HTTPException(status_code=404, detail=ZONES_BUILD_HINT)

    return JSONResponse(json.loads(path.read_text(encoding="utf-8")))


@app.get("/api/pilot/{region}")
def get_pilot_geojson(region: str) -> JSONResponse:
    region = _region_slug_or_404(region)

    return JSONResponse(
        _read_pilot_json(region, "pilot.geojson")
    )


@app.get("/api/pilot/{region}/meta")
def get_pilot_metadata(region: str) -> JSONResponse:
    region = _region_slug_or_404(region)

    return JSONResponse(
        _read_pilot_json(region, "pilot_meta.json")
    )


def get_future_pilot_data_dir() -> Path:
    """
    Directory containing generated future/ensemble/anomaly pilot
    artefacts (src/future_pilot_export.py's output). Overridable via
    AQUAHUB_FUTURE_PILOT_DATA_DIR, primarily for tests.
    """

    override = os.environ.get("AQUAHUB_FUTURE_PILOT_DATA_DIR")

    if override:
        return Path(override)

    return get_pilot_data_dir() / "future"


def _future_slice_or_404(
    variable: str,
    scenario: str,
    period: str,
) -> tuple[str, str, str]:
    """
    Validate variable/scenario/period against config/climate.toml
    before ever using them to build a file path - same allow-list
    principle _region_slug_or_404 applies to the region slug.
    """

    config = load_climate_config()

    configured_variables = set(
        config["variables"].get("core", [])
        + config["variables"].get("optional", [])
    )
    configured_scenarios = set(config["future"]["scenarios"])
    configured_periods = set(config["future"]["periods"])

    if variable not in configured_variables:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Unknown variable: '{variable}'. "
                f"Configured variables: {sorted(configured_variables)}"
            ),
        )

    if scenario not in configured_scenarios:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Unknown scenario: '{scenario}'. "
                f"Configured scenarios: {sorted(configured_scenarios)}"
            ),
        )

    if period not in configured_periods:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Unknown period: '{period}'. "
                f"Configured periods: {sorted(configured_periods)}"
            ),
        )

    return variable, scenario, period


FUTURE_BUILD_HINT_TEMPLATE = (
    "Future pilot data for '{region}' ({variable}/{scenario}/{period}) "
    "not found. Run 'python -m scripts.build_future_pilot_data --region "
    "{region} --variable {variable} --scenario {scenario} --period "
    "{period}' locally, then restart this API."
)


def _read_future_pilot_json(
    region: str,
    variable: str,
    scenario: str,
    period: str,
    suffix: str,
) -> dict:
    stem = f"{region}_{variable}_{scenario}_{period}_future"
    path = get_future_pilot_data_dir() / f"{stem}{suffix}"

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=FUTURE_BUILD_HINT_TEMPLATE.format(
                region=region,
                variable=variable,
                scenario=scenario,
                period=period,
            ),
        )

    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/pilot/{region}/future")
def list_available_future_slices(region: str) -> JSONResponse:
    """
    (variable, scenario, period) combinations that are both
    configured and have built future pilot data for this region.
    """

    region = _region_slug_or_404(region)

    config = load_climate_config()
    data_dir = get_future_pilot_data_dir()

    variables = (
        config["variables"].get("core", [])
        + config["variables"].get("optional", [])
    )
    scenarios = config["future"]["scenarios"]
    periods = config["future"]["periods"]

    available = [
        {"variable": variable, "scenario": scenario, "period": period}
        for variable in variables
        for scenario in scenarios
        for period in periods
        if (
            data_dir
            / f"{region}_{variable}_{scenario}_{period}_future.geojson"
        ).exists()
    ]

    return JSONResponse(available)


@app.get("/api/pilot/{region}/future/{variable}/{scenario}/{period}")
def get_future_pilot_geojson(
    region: str,
    variable: str,
    scenario: str,
    period: str,
) -> JSONResponse:
    region = _region_slug_or_404(region)
    variable, scenario, period = _future_slice_or_404(
        variable, scenario, period
    )

    return JSONResponse(
        _read_future_pilot_json(
            region, variable, scenario, period, ".geojson"
        )
    )


@app.get("/api/pilot/{region}/future/{variable}/{scenario}/{period}/meta")
def get_future_pilot_metadata(
    region: str,
    variable: str,
    scenario: str,
    period: str,
) -> JSONResponse:
    region = _region_slug_or_404(region)
    variable, scenario, period = _future_slice_or_404(
        variable, scenario, period
    )

    return JSONResponse(
        _read_future_pilot_json(
            region, variable, scenario, period, "_meta.json"
        )
    )


if WEB_DIR.exists():
    app.mount(
        "/",
        StaticFiles(directory=WEB_DIR, html=True),
        name="web",
    )
