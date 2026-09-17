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


if WEB_DIR.exists():
    app.mount(
        "/",
        StaticFiles(directory=WEB_DIR, html=True),
        name="web",
    )
