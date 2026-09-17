import geopandas as gpd
import pytest

from shapely.geometry import Point

from src.boundary_processing import (
    get_municipality_geometry,
    get_municipalities_by_names,
    get_municipalities_by_nuts3,
    get_municipalities_by_nuts3_list,
    get_nuts3_bounds,
)

def create_test_municipalities():
    """
    Cria uma pequena camada administrativa artificial
    para testes unitários.
    """

    return gpd.GeoDataFrame(
        {
            "municipio": [
                "Vila Real",
                "Alijó",
                "Bragança",
            ],
            "nuts3": [
                "Douro",
                "Douro",
                "Terras de Trás-os-Montes",
            ],
        },
        geometry=[
            Point(100000, 200000),
            Point(110000, 210000),
            Point(150000, 250000),
        ],
        crs="EPSG:3763",
    )

def test_get_municipality_geometry():
    """
    Verifica se um município é selecionado corretamente
    e reprojetado para EPSG:4326.
    """

    municipalities = create_test_municipalities()

    result = get_municipality_geometry(
        municipalities_gdf=municipalities,
        municipality_name="Vila Real",
    )

    assert len(result) == 1

    assert (
        result.iloc[0]["municipio"]
        == "Vila Real"
    )

    assert (
        result.crs.to_epsg()
        == 4326
    )

def test_get_municipality_geometry_is_case_insensitive():
    """
    A busca pelo município deve funcionar
    independentemente de maiúsculas/minúsculas.
    """

    municipalities = create_test_municipalities()

    result = get_municipality_geometry(
        municipalities_gdf=municipalities,
        municipality_name="vila real",
    )

    assert (
        result.iloc[0]["municipio"]
        == "Vila Real"
    )

def test_get_municipality_geometry_rejects_unknown_municipality():
    """
    Um município inexistente deve gerar erro explícito.
    """

    municipalities = create_test_municipalities()

    with pytest.raises(
        ValueError,
        match="Município não encontrado",
    ):
        get_municipality_geometry(
            municipalities_gdf=municipalities,
            municipality_name="Município Inexistente",
        )

def test_get_municipalities_by_names():
    """
    Verifica a seleção simultânea de múltiplos municípios.
    """

    municipalities = create_test_municipalities()

    result = get_municipalities_by_names(
        municipalities_gdf=municipalities,
        municipality_names=[
            "Vila Real",
            "Bragança",
        ],
    )

    assert len(result) == 2

    assert set(
        result["municipio"]
    ) == {
        "Vila Real",
        "Bragança",
    }

    assert result.crs.to_epsg() == 4326

def test_get_municipalities_by_names_rejects_missing_name():
    """
    Se algum município solicitado não existir,
    a função deve gerar erro.
    """

    municipalities = create_test_municipalities()

    with pytest.raises(
        ValueError,
        match="Municípios não encontrados",
    ):
        get_municipalities_by_names(
            municipalities_gdf=municipalities,
            municipality_names=[
                "Vila Real",
                "Não Existe",
            ],
        )

def test_get_municipalities_by_nuts3():
    """
    Verifica se todos os municípios pertencentes
    à NUTS III selecionada são retornados.
    """

    municipalities = create_test_municipalities()

    result = get_municipalities_by_nuts3(
        municipalities_gdf=municipalities,
        nuts3_name="Douro",
    )

    assert len(result) == 2

    assert set(
        result["municipio"]
    ) == {
        "Vila Real",
        "Alijó",
    }

    assert result.crs.to_epsg() == 4326

def test_get_nuts3_bounds():
    """
    Verifica se os limites espaciais da NUTS III
    são retornados na ordem nominal correta.
    """

    municipalities = create_test_municipalities()

    region = get_municipalities_by_nuts3(
        municipalities_gdf=municipalities,
        nuts3_name="Douro",
    )

    xmin, ymin, xmax, ymax = region.total_bounds

    result = get_nuts3_bounds(
        municipalities_gdf=municipalities,
        nuts3_name="Douro",
    )

    assert result == {
        "xmin": float(xmin),
        "xmax": float(xmax),
        "ymin": float(ymin),
        "ymax": float(ymax),
    }

def test_get_municipalities_by_nuts3_list_combines_multiple_regions():
    """
    Uma área de intervenção do AquaHub pode ser a combinação de
    mais de uma NUTS III oficial (ex. Beira Interior). A função
    deve unir os municípios de todas as NUTS III solicitadas.
    """

    municipalities = create_test_municipalities()

    result = get_municipalities_by_nuts3_list(
        municipalities_gdf=municipalities,
        nuts3_names=["Douro", "Terras de Trás-os-Montes"],
    )

    assert len(result) == 3

    assert set(result["municipio"]) == {
        "Vila Real",
        "Alijó",
        "Bragança",
    }

    assert result.crs.to_epsg() == 4326

def test_get_municipalities_by_nuts3_list_is_case_insensitive():
    municipalities = create_test_municipalities()

    result = get_municipalities_by_nuts3_list(
        municipalities_gdf=municipalities,
        nuts3_names=["douro"],
    )

    assert set(result["municipio"]) == {"Vila Real", "Alijó"}

def test_get_municipalities_by_nuts3_list_rejects_empty_list():
    municipalities = create_test_municipalities()

    with pytest.raises(ValueError, match="não pode estar vazia"):
        get_municipalities_by_nuts3_list(
            municipalities_gdf=municipalities,
            nuts3_names=[],
        )

def test_get_municipalities_by_nuts3_list_rejects_missing_nuts3():
    municipalities = create_test_municipalities()

    with pytest.raises(ValueError, match="NUTS III não encontradas"):
        get_municipalities_by_nuts3_list(
            municipalities_gdf=municipalities,
            nuts3_names=["Douro", "Não Existe"],
        )

def test_get_municipalities_by_nuts3_list_deduplicates_municipalities():
    """
    Se o mesmo município aparecer sob mais de uma NUTS III
    solicitada (não deveria acontecer com dados reais, mas a
    função não deve duplicá-lo caso ocorra), ele deve aparecer
    apenas uma vez no resultado.
    """

    municipalities = create_test_municipalities()

    result = get_municipalities_by_nuts3_list(
        municipalities_gdf=municipalities,
        nuts3_names=["Douro", "Douro"],
    )

    assert len(result) == 2
    assert result["municipio"].is_unique
