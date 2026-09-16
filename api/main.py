"""FastAPI backend for the AquaHub Douro pilot platform.

Serves the pre-generated pilot GeoJSON/metadata (produced locally by
scripts/build_pilot_douro.py, where CHELSA and CAOP data are
available) and the static frontend in web/.
"""

import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

APP_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = APP_ROOT / "web"

REGION_SLUG = "douro"

BUILD_HINT = (
    "Pilot data not found. Run "
    "'python -m scripts.build_pilot_douro' locally "
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


def _read_pilot_json(filename: str) -> dict:
    path = get_pilot_data_dir() / filename

    if not path.exists():
        raise HTTPException(status_code=404, detail=BUILD_HINT)

    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/pilot/{region}")
def get_pilot_geojson(region: str) -> JSONResponse:
    if region != REGION_SLUG:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown pilot region: {region}",
        )

    return JSONResponse(
        _read_pilot_json(f"{region}_pilot.geojson")
    )


@app.get("/api/pilot/{region}/meta")
def get_pilot_metadata(region: str) -> JSONResponse:
    if region != REGION_SLUG:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown pilot region: {region}",
        )

    return JSONResponse(
        _read_pilot_json(f"{region}_pilot_meta.json")
    )


if WEB_DIR.exists():
    app.mount(
        "/",
        StaticFiles(directory=WEB_DIR, html=True),
        name="web",
    )
