from pathlib import Path

import geopandas as gpd
import pandas as pd

from src.boundary_processing import (
    get_municipalities_by_nuts3,
    get_municipalities_by_nuts3_list,
)

from src.climate_processing import process_climatology_for_regions


def process_nuts3_climatology(
    municipalities_gdf: gpd.GeoDataFrame,
    nuts3_name: str,
    chelsa_dir: Path,
    variable: str,
    period: str = "1981-2010",
    version: str = "2.1",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Executa o pipeline completo de climatologia para todos os
    municípios de uma região NUTS III, para qualquer variável
    CHELSA suportada.

    Parameters
    ----------
    municipalities_gdf : geopandas.GeoDataFrame
        Camada contendo todos os municípios.

    nuts3_name : str
        Nome da região NUTS III.

    chelsa_dir : Path
        Diretório contendo os rasters CHELSA.

    variable : str
        Variável CHELSA a processar.

    period : str
        Período climatológico.

    version : str
        Versão do CHELSA.

    Returns
    -------
    tuple[pandas.DataFrame, pandas.DataFrame]
        Resultados mensais e anuais dos municípios
        pertencentes à NUTS III.
    """

    regions_gdf = get_municipalities_by_nuts3(
        municipalities_gdf=municipalities_gdf,
        nuts3_name=nuts3_name,
        target_crs="EPSG:4326",
    )

    monthly_output, annual_output = (
        process_climatology_for_regions(
            chelsa_dir=chelsa_dir,
            regions_gdf=regions_gdf,
            variable=variable,
            period=period,
            version=version,
        )
    )

    return monthly_output, annual_output

def process_multi_nuts3_climatology(
    municipalities_gdf: gpd.GeoDataFrame,
    nuts3_names: list[str],
    chelsa_dir: Path,
    variable: str,
    period: str = "1981-2010",
    version: str = "2.1",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Executa o pipeline completo de climatologia para todos os
    municípios pertencentes a uma ou mais regiões NUTS III
    combinadas, para qualquer variável CHELSA suportada.

    Existe para áreas de intervenção do AquaHub que não
    correspondem a uma única NUTS III oficial (ex. "Beira
    Interior" pode ser a combinação de várias NUTS III da CAOP,
    dependendo da classificação em uso). Para uma única NUTS III,
    process_nuts3_climatology é suficiente e mais direto.

    Parameters
    ----------
    municipalities_gdf : geopandas.GeoDataFrame
        Camada contendo todos os municípios.

    nuts3_names : list[str]
        Nomes das regiões NUTS III a combinar.

    chelsa_dir : Path
        Diretório contendo os rasters CHELSA.

    variable : str
        Variável CHELSA a processar.

    period : str
        Período climatológico.

    version : str
        Versão do CHELSA.

    Returns
    -------
    tuple[pandas.DataFrame, pandas.DataFrame]
        Resultados mensais e anuais dos municípios pertencentes
        às NUTS III combinadas.
    """

    regions_gdf = get_municipalities_by_nuts3_list(
        municipalities_gdf=municipalities_gdf,
        nuts3_names=nuts3_names,
        target_crs="EPSG:4326",
    )

    monthly_output, annual_output = (
        process_climatology_for_regions(
            chelsa_dir=chelsa_dir,
            regions_gdf=regions_gdf,
            variable=variable,
            period=period,
            version=version,
        )
    )

    return monthly_output, annual_output
