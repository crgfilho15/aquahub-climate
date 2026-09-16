import json

from fastapi.testclient import TestClient

from api.main import app


def write_fixture(tmp_path):
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
        "region_type": "NUTS3",
        "region_name": "Douro",
        "variable": "tas",
        "period": "1981-2010",
        "dataset": "CHELSA climatologies v2.1",
        "methodology_status": "provisional",
        "future_scenarios_included": False,
        "generated_at": "2026-09-16T00:00:00+00:00",
    }

    (tmp_path / "douro_pilot.geojson").write_text(
        json.dumps(geojson), encoding="utf-8"
    )
    (tmp_path / "douro_pilot_meta.json").write_text(
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
    assert "build_pilot_douro" in response.json()["detail"]


def test_get_pilot_unknown_region_returns_404(tmp_path, monkeypatch):
    monkeypatch.setenv("AQUAHUB_PILOT_DATA_DIR", str(tmp_path))

    client = TestClient(app)
    response = client.get("/api/pilot/beira-interior")

    assert response.status_code == 404
