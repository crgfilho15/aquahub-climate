import json

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
