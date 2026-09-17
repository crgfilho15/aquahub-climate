from pathlib import Path

import geopandas as gpd
import pandas as pd

from src.boundary_processing import (
    get_municipality_geometry,
    get_municipalities_by_names,
    get_municipalities_by_nuts3,
)

from src.climate_processing import (
    process_climatology_for_regions,
    process_temperature_climatology,
    process_temperature_climatology_for_regions,
)


def process_municipality_temperature(
    municipalities_gdf: gpd.GeoDataFrame,
    municipality_name: str,
    chelsa_dir: Path,
    period: str = "1981-2010",
    version: str = "2.1",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Executa o pipeline completo de climatologia de temperatura
    para um município.

    O fluxo inclui:

    1. seleção do município;
    2. reprojeção para EPSG:4326;
    3. processamento dos 12 rasters mensais CHELSA;
    4. cálculo da climatologia mensal;
    5. cálculo da média anual climatológica.

    Parameters
    ----------
    municipalities_gdf : geopandas.GeoDataFrame
        Camada contendo os municípios.

    municipality_name : str
        Nome do município a processar.

    chelsa_dir : Path
        Diretório contendo os rasters CHELSA.

    period : str
        Período climatológico.

    version : str
        Versão do CHELSA.

    Returns
    -------
    tuple[pandas.DataFrame, pandas.DataFrame]
        Resultado mensal e resultado anual.
    """

    municipality_geometry = get_municipality_geometry(
        municipalities_gdf=municipalities_gdf,
        municipality_name=municipality_name,
        target_crs="EPSG:4326",
    )

    monthly_output, annual_output = (
        process_temperature_climatology(
            chelsa_dir=chelsa_dir,
            region_gdf=municipality_geometry,
            municipality_name=municipality_name,
            period=period,
            version=version,
        )
    )

    return monthly_output, annual_output

def process_multiple_municipalities_temperature(
    municipalities_gdf: gpd.GeoDataFrame,
    municipality_names: list[str],
    chelsa_dir: Path,
    period: str = "1981-2010",
    version: str = "2.1",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Processa a climatologia de temperatura para vários municípios.

    Os municípios são selecionados em conjunto e os rasters
    mensais CHELSA são processados regionalmente, evitando
    repetir a leitura/processamento para cada município.

    Parameters
    ----------
    municipalities_gdf : geopandas.GeoDataFrame
        Camada contendo todos os municípios.

    municipality_names : list[str]
        Lista de municípios a processar.

    chelsa_dir : Path
        Diretório contendo os rasters CHELSA.

    period : str
        Período climatológico.

    version : str
        Versão do CHELSA.

    Returns
    -------
    tuple[pandas.DataFrame, pandas.DataFrame]
        Resultado mensal e resultado anual
        dos municípios selecionados.
    """

    regions_gdf = get_municipalities_by_names(
        municipalities_gdf=municipalities_gdf,
        municipality_names=municipality_names,
        target_crs="EPSG:4326",
    )

    monthly_output, annual_output = (
        process_temperature_climatology_for_regions(
            chelsa_dir=chelsa_dir,
            regions_gdf=regions_gdf,
            period=period,
            version=version,
        )
    )

    return monthly_output, annual_output

def process_nuts3_temperature(
    municipalities_gdf: gpd.GeoDataFrame,
    nuts3_name: str,
    chelsa_dir: Path,
    period: str = "1981-2010",
    version: str = "2.1",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Executa o pipeline completo de climatologia de temperatura
    para todos os municípios de uma região NUTS III.

    O fluxo inclui:

    1. seleção automática dos municípios da NUTS III;
    2. reprojeção para EPSG:4326;
    3. processamento regional dos 12 rasters CHELSA;
    4. cálculo das climatologias mensais;
    5. cálculo das médias anuais por município.

    Parameters
    ----------
    municipalities_gdf : geopandas.GeoDataFrame
        Camada contendo todos os municípios.

    nuts3_name : str
        Nome da região NUTS III.

    chelsa_dir : Path
        Diretório contendo os rasters CHELSA.

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
        process_temperature_climatology_for_regions(
            chelsa_dir=chelsa_dir,
            regions_gdf=regions_gdf,
            period=period,
            version=version,
        )
    )

    return monthly_output, annual_output

# ---------------------------------------------------------------------
# Pipeline genérico, parametrizado por variável.
#
# 'tas' é a única variável validada com dados CHELSA reais até agora,
# mas 'tasmin', 'tasmax' e 'pr' seguem exatamente o mesmo formato de
# arquivo CHELSA e a mesma lógica de estatística zonal, diferindo
# apenas na conversão de unidade (ver
# src.climate_processing.CHELSA_VARIABLE_UNITS). As funções
# *_temperature acima continuam válidas e inalteradas: são casos
# específicos deste pipeline genérico para 'tas'.
# ---------------------------------------------------------------------

def process_municipality_climatology(
    municipalities_gdf: gpd.GeoDataFrame,
    municipality_name: str,
    chelsa_dir: Path,
    variable: str,
    period: str = "1981-2010",
    version: str = "2.1",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Executa o pipeline completo de climatologia para um
    município, para qualquer variável CHELSA suportada.

    Parameters
    ----------
    municipalities_gdf : geopandas.GeoDataFrame
        Camada contendo os municípios.

    municipality_name : str
        Nome do município a processar.

    chelsa_dir : Path
        Diretório contendo os rasters CHELSA.

    variable : str
        Variável CHELSA a processar (ex. 'tas', 'tasmin',
        'tasmax', 'pr').

    period : str
        Período climatológico.

    version : str
        Versão do CHELSA.

    Returns
    -------
    tuple[pandas.DataFrame, pandas.DataFrame]
        Resultado mensal e resultado anual.
    """

    municipality_geometry = get_municipality_geometry(
        municipalities_gdf=municipalities_gdf,
        municipality_name=municipality_name,
        target_crs="EPSG:4326",
    )

    municipality_geometry = municipality_geometry.copy()
    municipality_geometry["municipio"] = municipality_name

    monthly_output, annual_output = (
        process_climatology_for_regions(
            chelsa_dir=chelsa_dir,
            regions_gdf=municipality_geometry,
            variable=variable,
            period=period,
            version=version,
        )
    )

    return monthly_output, annual_output

def process_multiple_municipalities_climatology(
    municipalities_gdf: gpd.GeoDataFrame,
    municipality_names: list[str],
    chelsa_dir: Path,
    variable: str,
    period: str = "1981-2010",
    version: str = "2.1",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Processa a climatologia de vários municípios, para
    qualquer variável CHELSA suportada.

    Parameters
    ----------
    municipalities_gdf : geopandas.GeoDataFrame
        Camada contendo todos os municípios.

    municipality_names : list[str]
        Lista de municípios a processar.

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
        Resultado mensal e resultado anual
        dos municípios selecionados.
    """

    regions_gdf = get_municipalities_by_names(
        municipalities_gdf=municipalities_gdf,
        municipality_names=municipality_names,
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