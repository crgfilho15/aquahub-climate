import geopandas as gpd
import pytest

from shapely.geometry import Point

from src.gisco_boundary_processing import (
    get_region_bounds,
    get_regions_by_nuts_id,
    list_available_nuts_regions,
)

def create_test_gisco_regions():
    """
    Cria uma pequena camada GISCO/Eurostat artificial para testes
    unitários, com o esquema de colunas real (NUTS_ID, NUTS_NAME,
    CNTR_CODE, LEVL_CODE) usado pelos ficheiros de fronteiras NUTS
    do Eurostat/GISCO.
    """

    return gpd.GeoDataFrame(
        {
            "NUTS_ID": ["ES41", "ES43", "ES30", "PT11"],
            "NUTS_NAME": [
                "Castilla y León",
                "Extremadura",
                "Comunidad de Madrid",
                "Norte",
            ],
            "CNTR_CODE": ["ES", "ES", "ES", "PT"],
            "LEVL_CODE": [2, 2, 2, 2],
        },
        geometry=[
            Point(-4.5, 41.6),
            Point(-6.1, 39.2),
            Point(-3.7, 40.4),
            Point(-8.6, 41.5),
        ],
        crs="EPSG:4326",
    )

def test_get_regions_by_nuts_id():
    regions = create_test_gisco_regions()

    result = get_regions_by_nuts_id(
        gisco_gdf=regions,
        nuts_ids=["ES41", "ES43"],
    )

    assert len(result) == 2

    assert set(result["NUTS_ID"]) == {"ES41", "ES43"}

    assert result.crs.to_epsg() == 4326

def test_get_regions_by_nuts_id_is_case_insensitive():
    regions = create_test_gisco_regions()

    result = get_regions_by_nuts_id(
        gisco_gdf=regions,
        nuts_ids=["es41"],
    )

    assert set(result["NUTS_ID"]) == {"ES41"}

def test_get_regions_by_nuts_id_rejects_empty_list():
    regions = create_test_gisco_regions()

    with pytest.raises(ValueError, match="não pode estar vazia"):
        get_regions_by_nuts_id(
            gisco_gdf=regions,
            nuts_ids=[],
        )

def test_get_regions_by_nuts_id_rejects_missing_id():
    regions = create_test_gisco_regions()

    with pytest.raises(ValueError, match="NUTS_ID não encontrados"):
        get_regions_by_nuts_id(
            gisco_gdf=regions,
            nuts_ids=["ES41", "ES99"],
        )

def test_get_regions_by_nuts_id_deduplicates():
    regions = create_test_gisco_regions()

    result = get_regions_by_nuts_id(
        gisco_gdf=regions,
        nuts_ids=["ES41", "ES41"],
    )

    assert len(result) == 1
    assert result["NUTS_ID"].is_unique

def test_get_region_bounds():
    regions = create_test_gisco_regions()

    selected = get_regions_by_nuts_id(
        gisco_gdf=regions,
        nuts_ids=["ES41", "ES43"],
    )

    xmin, ymin, xmax, ymax = selected.total_bounds

    result = get_region_bounds(
        gisco_gdf=regions,
        nuts_ids=["ES41", "ES43"],
    )

    assert result == {
        "xmin": float(xmin),
        "xmax": float(xmax),
        "ymin": float(ymin),
        "ymax": float(ymax),
    }

def test_list_available_nuts_regions_filters_by_country_and_level():
    regions = create_test_gisco_regions()

    result = list_available_nuts_regions(
        gisco_gdf=regions,
        country_code="ES",
        levl_code=2,
    )

    assert result == [
        ("ES30", "Comunidad de Madrid"),
        ("ES41", "Castilla y León"),
        ("ES43", "Extremadura"),
    ]

def test_list_available_nuts_regions_without_filters_returns_all():
    regions = create_test_gisco_regions()

    result = list_available_nuts_regions(gisco_gdf=regions)

    assert len(result) == 4
    assert ("PT11", "Norte") in result
