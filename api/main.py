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

import numpy as np
import rasterio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
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
app.add_middleware(GZipMiddleware, minimum_size=1000)


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


def get_indices_catalog_path() -> Path:
    """
    Path to the professor's crop-index catalog (src/indices_catalog.py
    + scripts/build_indices_catalog.py's output). Overridable via
    AQUAHUB_INDICES_CATALOG_PATH, primarily for tests.
    """

    override = os.environ.get("AQUAHUB_INDICES_CATALOG_PATH")

    if override:
        return Path(override)

    return get_pilot_data_dir() / "indices_catalog.json"


def get_index_pilot_data_dir() -> Path:
    """
    Directory containing the per-zone/epoch index rasters and stats
    (scripts/build_index_pilot_data.py's output). Overridable via
    AQUAHUB_INDEX_PILOT_DATA_DIR, primarily for tests.
    """

    override = os.environ.get("AQUAHUB_INDEX_PILOT_DATA_DIR")

    if override:
        return Path(override)

    return get_pilot_data_dir() / "indices"


INDICES_CATALOG_BUILD_HINT = (
    "Indices catalog not found. Run "
    "'python -m scripts.build_indices_catalog' locally, then restart "
    "this API."
)


@app.get("/api/indices")
def get_indices_catalog() -> JSONResponse:
    """
    The professor's crop-index catalog: code, name, formula,
    reference and per-crop relevance for every delivered bioclimatic
    index (see src/indices_catalog.py - content is in Portuguese as
    delivered, not yet translated, see docs/04 Phase 7).
    """

    path = get_indices_catalog_path()

    if not path.exists():
        raise HTTPException(
            status_code=404, detail=INDICES_CATALOG_BUILD_HINT
        )

    return JSONResponse(json.loads(path.read_text(encoding="utf-8")))


def _index_code_or_404(code: str) -> str:
    path = get_indices_catalog_path()

    if not path.exists():
        raise HTTPException(
            status_code=404, detail=INDICES_CATALOG_BUILD_HINT
        )

    catalog = json.loads(path.read_text(encoding="utf-8"))

    if code not in catalog.get("indices", {}):
        raise HTTPException(
            status_code=404,
            detail=f"Unknown index code: '{code}'.",
        )

    return code


def _scenario_period_or_404(scenario: str, period: str) -> tuple[str, str]:
    config = load_climate_config()

    configured_scenarios = set(config["future"]["scenarios"])
    configured_periods = set(config["future"]["periods"])

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

    return scenario, period


INDEX_BUILD_HINT_TEMPLATE = (
    "Index pilot data for '{code}' ({epoch}) not found. Run "
    "'python -m scripts.build_index_pilot_data' locally, then restart "
    "this API."
)


def _read_zone_index_grid(slug: str, code: str, epoch: str) -> dict | None:
    """
    One zone's grid for one index/epoch: bounds, width/height, the
    decoded value grid (NaN as null), and mean/min/max. Returns None
    (not a 404 by itself - the caller decides) if this zone/epoch
    hasn't been built yet, so a partially-delivered epoch still shows
    whichever zones *are* ready instead of failing outright.
    """

    data_dir = get_index_pilot_data_dir()
    raster_path = data_dir / f"{slug}_{epoch}.tif"
    stats_path = data_dir / f"{slug}_{epoch}_stats.json"

    if not raster_path.exists() or not stats_path.exists():
        return None

    stats = json.loads(stats_path.read_text(encoding="utf-8"))

    if code not in stats:
        return None

    with rasterio.open(raster_path) as src:
        band_names = list(src.descriptions)

        if code not in band_names:
            return None

        band_index = band_names.index(code) + 1
        raw = src.read(band_index)
        scale = src.scales[band_index - 1]
        offset = src.offsets[band_index - 1]
        nodata = src.nodata
        bounds = src.bounds
        width, height = src.width, src.height

    decoded = np.where(raw == nodata, np.nan, raw * scale + offset)

    values = [
        [None if np.isnan(v) else round(float(v), 3) for v in row]
        for row in decoded
    ]

    zone_stats = stats[code]

    return {
        "slug": slug,
        "bounds": {
            "west": bounds.left,
            "south": bounds.bottom,
            "east": bounds.right,
            "north": bounds.top,
        },
        "width": width,
        "height": height,
        "values": values,
        "mean": round(float(zone_stats["mean"]), 3),
        "min": round(float(zone_stats["min"]), 3),
        "max": round(float(zone_stats["max"]), 3),
    }


def _get_zones_index(code: str, epoch: str) -> JSONResponse:
    code = _index_code_or_404(code)

    zone_grids = []

    for region in get_configured_regions():
        grid = _read_zone_index_grid(region["slug"], code, epoch)

        if grid is not None:
            grid["label"] = region["label"]
            zone_grids.append(grid)

    if not zone_grids:
        raise HTTPException(
            status_code=404,
            detail=INDEX_BUILD_HINT_TEMPLATE.format(code=code, epoch=epoch),
        )

    return JSONResponse(
        {
            "code": code,
            "epoch": epoch,
            "global_min": min(z["min"] for z in zone_grids),
            "global_max": max(z["max"] for z in zone_grids),
            "zones": zone_grids,
        }
    )


@app.get("/api/pilot/zones/index/{code}")
def get_zones_index_historical(code: str) -> JSONResponse:
    """All 5 zones' grid + stats for one index, historical (1981-2010)."""

    return _get_zones_index(code, epoch="historical")


@app.get("/api/pilot/zones/index/{code}/{scenario}/{period}")
def get_zones_index_future(
    code: str, scenario: str, period: str
) -> JSONResponse:
    """All 5 zones' grid + stats for one index, one future scenario/period."""

    scenario, period = _scenario_period_or_404(scenario, period)

    return _get_zones_index(code, epoch=f"{scenario}_{period}")


def _get_index_point(
    region: str, code: str, epoch: str, lat: float, lon: float
) -> JSONResponse:
    region = _region_slug_or_404(region)
    code = _index_code_or_404(code)

    raster_path = get_index_pilot_data_dir() / f"{region}_{epoch}.tif"

    if not raster_path.exists():
        raise HTTPException(
            status_code=404,
            detail=INDEX_BUILD_HINT_TEMPLATE.format(code=code, epoch=epoch),
        )

    with rasterio.open(raster_path) as src:
        band_names = list(src.descriptions)

        if code not in band_names:
            raise HTTPException(
                status_code=404,
                detail=f"Index '{code}' not present in {raster_path.name}.",
            )

        band_index = band_names.index(code) + 1
        row, col = src.index(lon, lat)

        if not (0 <= row < src.height and 0 <= col < src.width):
            raise HTTPException(
                status_code=404,
                detail="Point is outside this zone's raster extent.",
            )

        raw = src.read(
            band_index, window=((row, row + 1), (col, col + 1))
        )[0, 0]
        scale = src.scales[band_index - 1]
        offset = src.offsets[band_index - 1]
        nodata = src.nodata

    if raw == nodata:
        raise HTTPException(
            status_code=404,
            detail="No data at this point (outside the zone polygon).",
        )

    return JSONResponse(
        {
            "region": region,
            "code": code,
            "epoch": epoch,
            "lat": lat,
            "lon": lon,
            "value": round(float(raw) * scale + offset, 3),
        }
    )


@app.get("/api/pilot/{region}/index/{code}/point")
def get_index_point_historical(
    region: str, code: str, lat: float, lon: float
) -> JSONResponse:
    """Exact pixel value at (lat, lon) for one index, historical."""

    return _get_index_point(region, code, "historical", lat, lon)


@app.get("/api/pilot/{region}/index/{code}/{scenario}/{period}/point")
def get_index_point_future(
    region: str,
    code: str,
    scenario: str,
    period: str,
    lat: float,
    lon: float,
) -> JSONResponse:
    """Exact pixel value at (lat, lon) for one index, one future
    scenario/period."""

    scenario, period = _scenario_period_or_404(scenario, period)

    return _get_index_point(
        region, code, f"{scenario}_{period}", lat, lon
    )


if WEB_DIR.exists():
    app.mount(
        "/",
        StaticFiles(directory=WEB_DIR, html=True),
        name="web",
    )
