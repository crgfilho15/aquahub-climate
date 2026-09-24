"""FastAPI backend for the AquaHub Climate Atlas.

Serves the pre-generated zone overview (produced locally by
scripts/build_pilot_region.py + scripts/build_zone_overview.py) and
the professor's ingested bioclimatic-index rasters/catalog
(scripts/build_indices_catalog.py + scripts/build_index_pilot_data.py)
- everything read straight off disk, no database, plus the static
frontend in web/.

Regions are driven by config/climate.toml's
[[pilot_platform.regions]] list - never trust the 'region' path
parameter directly for filesystem access; only configured slugs are
ever used to build a file path.
"""

import json
import os
import tempfile
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import tifffile
from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.climate_config import load_climate_config

APP_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = APP_ROOT / "web"

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

# Public (read-only, no auth needed) base URL for the index rasters in
# Vercel Blob storage. The deployed function no longer bundles these
# ~136MB+ .tif files locally (that's what blew past Vercel's 500MB/
# 225MB function-size limits, Sept 2026) - they're uploaded there once
# (see scripts/build_index_pilot_data.py's own local output, pushed to
# Blob out of band) and fetched on demand instead. Overridable via
# AQUAHUB_INDEX_BLOB_BASE_URL for tests or a future store rotation.
INDEX_BLOB_BASE_URL = os.environ.get(
    "AQUAHUB_INDEX_BLOB_BASE_URL",
    "https://7qpbuykrpwwiycz7.public.blob.vercel-storage.com/indices",
)


def _get_index_blob_cache_dir() -> Path:
    """
    Local cache for rasters fetched from Blob storage. Vercel's
    deployed function only has tempfile.gettempdir() (/tmp) writable;
    that directory persists across requests on the same warm
    container, so a given raster is downloaded at most once per
    container, not once per request.
    """

    cache_dir = Path(tempfile.gettempdir()) / "aquahub_index_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _resolve_raster_path(filename: str) -> Path | None:
    """
    Find `filename` (e.g. "douro_historical.tif") locally first -
    the normal case for local dev, where
    scripts/build_index_pilot_data.py already wrote it to
    get_index_pilot_data_dir(). If it isn't there, fetch it from Blob
    storage once and cache it locally for subsequent requests.

    Returns None if the file exists in neither place, so callers can
    fall back to the same "not built yet" 404 behaviour as before.
    """

    local_path = get_index_pilot_data_dir() / filename

    if local_path.exists():
        return local_path

    cache_path = _get_index_blob_cache_dir() / filename

    if cache_path.exists():
        return cache_path

    url = f"{INDEX_BLOB_BASE_URL}/{filename}"
    partial_path = cache_path.with_name(cache_path.name + ".part")

    try:
        urllib.request.urlretrieve(url, partial_path)
    except (urllib.error.URLError, OSError):
        partial_path.unlink(missing_ok=True)
        return None

    partial_path.rename(cache_path)
    return cache_path


def _read_index_raster(raster_path: Path) -> dict:
    """
    Decode one of our multi-band index GeoTIFFs (single-page,
    band-interleaved uint16, written by src/index_pilot_export.py) via
    tifffile + plain TIFF/GDAL tag parsing - deliberately not
    rasterio, whose bundled GDAL needs a system libexpat.so.1 that
    isn't present on Vercel's Python runtime. Confirmed against the
    real public.ecr.aws/lambda/python:3.12 image (Sept 2026): importing
    rasterio there raises `ImportError: libexpat.so.1: cannot open
    shared object file`, which crashed the entire deployed app (every
    route, including static files) since the failure happens at
    module-import time. tifffile has no such native dependency.

    Our rasters are always plain EPSG:4326 (lat/lon) - no CRS/
    reprojection machinery is needed, just the affine transform's two
    GeoTIFF tags (ModelPixelScaleTag, ModelTiepointTag).
    """

    with tifffile.TiffFile(str(raster_path)) as tif:
        page = tif.pages[0]
        array = page.asarray()
        tags = page.tags
        pixel_scale = tags["ModelPixelScaleTag"].value
        tie_point = tags["ModelTiepointTag"].value
        gdal_metadata_xml = tags["GDAL_METADATA"].value
        nodata = float(tags["GDAL_NODATA"].value)
        width = page.imagewidth
        height = page.imagelength

    if array.ndim == 2:
        array = array[:, :, np.newaxis]

    pixel_width, pixel_height = pixel_scale[0], pixel_scale[1]
    west, north = tie_point[3], tie_point[4]
    bounds = {
        "west": west,
        "north": north,
        "east": west + width * pixel_width,
        "south": north - height * pixel_height,
    }

    band_count = array.shape[-1]
    band_names: list[str | None] = [None] * band_count
    scales = [1.0] * band_count
    offsets = [0.0] * band_count

    for item in ET.fromstring(gdal_metadata_xml).findall("Item"):
        sample = int(item.get("sample", "0"))
        role = item.get("role")

        if role == "description":
            band_names[sample] = item.text
        elif role == "scale":
            scales[sample] = float(item.text)
        elif role == "offset":
            offsets[sample] = float(item.text)

    return {
        "array": array,
        "band_names": band_names,
        "scales": scales,
        "offsets": offsets,
        "nodata": nodata,
        "bounds": bounds,
        "width": width,
        "height": height,
        "pixel_width": pixel_width,
        "pixel_height": pixel_height,
    }


def _read_zone_index_grid(slug: str, code: str, epoch: str) -> dict | None:
    """
    One zone's grid for one index/epoch: bounds, width/height, the
    decoded value grid (NaN as null), and mean/min/max. Returns None
    (not a 404 by itself - the caller decides) if this zone/epoch
    hasn't been built yet, so a partially-delivered epoch still shows
    whichever zones *are* ready instead of failing outright.
    """

    data_dir = get_index_pilot_data_dir()
    stats_path = data_dir / f"{slug}_{epoch}_stats.json"

    if not stats_path.exists():
        return None

    raster_path = _resolve_raster_path(f"{slug}_{epoch}.tif")

    if raster_path is None:
        return None

    stats = json.loads(stats_path.read_text(encoding="utf-8"))

    if code not in stats:
        return None

    raster = _read_index_raster(raster_path)
    band_names = raster["band_names"]

    if code not in band_names:
        return None

    band_index = band_names.index(code)
    raw = raster["array"][:, :, band_index]
    scale = raster["scales"][band_index]
    offset = raster["offsets"][band_index]
    nodata = raster["nodata"]

    decoded = np.where(raw == nodata, np.nan, raw * scale + offset)

    values = [
        [None if np.isnan(v) else round(float(v), 3) for v in row]
        for row in decoded
    ]

    zone_stats = stats[code]

    return {
        "slug": slug,
        "bounds": raster["bounds"],
        "width": raster["width"],
        "height": raster["height"],
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

    raster_path = _resolve_raster_path(f"{region}_{epoch}.tif")

    if raster_path is None:
        raise HTTPException(
            status_code=404,
            detail=INDEX_BUILD_HINT_TEMPLATE.format(code=code, epoch=epoch),
        )

    raster = _read_index_raster(raster_path)
    band_names = raster["band_names"]

    if code not in band_names:
        raise HTTPException(
            status_code=404,
            detail=f"Index '{code}' not present in {raster_path.name}.",
        )

    band_index = band_names.index(code)
    west = raster["bounds"]["west"]
    north = raster["bounds"]["north"]
    col = int((lon - west) / raster["pixel_width"])
    row = int((north - lat) / raster["pixel_height"])

    if not (0 <= row < raster["height"] and 0 <= col < raster["width"]):
        raise HTTPException(
            status_code=404,
            detail="Point is outside this zone's raster extent.",
        )

    raw = raster["array"][row, col, band_index]
    scale = raster["scales"][band_index]
    offset = raster["offsets"][band_index]
    nodata = raster["nodata"]

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
