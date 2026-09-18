import geopandas as gpd
import pandas as pd

from shapely.geometry import Point

import src.climate_pipeline as pipeline

def test_process_nuts3_climatology_passes_variable(monkeypatch):
    municipalities = gpd.GeoDataFrame(
        {
            "municipio": ["Vila Real", "Alijó"],
            "nuts3": ["Douro", "Douro"],
        },
        geometry=[Point(-7.74, 41.30), Point(-7.47, 41.28)],
        crs="EPSG:4326",
    )

    fake_monthly = pd.DataFrame(
        {
            "municipality": ["Vila Real"] * 12 + ["Alijó"] * 12,
            "month": list(range(1, 13)) * 2,
            "mean_value": [50.0] * 24,
        }
    )

    fake_annual = pd.DataFrame(
        {
            "municipality": ["Vila Real", "Alijó"],
            "mean_value": [50.0, 55.0],
        }
    )

    def fake_get_municipalities_by_nuts3(
        municipalities_gdf, nuts3_name, target_crs
    ):
        assert nuts3_name == "Douro"
        assert target_crs == "EPSG:4326"
        return municipalities_gdf.copy()

    def fake_process_climatology_for_regions(
        chelsa_dir, regions_gdf, variable, period, version
    ):
        assert variable == "tasmax"
        assert len(regions_gdf) == 2
        return fake_monthly, fake_annual

    monkeypatch.setattr(
        pipeline,
        "get_municipalities_by_nuts3",
        fake_get_municipalities_by_nuts3,
    )

    monkeypatch.setattr(
        pipeline,
        "process_climatology_for_regions",
        fake_process_climatology_for_regions,
    )

    monthly, annual = pipeline.process_nuts3_climatology(
        municipalities_gdf=municipalities,
        nuts3_name="Douro",
        chelsa_dir="fake/path",
        variable="tasmax",
        period="1981-2010",
        version="2.1",
    )

    pd.testing.assert_frame_equal(monthly, fake_monthly)
    pd.testing.assert_frame_equal(annual, fake_annual)

def test_process_multi_nuts3_climatology_combines_regions(monkeypatch):
    """
    Verifica se o pipeline multi-NUTS III (usado por áreas de
    intervenção que combinam mais de uma NUTS III oficial, como
    Beira Interior) seleciona as regiões corretas e repassa a
    variável ao núcleo de processamento.
    """

    municipalities = gpd.GeoDataFrame(
        {
            "municipio": ["Vila Real", "Alijó", "Bragança"],
            "nuts3": [
                "Douro",
                "Douro",
                "Terras de Trás-os-Montes",
            ],
        },
        geometry=[
            Point(-7.74, 41.30),
            Point(-7.47, 41.28),
            Point(-6.76, 41.81),
        ],
        crs="EPSG:4326",
    )

    fake_monthly = pd.DataFrame(
        {
            "municipality": (
                ["Vila Real"] * 12
                + ["Alijó"] * 12
                + ["Bragança"] * 12
            ),
            "month": list(range(1, 13)) * 3,
            "mean_value": [50.0] * 36,
        }
    )

    fake_annual = pd.DataFrame(
        {
            "municipality": ["Vila Real", "Alijó", "Bragança"],
            "mean_value": [50.0, 51.0, 52.0],
        }
    )

    def fake_get_municipalities_by_nuts3_list(
        municipalities_gdf, nuts3_names, target_crs
    ):
        assert nuts3_names == ["Douro", "Terras de Trás-os-Montes"]
        assert target_crs == "EPSG:4326"
        return municipalities_gdf.copy()

    def fake_process_climatology_for_regions(
        chelsa_dir, regions_gdf, variable, period, version
    ):
        assert variable == "pr"
        assert len(regions_gdf) == 3
        return fake_monthly, fake_annual

    monkeypatch.setattr(
        pipeline,
        "get_municipalities_by_nuts3_list",
        fake_get_municipalities_by_nuts3_list,
    )

    monkeypatch.setattr(
        pipeline,
        "process_climatology_for_regions",
        fake_process_climatology_for_regions,
    )

    monthly, annual = pipeline.process_multi_nuts3_climatology(
        municipalities_gdf=municipalities,
        nuts3_names=["Douro", "Terras de Trás-os-Montes"],
        chelsa_dir="fake/path",
        variable="pr",
        period="1981-2010",
        version="2.1",
    )

    pd.testing.assert_frame_equal(monthly, fake_monthly)
    pd.testing.assert_frame_equal(annual, fake_annual)
