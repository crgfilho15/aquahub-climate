import geopandas as gpd
import pandas as pd

from shapely.geometry import Point

import src.climate_pipeline as pipeline

def test_process_municipality_temperature(monkeypatch):
    """
    Verifica se o pipeline de um município:

    1. obtém a geometria;
    2. chama o processamento climático;
    3. devolve os resultados mensal e anual.
    """

    municipalities = gpd.GeoDataFrame(
        {
            "municipio": ["Vila Real"],
        },
        geometry=[
            Point(-7.74, 41.30),
        ],
        crs="EPSG:4326",
    )

    fake_monthly = pd.DataFrame(
        {
            "municipality": ["Vila Real"] * 12,
            "month": range(1, 13),
            "mean_celsius": [10.0] * 12,
        }
    )

    fake_annual = pd.DataFrame(
        {
            "municipality": ["Vila Real"],
            "mean_celsius": [10.0],
        }
    )

    def fake_get_municipality_geometry(
        municipalities_gdf,
        municipality_name,
        target_crs,
    ):
        assert municipality_name == "Vila Real"
        assert target_crs == "EPSG:4326"

        return municipalities_gdf.copy()

    def fake_process_temperature_climatology(
        chelsa_dir,
        region_gdf,
        municipality_name,
        period,
        version,
    ):
        assert municipality_name == "Vila Real"
        assert period == "1981-2010"
        assert version == "2.1"
        assert len(region_gdf) == 1

        return fake_monthly, fake_annual

    monkeypatch.setattr(
        pipeline,
        "get_municipality_geometry",
        fake_get_municipality_geometry,
    )

    monkeypatch.setattr(
        pipeline,
        "process_temperature_climatology",
        fake_process_temperature_climatology,
    )

    monthly, annual = (
        pipeline.process_municipality_temperature(
            municipalities_gdf=municipalities,
            municipality_name="Vila Real",
            chelsa_dir="fake/path",
            period="1981-2010",
            version="2.1",
        )
    )

    pd.testing.assert_frame_equal(
        monthly,
        fake_monthly,
    )

    pd.testing.assert_frame_equal(
        annual,
        fake_annual,
    )
    
def test_process_multiple_municipalities_temperature(monkeypatch):
    """
    Verifica se o pipeline de múltiplos municípios:

    1. seleciona as geometrias em conjunto;
    2. chama o processamento regional;
    3. devolve corretamente os resultados.
    """

    municipalities = gpd.GeoDataFrame(
        {
            "municipio": [
                "Vila Real",
                "Bragança",
            ],
        },
        geometry=[
            Point(-7.74, 41.30),
            Point(-6.76, 41.81),
        ],
        crs="EPSG:4326",
    )

    fake_monthly = pd.DataFrame(
        {
            "municipality": (
                ["Vila Real"] * 12
                + ["Bragança"] * 12
            ),
            "month": (
                list(range(1, 13))
                + list(range(1, 13))
            ),
            "mean_celsius": (
                [10.0] * 12
                + [11.0] * 12
            ),
        }
    )

    fake_annual = pd.DataFrame(
        {
            "municipality": [
                "Vila Real",
                "Bragança",
            ],
            "mean_celsius": [
                10.0,
                11.0,
            ],
        }
    )

    def fake_get_municipalities_by_names(
        municipalities_gdf,
        municipality_names,
        target_crs,
    ):
        assert municipality_names == [
            "Vila Real",
            "Bragança",
        ]

        assert target_crs == "EPSG:4326"

        return municipalities_gdf.copy()

    def fake_process_temperature_climatology_for_regions(
        chelsa_dir,
        regions_gdf,
        period,
        version,
    ):
        assert len(regions_gdf) == 2
        assert period == "1981-2010"
        assert version == "2.1"

        return fake_monthly, fake_annual

    monkeypatch.setattr(
        pipeline,
        "get_municipalities_by_names",
        fake_get_municipalities_by_names,
    )

    monkeypatch.setattr(
        pipeline,
        "process_temperature_climatology_for_regions",
        fake_process_temperature_climatology_for_regions,
    )

    monthly, annual = (
        pipeline.process_multiple_municipalities_temperature(
            municipalities_gdf=municipalities,
            municipality_names=[
                "Vila Real",
                "Bragança",
            ],
            chelsa_dir="fake/path",
            period="1981-2010",
            version="2.1",
        )
    )

    pd.testing.assert_frame_equal(
        monthly,
        fake_monthly,
    )

    pd.testing.assert_frame_equal(
        annual,
        fake_annual,
    )

def test_process_nuts3_temperature(monkeypatch):
    """
    Verifica se o pipeline de uma NUTS III:

    1. seleciona automaticamente os municípios da região;
    2. chama o processamento climático regional;
    3. devolve os resultados mensal e anual.
    """

    municipalities = gpd.GeoDataFrame(
        {
            "municipio": [
                "Vila Real",
                "Alijó",
            ],
            "nuts3": [
                "Douro",
                "Douro",
            ],
        },
        geometry=[
            Point(-7.74, 41.30),
            Point(-7.47, 41.28),
        ],
        crs="EPSG:4326",
    )

    fake_monthly = pd.DataFrame(
        {
            "municipality": (
                ["Vila Real"] * 12
                + ["Alijó"] * 12
            ),
            "month": (
                list(range(1, 13))
                + list(range(1, 13))
            ),
            "mean_celsius": (
                [10.0] * 12
                + [11.0] * 12
            ),
        }
    )

    fake_annual = pd.DataFrame(
        {
            "municipality": [
                "Vila Real",
                "Alijó",
            ],
            "mean_celsius": [
                10.0,
                11.0,
            ],
        }
    )

    def fake_get_municipalities_by_nuts3(
        municipalities_gdf,
        nuts3_name,
        target_crs,
    ):
        assert nuts3_name == "Douro"
        assert target_crs == "EPSG:4326"

        return municipalities_gdf.copy()

    def fake_process_temperature_climatology_for_regions(
        chelsa_dir,
        regions_gdf,
        period,
        version,
    ):
        assert len(regions_gdf) == 2
        assert period == "1981-2010"
        assert version == "2.1"

        return fake_monthly, fake_annual

    monkeypatch.setattr(
        pipeline,
        "get_municipalities_by_nuts3",
        fake_get_municipalities_by_nuts3,
    )

    monkeypatch.setattr(
        pipeline,
        "process_temperature_climatology_for_regions",
        fake_process_temperature_climatology_for_regions,
    )

    monthly, annual = (
        pipeline.process_nuts3_temperature(
            municipalities_gdf=municipalities,
            nuts3_name="Douro",
            chelsa_dir="fake/path",
            period="1981-2010",
            version="2.1",
        )
    )

    pd.testing.assert_frame_equal(
        monthly,
        fake_monthly,
    )

    pd.testing.assert_frame_equal(
        annual,
        fake_annual,
    )