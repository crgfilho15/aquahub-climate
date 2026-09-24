import json

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import rasterio
import xarray as xr
from shapely.geometry import box

from src.index_pilot_export import (
    IndexPilotExportError,
    compute_variable_scale_offsets,
    compute_zone_index_stats,
    crop_zone_indices_raster,
    load_zone_geometries,
    save_zone_index_stats,
)


def make_dataset():
    """A tiny 2x2 synthetic grid, 2 variables, values chosen so the
    expected min/max/scale are easy to check by hand."""

    lat = [0.75, 0.25]
    lon = [0.25, 0.75]
    var_a = np.array([[[10.0, 20.0], [30.0, 40.0]]])
    var_b = np.array([[[1.0, 2.0], [3.0, 4.0]]])

    return xr.Dataset(
        {
            "VAR_A": (("time", "lat", "lon"), var_a),
            "VAR_B": (("time", "lat", "lon"), var_b),
        },
        coords={"time": [2000], "lat": lat, "lon": lon},
    )


def test_load_zone_geometries_reads_slug_column(tmp_path):
    path = tmp_path / "zones_overview.geojson"
    feature_collection = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"slug": "douro", "label": "Douro"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]
                    ],
                },
            }
        ],
    }
    path.write_text(json.dumps(feature_collection), encoding="utf-8")

    gdf = load_zone_geometries(path)

    assert list(gdf["slug"]) == ["douro"]


def test_load_zone_geometries_missing_file_raises(tmp_path):
    with pytest.raises(IndexPilotExportError):
        load_zone_geometries(tmp_path / "does_not_exist.geojson")


def test_compute_variable_scale_offsets_uses_full_grid_range():
    ds = make_dataset()

    scale_offsets = compute_variable_scale_offsets(ds)

    assert set(scale_offsets.keys()) == {"VAR_A", "VAR_B"}

    scale_a, offset_a = scale_offsets["VAR_A"]
    assert offset_a == 10.0
    assert scale_a == pytest.approx((40.0 - 10.0) / 65000)

    scale_b, offset_b = scale_offsets["VAR_B"]
    assert offset_b == 1.0
    assert scale_b == pytest.approx((4.0 - 1.0) / 65000)


def test_crop_zone_indices_raster_writes_uint16_geotiff_with_bands(tmp_path):
    ds = make_dataset()
    scale_offsets = compute_variable_scale_offsets(ds)
    zone_geometry = box(0, 0, 1, 1)
    output_path = tmp_path / "zone.tif"

    band_names = crop_zone_indices_raster(
        dataset=ds,
        zone_geometry=zone_geometry,
        scale_offsets=scale_offsets,
        output_path=output_path,
    )

    assert band_names == ["VAR_A", "VAR_B"]
    assert output_path.exists()

    with rasterio.open(output_path) as src:
        assert src.count == 2
        assert list(src.descriptions) == ["VAR_A", "VAR_B"]
        assert src.dtypes[0] == "uint16"

        raw = src.read(1)
        scale, offset = src.scales[0], src.offsets[0]
        decoded = raw.astype(float) * scale + offset

        assert np.nanmax(decoded) == pytest.approx(40.0, abs=0.01)
        assert np.nanmin(decoded) == pytest.approx(10.0, abs=0.01)


def test_crop_zone_indices_raster_missing_scale_offset_raises(tmp_path):
    ds = make_dataset()
    zone_geometry = box(0, 0, 1, 1)

    with pytest.raises(IndexPilotExportError):
        crop_zone_indices_raster(
            dataset=ds,
            zone_geometry=zone_geometry,
            scale_offsets={"VAR_A": (1.0, 0.0)},  # VAR_B missing
            output_path=tmp_path / "zone.tif",
        )


def test_compute_zone_index_stats_returns_mean_min_max(tmp_path):
    ds = make_dataset()
    nc_path = tmp_path / "synthetic.nc"
    ds.to_netcdf(nc_path)

    zones_gdf = gpd.GeoDataFrame(
        {"slug": ["test-zone"]},
        geometry=[box(0, 0, 1, 1)],
        crs="EPSG:4326",
    )

    stats_df = compute_zone_index_stats(
        nc_path, zones_gdf, ["VAR_A", "VAR_B"]
    )

    assert set(stats_df["code"]) == {"VAR_A", "VAR_B"}

    var_a_row = stats_df[stats_df["code"] == "VAR_A"].iloc[0]
    assert var_a_row["min"] == pytest.approx(10.0)
    assert var_a_row["max"] == pytest.approx(40.0)
    assert 10.0 <= var_a_row["mean"] <= 40.0


def test_save_zone_index_stats_writes_json_for_one_zone(tmp_path):
    stats_df = pd.DataFrame(
        [
            {"slug": "douro", "code": "VAR_A", "mean": 25.0, "min": 10.0, "max": 40.0},
            {"slug": "douro", "code": "VAR_B", "mean": 2.5, "min": 1.0, "max": 4.0},
            {"slug": "extremadura", "code": "VAR_A", "mean": 99.0, "min": 90.0, "max": 100.0},
        ]
    )

    output_path = save_zone_index_stats(
        stats_df, tmp_path, slug="douro", epoch="historical"
    )

    assert output_path.name == "douro_historical_stats.json"
    saved = json.loads(output_path.read_text(encoding="utf-8"))

    assert set(saved.keys()) == {"VAR_A", "VAR_B"}
    assert saved["VAR_A"] == {"mean": 25.0, "min": 10.0, "max": 40.0}
