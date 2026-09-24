"""
Export utilities for the professor's ensemble1 bioclimatic indices on
the pilot platform.

For each of the 5 AquaHub zones and each of ensemble1's 3 epochs
(historical, ssp126_2041-2070, ssp585_2041-2070), this module produces
two artefacts per zone/epoch, both committed to Git (see
docs/04_roadmap_future_and_bioclimatic_indices.md Section 2.1):

- A small `uint16`-encoded, per-variable-scaled, multi-band GeoTIFF
  covering only that zone's own polygon (not the 5-zone union) - used
  by the Climate Atlas for the per-zone heatmap overlay and the
  point-query endpoint. `uint16` + a per-variable scale/offset keeps
  this small (real measured total across 5 zones x 3 epochs: ~141MB,
  vs. 224MB uncompressed as float32) with negligible precision loss -
  the same scale/offset technique CHELSA's own rasters already use
  elsewhere in this project, just computed per-variable here since the
  129 indices have very different ranges.
- A tiny JSON of coverage-weighted mean/min/max per index, computed via
  `exact_extract` (the same tool and call pattern
  src/climate_processing.py's calculate_monthly_value_for_regions
  already uses) - this is the authoritative statistic, distinct from
  the raster above, which is for visualization/point-query only.
"""

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import rioxarray  # noqa: F401 - registers the .rio accessor
import xarray as xr
from exactextract import exact_extract

NODATA_UINT16 = 65535
USABLE_RANGE = 65000


class IndexPilotExportError(ValueError):
    """Raised when index pilot export inputs are inconsistent."""


def load_zone_geometries(
    zones_overview_path: str | Path,
) -> gpd.GeoDataFrame:
    """Load the 5 zones' own individual polygons (not a union) from
    data/processed/pilot/zones_overview.geojson, keyed by 'slug'."""

    path = Path(zones_overview_path)

    if not path.exists():
        raise IndexPilotExportError(
            f"Zones overview not found: {path}. Run "
            "'python -m scripts.build_zone_overview' first."
        )

    gdf = gpd.read_file(path)

    if "slug" not in gdf.columns:
        raise IndexPilotExportError(
            f"{path} is missing the 'slug' column."
        )

    return gdf


def compute_variable_scale_offsets(
    dataset: xr.Dataset,
) -> dict[str, tuple[float, float]]:
    """
    Compute a (scale, offset) pair per data variable, from that
    variable's real min/max across the *whole* grid (all 5 zones
    combined) - so the same physical value quantizes identically no
    matter which zone's file it ends up in.

    uint16 encoding: encoded = round((value - offset) / scale),
    clipped to [0, USABLE_RANGE]; decode: value = encoded * scale +
    offset. NODATA_UINT16 (65535) is reserved for NaN/no-data pixels.
    """

    scales_offsets = {}

    for name, da in dataset.data_vars.items():
        values = da.values
        finite = values[np.isfinite(values)]

        if finite.size == 0:
            raise IndexPilotExportError(
                f"Variable '{name}' has no finite values in the grid."
            )

        vmin = float(finite.min())
        vmax = float(finite.max())
        span = vmax - vmin if vmax > vmin else 1.0

        scales_offsets[name] = (span / USABLE_RANGE, vmin)

    return scales_offsets


def crop_zone_indices_raster(
    dataset: xr.Dataset,
    zone_geometry,
    scale_offsets: dict[str, tuple[float, float]],
    output_path: str | Path,
) -> list[str]:
    """
    Crop every data variable in `dataset` to `zone_geometry`
    (EPSG:4326) and write one uint16-encoded, per-band-scaled,
    compressed multi-band GeoTIFF.

    Returns
    -------
    list[str]
        The band order (index codes), matching each written band's
        1-based position and its GDAL band description.
    """

    stacked = dataset.to_array(dim="variable")

    if "time" in stacked.dims:
        stacked = stacked.isel(time=0)

    stacked = stacked.rio.set_spatial_dims(x_dim="lon", y_dim="lat")
    stacked = stacked.rio.write_crs("EPSG:4326")

    clipped = stacked.rio.clip(
        [zone_geometry], crs="EPSG:4326", drop=True
    )

    band_names = list(stacked["variable"].values)
    missing = set(band_names) - scale_offsets.keys()

    if missing:
        raise IndexPilotExportError(
            f"Missing scale/offset for variables: {sorted(missing)}"
        )

    n_bands, height, width = clipped.shape

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    profile = {
        "driver": "GTiff",
        "dtype": "uint16",
        "count": n_bands,
        "height": height,
        "width": width,
        "crs": clipped.rio.crs,
        "transform": clipped.rio.transform(),
        "nodata": NODATA_UINT16,
        "compress": "deflate",
        "predictor": 2,
        "zlevel": 9,
    }

    with rasterio.open(output_path, "w", **profile) as dst:
        for band_index, name in enumerate(band_names, start=1):
            scale, offset = scale_offsets[name]
            band_values = clipped.sel(variable=name).values

            encoded = np.where(
                np.isnan(band_values),
                NODATA_UINT16,
                np.clip(
                    np.round((band_values - offset) / scale),
                    0,
                    USABLE_RANGE,
                ),
            ).astype(np.uint16)

            dst.write(encoded, band_index)
            dst.set_band_description(band_index, name)

        dst.scales = tuple(scale_offsets[name][0] for name in band_names)
        dst.offsets = tuple(scale_offsets[name][1] for name in band_names)

    return band_names


def compute_zone_index_stats(
    nc_path: str | Path,
    zones_gdf: gpd.GeoDataFrame,
    variable_codes: list[str],
) -> pd.DataFrame:
    """
    Coverage-weighted mean/min/max per zone x index code, via
    exact_extract - the same tool/call pattern
    src/climate_processing.py's calculate_monthly_value_for_regions
    already uses for the rest of the pipeline's zonal statistics.

    Returns
    -------
    pandas.DataFrame
        One row per (slug, code), columns: slug, code, mean, min, max.
    """

    if "slug" not in zones_gdf.columns:
        raise IndexPilotExportError("zones_gdf must have a 'slug' column.")

    rows = []

    for code in variable_codes:
        raster_path = f'NETCDF:"{nc_path}":{code}'

        result = exact_extract(
            raster_path,
            zones_gdf,
            [
                "mean=mean(coverage_weight=area_spherical_m2)",
                "min=min",
                "max=max",
            ],
            include_cols=["slug"],
            output="pandas",
        )
        result["code"] = code
        rows.append(result)

    return pd.concat(rows, ignore_index=True)[
        ["slug", "code", "mean", "min", "max"]
    ]


def save_zone_index_stats(
    stats_df: pd.DataFrame,
    output_dir: str | Path,
    slug: str,
    epoch: str,
) -> Path:
    """Persist one zone's index stats (mean/min/max per code, for
    this epoch) as data/processed/pilot/indices/{slug}_{epoch}_stats.json."""

    zone_stats = (
        stats_df[stats_df["slug"] == slug]
        .set_index("code")[["mean", "min", "max"]]
        .to_dict(orient="index")
    )

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{slug}_{epoch}_stats.json"
    output_path.write_text(
        json.dumps(zone_stats, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return output_path
