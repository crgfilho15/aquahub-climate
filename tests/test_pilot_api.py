import json

import pytest
from fastapi.testclient import TestClient

from api.main import app


def write_fixture(tmp_path, slug="douro", label="Douro"):
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "municipio": "Vila Real",
                    "annual_mean_celsius": 12.03,
                    "monthly_mean_celsius": [5.0] * 12,
                    "variable": "tas",
                    "period": "1981-2010",
                    "source": "CHELSA climatologies v2.1",
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[-7.9, 41.2], [-7.6, 41.2], [-7.6, 41.4], [-7.9, 41.4], [-7.9, 41.2]]
                    ],
                },
            }
        ],
    }

    metadata = {
        "slug": slug,
        "region_type": "NUTS3",
        "region_name": label,
        "variable": "tas",
        "period": "1981-2010",
        "dataset": "CHELSA climatologies v2.1",
        "methodology_status": "provisional",
        "future_scenarios_included": False,
        "generated_at": "2026-09-16T00:00:00+00:00",
    }

    (tmp_path / f"{slug}_pilot.geojson").write_text(
        json.dumps(geojson), encoding="utf-8"
    )
    (tmp_path / f"{slug}_pilot_meta.json").write_text(
        json.dumps(metadata), encoding="utf-8"
    )


def test_get_pilot_geojson_returns_data(tmp_path, monkeypatch):
    write_fixture(tmp_path)
    monkeypatch.setenv("AQUAHUB_PILOT_DATA_DIR", str(tmp_path))

    client = TestClient(app)
    response = client.get("/api/pilot/douro")

    assert response.status_code == 200
    body = response.json()
    assert body["features"][0]["properties"]["municipio"] == "Vila Real"


def test_get_pilot_metadata_returns_data(tmp_path, monkeypatch):
    write_fixture(tmp_path)
    monkeypatch.setenv("AQUAHUB_PILOT_DATA_DIR", str(tmp_path))

    client = TestClient(app)
    response = client.get("/api/pilot/douro/meta")

    assert response.status_code == 200
    assert response.json()["region_name"] == "Douro"


def test_get_pilot_geojson_missing_data_returns_404_with_hint(tmp_path, monkeypatch):
    monkeypatch.setenv("AQUAHUB_PILOT_DATA_DIR", str(tmp_path))

    client = TestClient(app)
    response = client.get("/api/pilot/douro")

    assert response.status_code == 404
    detail = response.json()["detail"]
    assert "build_pilot_region" in detail
    assert "douro" in detail


def test_get_pilot_unconfigured_region_returns_404(tmp_path, monkeypatch):
    """A slug that isn't in config/climate.toml's
    [[pilot_platform.regions]] must never reach the filesystem lookup —
    it is rejected by the allow-list before any file path is built."""

    monkeypatch.setenv("AQUAHUB_PILOT_DATA_DIR", str(tmp_path))

    client = TestClient(app)
    response = client.get("/api/pilot/not-a-real-region")

    assert response.status_code == 404
    assert "Unknown pilot region" in response.json()["detail"]


def test_get_pilot_configured_but_unbuilt_region_returns_build_hint(
    tmp_path, monkeypatch
):
    """'beira-interior' is configured in climate.toml but has no
    nuts3_names yet, so it is never built; the API should say so via
    the normal missing-data hint, not treat it as unknown."""

    monkeypatch.setenv("AQUAHUB_PILOT_DATA_DIR", str(tmp_path))

    client = TestClient(app)
    response = client.get("/api/pilot/beira-interior")

    assert response.status_code == 404
    detail = response.json()["detail"]
    assert "build_pilot_region" in detail
    assert "beira-interior" in detail


def test_list_available_pilot_regions_empty_when_nothing_built(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("AQUAHUB_PILOT_DATA_DIR", str(tmp_path))

    client = TestClient(app)
    response = client.get("/api/pilot")

    assert response.status_code == 200
    assert response.json() == []


def test_list_available_pilot_regions_includes_built_region_only(
    tmp_path, monkeypatch
):
    write_fixture(tmp_path, slug="douro", label="Douro")
    monkeypatch.setenv("AQUAHUB_PILOT_DATA_DIR", str(tmp_path))

    client = TestClient(app)
    response = client.get("/api/pilot")

    assert response.status_code == 200
    assert response.json() == [{"slug": "douro", "label": "Douro"}]


def write_zones_overview_fixture(tmp_path):
    feature_collection = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "slug": "douro",
                    "label": "Douro",
                    "built": True,
                    "annual_mean_celsius": 13.0,
                    "municipality_values": [
                        {"municipio": "Vila Real", "annual_mean_celsius": 12.0},
                        {"municipio": "Sabrosa", "annual_mean_celsius": 14.0},
                    ],
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[-7.9, 41.2], [-7.6, 41.2], [-7.6, 41.4], [-7.9, 41.4], [-7.9, 41.2]]
                    ],
                },
            },
            {
                "type": "Feature",
                "properties": {
                    "slug": "castilla-y-leon",
                    "label": "Castilla y León",
                    "built": False,
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[-6.5, 40.0], [-4.0, 40.0], [-4.0, 42.5], [-6.5, 42.5], [-6.5, 40.0]]
                    ],
                },
            },
        ],
    }

    (tmp_path / "zones_overview.geojson").write_text(
        json.dumps(feature_collection), encoding="utf-8"
    )


def test_get_zone_overview_returns_data(tmp_path, monkeypatch):
    write_zones_overview_fixture(tmp_path)
    monkeypatch.setenv("AQUAHUB_PILOT_DATA_DIR", str(tmp_path))

    client = TestClient(app)
    response = client.get("/api/pilot/zones")

    assert response.status_code == 200
    body = response.json()
    slugs = {f["properties"]["slug"] for f in body["features"]}
    assert slugs == {"douro", "castilla-y-leon"}

    built_by_slug = {
        f["properties"]["slug"]: f["properties"]["built"]
        for f in body["features"]
    }
    assert built_by_slug == {"douro": True, "castilla-y-leon": False}


def test_get_zone_overview_missing_returns_404_with_hint(tmp_path, monkeypatch):
    monkeypatch.setenv("AQUAHUB_PILOT_DATA_DIR", str(tmp_path))

    client = TestClient(app)
    response = client.get("/api/pilot/zones")

    assert response.status_code == 404
    assert "build_zone_overview" in response.json()["detail"]


def write_future_fixture(
    tmp_path,
    slug="douro",
    variable="tas",
    scenario="ssp585",
    period="2041-2070",
):
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "municipio": "Vila Real",
                    "variable": variable,
                    "scenario": scenario,
                    "period": period,
                    "annual_ensemble_mean": 13.5,
                    "annual_anomaly_absolute": 2.1,
                    "monthly_ensemble_mean": [10.0] * 12,
                    "monthly_anomaly_absolute": [2.0] * 12,
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[-7.9, 41.2], [-7.6, 41.2], [-7.6, 41.4], [-7.9, 41.4], [-7.9, 41.2]]
                    ],
                },
            }
        ],
    }

    metadata = {
        "slug": slug,
        "region_name": "Douro",
        "variable": variable,
        "scenario": scenario,
        "period": period,
        "dataset": "CHELSA-climatologies-v2.1-CMIP6",
        "gcms": ["GFDL-ESM4"],
        "ensemble_method": "equal_weight_mean",
        "methodology_status": "provisional",
        "generated_at": "2026-09-18T00:00:00+00:00",
    }

    stem = f"{slug}_{variable}_{scenario}_{period}_future"

    (tmp_path / f"{stem}.geojson").write_text(
        json.dumps(geojson), encoding="utf-8"
    )
    (tmp_path / f"{stem}_meta.json").write_text(
        json.dumps(metadata), encoding="utf-8"
    )


def test_get_future_pilot_geojson_returns_data(tmp_path, monkeypatch):
    write_future_fixture(tmp_path)
    monkeypatch.setenv("AQUAHUB_FUTURE_PILOT_DATA_DIR", str(tmp_path))

    client = TestClient(app)
    response = client.get(
        "/api/pilot/douro/future/tas/ssp585/2041-2070"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["features"][0]["properties"]["municipio"] == "Vila Real"


def test_get_future_pilot_metadata_returns_data(tmp_path, monkeypatch):
    write_future_fixture(tmp_path)
    monkeypatch.setenv("AQUAHUB_FUTURE_PILOT_DATA_DIR", str(tmp_path))

    client = TestClient(app)
    response = client.get(
        "/api/pilot/douro/future/tas/ssp585/2041-2070/meta"
    )

    assert response.status_code == 200
    assert response.json()["gcms"] == ["GFDL-ESM4"]


def test_get_future_pilot_missing_slice_returns_404_with_hint(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("AQUAHUB_FUTURE_PILOT_DATA_DIR", str(tmp_path))

    client = TestClient(app)
    response = client.get(
        "/api/pilot/douro/future/tas/ssp585/2041-2070"
    )

    assert response.status_code == 404
    detail = response.json()["detail"]
    assert "build_future_pilot_data" in detail
    assert "ssp585" in detail
    assert "2041-2070" in detail


def test_get_future_pilot_unconfigured_scenario_returns_404_without_filesystem(
    tmp_path, monkeypatch
):
    """A scenario not in config/climate.toml's [future].scenarios must
    be rejected by the allow-list before any file path is built - same
    principle as the region slug allow-list."""

    write_future_fixture(tmp_path)
    monkeypatch.setenv("AQUAHUB_FUTURE_PILOT_DATA_DIR", str(tmp_path))

    client = TestClient(app)
    response = client.get(
        "/api/pilot/douro/future/tas/ssp370/2041-2070"
    )

    assert response.status_code == 404
    assert "Unknown scenario" in response.json()["detail"]


def test_get_future_pilot_unconfigured_region_returns_404(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("AQUAHUB_FUTURE_PILOT_DATA_DIR", str(tmp_path))

    client = TestClient(app)
    response = client.get(
        "/api/pilot/not-a-real-region/future/tas/ssp585/2041-2070"
    )

    assert response.status_code == 404
    assert "Unknown pilot region" in response.json()["detail"]


def test_list_available_future_slices_empty_when_nothing_built(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("AQUAHUB_FUTURE_PILOT_DATA_DIR", str(tmp_path))

    client = TestClient(app)
    response = client.get("/api/pilot/douro/future")

    assert response.status_code == 200
    assert response.json() == []


def test_list_available_future_slices_includes_built_slice_only(
    tmp_path, monkeypatch
):
    write_future_fixture(
        tmp_path, variable="tas", scenario="ssp585", period="2041-2070"
    )
    monkeypatch.setenv("AQUAHUB_FUTURE_PILOT_DATA_DIR", str(tmp_path))

    client = TestClient(app)
    response = client.get("/api/pilot/douro/future")

    assert response.status_code == 200
    assert response.json() == [
        {"variable": "tas", "scenario": "ssp585", "period": "2041-2070"}
    ]


def write_indices_catalog_fixture(tmp_path, codes=("GDD10",)):
    path = tmp_path / "indices_catalog.json"
    catalog = {
        "language": "pt",
        "source": "test",
        "generated_at": "2026-09-23T00:00:00+00:00",
        "indices": {
            code: {
                "category": "Acumulação de graus-dia",
                "name": f"Nome de {code}",
                "formula": f"Formula de {code}",
                "reference": "—",
                "crops": ["grapevine"],
            }
            for code in codes
        },
    }
    path.write_text(json.dumps(catalog), encoding="utf-8")
    return path


def write_index_pilot_fixture(
    tmp_path, slug="douro", epoch="historical", code="GDD10"
):
    """A minimal 2x2 uint16 GeoTIFF (one band) + its stats JSON,
    matching scripts/build_index_pilot_data.py's real output shape."""

    import numpy as np
    import rasterio
    from rasterio.transform import from_origin

    raster_path = tmp_path / f"{slug}_{epoch}.tif"
    stats_path = tmp_path / f"{slug}_{epoch}_stats.json"

    scale, offset = 0.1, 10.0
    real_values = np.array([[20.0, 30.0], [40.0, np.nan]])
    encoded = np.where(
        np.isnan(real_values),
        65535,
        np.round((real_values - offset) / scale),
    ).astype(np.uint16)

    transform = from_origin(west=-8.0, north=42.0, xsize=0.01, ysize=0.01)

    with rasterio.open(
        raster_path,
        "w",
        driver="GTiff",
        height=2,
        width=2,
        count=1,
        dtype="uint16",
        crs="EPSG:4326",
        transform=transform,
        nodata=65535,
    ) as dst:
        dst.write(encoded, 1)
        dst.set_band_description(1, code)
        dst.scales = (scale,)
        dst.offsets = (offset,)

    stats_path.write_text(
        json.dumps({code: {"mean": 30.0, "min": 20.0, "max": 40.0}}),
        encoding="utf-8",
    )

    return raster_path, stats_path


def test_get_indices_catalog_returns_data(tmp_path, monkeypatch):
    write_indices_catalog_fixture(tmp_path)
    monkeypatch.setenv(
        "AQUAHUB_INDICES_CATALOG_PATH", str(tmp_path / "indices_catalog.json")
    )

    client = TestClient(app)
    response = client.get("/api/indices")

    assert response.status_code == 200
    assert response.json()["indices"]["GDD10"]["name"] == "Nome de GDD10"


def test_get_indices_catalog_missing_returns_404_with_hint(
    tmp_path, monkeypatch
):
    monkeypatch.setenv(
        "AQUAHUB_INDICES_CATALOG_PATH", str(tmp_path / "missing.json")
    )

    client = TestClient(app)
    response = client.get("/api/indices")

    assert response.status_code == 404
    assert "build_indices_catalog" in response.json()["detail"]


def test_get_zones_index_historical_returns_one_zone(tmp_path, monkeypatch):
    write_indices_catalog_fixture(tmp_path)
    write_index_pilot_fixture(tmp_path, slug="douro", epoch="historical")
    monkeypatch.setenv(
        "AQUAHUB_INDICES_CATALOG_PATH", str(tmp_path / "indices_catalog.json")
    )
    monkeypatch.setenv("AQUAHUB_INDEX_PILOT_DATA_DIR", str(tmp_path))

    client = TestClient(app)
    response = client.get("/api/pilot/zones/index/GDD10")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == "GDD10"
    assert body["epoch"] == "historical"
    assert body["global_min"] == 20.0
    assert body["global_max"] == 40.0

    douro = next(z for z in body["zones"] if z["slug"] == "douro")
    assert douro["mean"] == 30.0
    assert douro["width"] == 2
    assert douro["height"] == 2
    assert douro["values"][0][0] == pytest.approx(20.0, abs=0.05)
    assert douro["values"][1][1] is None  # NaN pixel


def test_get_zones_index_unknown_code_returns_404(tmp_path, monkeypatch):
    write_indices_catalog_fixture(tmp_path)
    monkeypatch.setenv(
        "AQUAHUB_INDICES_CATALOG_PATH", str(tmp_path / "indices_catalog.json")
    )
    monkeypatch.setenv("AQUAHUB_INDEX_PILOT_DATA_DIR", str(tmp_path))

    client = TestClient(app)
    response = client.get("/api/pilot/zones/index/NOT_A_REAL_CODE")

    assert response.status_code == 404
    assert "Unknown index code" in response.json()["detail"]


def test_get_zones_index_not_built_yet_returns_404_with_hint(
    tmp_path, monkeypatch
):
    write_indices_catalog_fixture(tmp_path)
    monkeypatch.setenv(
        "AQUAHUB_INDICES_CATALOG_PATH", str(tmp_path / "indices_catalog.json")
    )
    monkeypatch.setenv("AQUAHUB_INDEX_PILOT_DATA_DIR", str(tmp_path))

    client = TestClient(app)
    response = client.get("/api/pilot/zones/index/GDD10")

    assert response.status_code == 404
    assert "build_index_pilot_data" in response.json()["detail"]


def test_get_zones_index_future_unconfigured_scenario_returns_404(
    tmp_path, monkeypatch
):
    write_indices_catalog_fixture(tmp_path)
    monkeypatch.setenv(
        "AQUAHUB_INDICES_CATALOG_PATH", str(tmp_path / "indices_catalog.json")
    )
    monkeypatch.setenv("AQUAHUB_INDEX_PILOT_DATA_DIR", str(tmp_path))

    client = TestClient(app)
    response = client.get(
        "/api/pilot/zones/index/GDD10/ssp370/2041-2070"
    )

    assert response.status_code == 404
    assert "Unknown scenario" in response.json()["detail"]


def test_get_index_point_returns_exact_value(tmp_path, monkeypatch):
    write_indices_catalog_fixture(tmp_path)
    write_index_pilot_fixture(tmp_path, slug="douro", epoch="historical")
    monkeypatch.setenv(
        "AQUAHUB_INDICES_CATALOG_PATH", str(tmp_path / "indices_catalog.json")
    )
    monkeypatch.setenv("AQUAHUB_INDEX_PILOT_DATA_DIR", str(tmp_path))

    client = TestClient(app)
    response = client.get(
        "/api/pilot/douro/index/GDD10/point",
        params={"lat": 41.995, "lon": -7.995},
    )

    assert response.status_code == 200
    assert response.json()["value"] == pytest.approx(20.0, abs=0.05)


def test_get_index_point_outside_extent_returns_404(tmp_path, monkeypatch):
    write_indices_catalog_fixture(tmp_path)
    write_index_pilot_fixture(tmp_path, slug="douro", epoch="historical")
    monkeypatch.setenv(
        "AQUAHUB_INDICES_CATALOG_PATH", str(tmp_path / "indices_catalog.json")
    )
    monkeypatch.setenv("AQUAHUB_INDEX_PILOT_DATA_DIR", str(tmp_path))

    client = TestClient(app)
    response = client.get(
        "/api/pilot/douro/index/GDD10/point",
        params={"lat": 0.0, "lon": 0.0},
    )

    assert response.status_code == 404


def test_get_index_point_on_nodata_pixel_returns_404(tmp_path, monkeypatch):
    write_indices_catalog_fixture(tmp_path)
    write_index_pilot_fixture(tmp_path, slug="douro", epoch="historical")
    monkeypatch.setenv(
        "AQUAHUB_INDICES_CATALOG_PATH", str(tmp_path / "indices_catalog.json")
    )
    monkeypatch.setenv("AQUAHUB_INDEX_PILOT_DATA_DIR", str(tmp_path))

    client = TestClient(app)
    # bottom-right pixel of the 2x2 fixture is NaN/nodata
    response = client.get(
        "/api/pilot/douro/index/GDD10/point",
        params={"lat": 41.985, "lon": -7.985},
    )

    assert response.status_code == 404
    assert "No data at this point" in response.json()["detail"]
