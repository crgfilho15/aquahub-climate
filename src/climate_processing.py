from pathlib import Path
import calendar
import geopandas as gpd
import pandas as pd
from exactextract import exact_extract

def calculate_monthly_temperature(
    raster_path: Path,
    region_gdf: gpd.GeoDataFrame,
    month: int,
    municipality_name: str,
) -> dict:
    """
    Calcula a temperatura média espacial de um raster CHELSA
    para uma única região.

    Esta função mantém compatibilidade com a interface
    original, utilizando internamente o processamento
    regional.
    """

    if len(region_gdf) != 1:
        raise ValueError(
            "region_gdf deve conter exatamente uma região."
        )

    region = region_gdf.copy()

    region["municipio"] = municipality_name

    result = calculate_monthly_temperature_for_regions(
        raster_path=raster_path,
        regions_gdf=region,
        month=month,
    )

    row = result.iloc[0]

    return {
        "municipality": row["municipality"],
        "month": int(row["month"]),
        "mean_kelvin": float(row["mean_kelvin"]),
        "mean_celsius": float(row["mean_celsius"]),
    }

def calculate_monthly_temperature_climatology(
    chelsa_dir: Path,
    region_gdf: gpd.GeoDataFrame,
    municipality_name: str,
    period: str = "1981-2010",
    version: str = "2.1",
) -> pd.DataFrame:
    """
    Calcula a climatologia mensal de temperatura
    para uma única região.

    Esta função mantém compatibilidade com a interface
    original, utilizando internamente o processamento
    regional.
    """

    if len(region_gdf) != 1:
        raise ValueError(
            "region_gdf deve conter exatamente uma região."
        )

    region = region_gdf.copy()

    region["municipio"] = municipality_name

    monthly_output = (
        calculate_monthly_temperature_climatology_for_regions(
            chelsa_dir=chelsa_dir,
            regions_gdf=region,
            period=period,
            version=version,
        )
    )

    # Mantém exatamente a estrutura retornada
    # pela versão original da função.
    return monthly_output[
        [
            "municipality",
            "month",
            "mean_kelvin",
            "mean_celsius",
        ]
    ].copy()

def calculate_annual_temperature_climatology(
    monthly_df: pd.DataFrame,
    start_year: int,
    end_year: int,
) -> float:
    """
    Calcula a temperatura média anual climatológica
    para uma única região.

    Esta função mantém compatibilidade com a interface
    original, utilizando internamente o processamento
    regional.
    """

    if "municipality" not in monthly_df.columns:
        raise ValueError(
            "monthly_df deve conter a coluna 'municipality'."
        )

    municipalities = (
        monthly_df["municipality"]
        .dropna()
        .unique()
    )

    if len(municipalities) != 1:
        raise ValueError(
            "monthly_df deve conter exatamente uma região."
        )

    annual_output = (
        calculate_annual_temperature_climatology_for_regions(
            monthly_df=monthly_df,
            start_year=start_year,
            end_year=end_year,
        )
    )

    return float(
        annual_output.loc[0, "mean_celsius"]
    )

def process_temperature_climatology(
    chelsa_dir: Path,
    region_gdf: gpd.GeoDataFrame,
    municipality_name: str,
    period: str = "1981-2010",
    version: str = "2.1",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Processa a climatologia de temperatura média (tas)
    para uma única região.

    Esta função mantém compatibilidade com a interface
    original, utilizando internamente o pipeline regional.

    Parameters
    ----------
    chelsa_dir : Path
        Diretório contendo os rasters CHELSA.

    region_gdf : geopandas.GeoDataFrame
        GeoDataFrame contendo exatamente uma região.

    municipality_name : str
        Nome da região/município.

    period : str
        Período climatológico.

    version : str
        Versão do CHELSA.

    Returns
    -------
    tuple[pandas.DataFrame, pandas.DataFrame]
        Resultado mensal e resultado anual.
    """

    if len(region_gdf) != 1:
        raise ValueError(
            "region_gdf deve conter exatamente uma região."
        )

    region = region_gdf.copy()

    # Garante compatibilidade com o núcleo regional,
    # mesmo que a geometria original não possua
    # uma coluna chamada 'municipio'.
    region["municipio"] = municipality_name

    monthly_output, annual_output = (
        process_temperature_climatology_for_regions(
            chelsa_dir=chelsa_dir,
            regions_gdf=region,
            period=period,
            version=version,
        )
    )

    return monthly_output, annual_output

def calculate_monthly_temperature_for_regions(
    raster_path: Path,
    regions_gdf: gpd.GeoDataFrame,
    month: int,
) -> pd.DataFrame:
    """
    Calcula a temperatura média espacial de um raster CHELSA
    para múltiplas regiões em uma única operação.

    Parameters
    ----------
    raster_path : Path
        Caminho para o raster CHELSA.

    regions_gdf : geopandas.GeoDataFrame
        Regiões a processar. Deve conter a coluna 'municipio'
        e estar no mesmo CRS do raster.

    month : int
        Número do mês, entre 1 e 12.

    Returns
    -------
    pandas.DataFrame
        Tabela contendo uma linha por município,
        com temperatura média em Kelvin e Celsius.
    """

    if "municipio" not in regions_gdf.columns:
        raise ValueError(
            "regions_gdf deve conter a coluna 'municipio'."
        )

    if not 1 <= month <= 12:
        raise ValueError(
            "month deve estar entre 1 e 12."
        )

    result = exact_extract(
        raster_path,
        regions_gdf,
        [
            "mean_kelvin=mean(coverage_weight=area_spherical_m2)"
        ],
        include_cols=[
            "municipio"
        ],
        output="pandas",
    )

    result = result.rename(
        columns={
            "municipio": "municipality"
        }
    )

    result["month"] = month

    result["mean_kelvin"] = (
        result["mean_kelvin"].astype(float)
    )

    result["mean_celsius"] = (
        result["mean_kelvin"] - 273.15
    )

    return result[
        [
            "municipality",
            "month",
            "mean_kelvin",
            "mean_celsius",
        ]
    ]

def calculate_monthly_temperature_climatology_for_regions(
    chelsa_dir: Path,
    regions_gdf: gpd.GeoDataFrame,
    period: str = "1981-2010",
    version: str = "2.1",
) -> pd.DataFrame:
    """
    Calcula a climatologia mensal de temperatura
    para múltiplas regiões.

    Cada raster mensal CHELSA é processado uma única vez
    para todas as regiões fornecidas.

    Parameters
    ----------
    chelsa_dir : Path
        Diretório contendo os rasters CHELSA.

    regions_gdf : geopandas.GeoDataFrame
        Regiões que serão processadas.
        Deve conter a coluna 'municipio'.

    period : str
        Período climatológico.

    version : str
        Versão do CHELSA.

    Returns
    -------
    pandas.DataFrame
        Climatologia mensal contendo uma linha
        por município e mês.
    """

    monthly_results = []

    for month in range(1, 13):

        month_str = f"{month:02d}"

        raster_path = (
            chelsa_dir
            / f"CHELSA_tas_{month_str}_{period}_V.{version}.tif"
        )

        if not raster_path.exists():
            raise FileNotFoundError(
                f"Raster não encontrado: {raster_path}"
            )

        month_result = (
            calculate_monthly_temperature_for_regions(
                raster_path=raster_path,
                regions_gdf=regions_gdf,
                month=month,
            )
        )

        monthly_results.append(
            month_result
        )

    monthly_output = pd.concat(
        monthly_results,
        ignore_index=True,
    )

    monthly_output["variable"] = "tas"
    monthly_output["period"] = period
    monthly_output["source"] = (
        f"CHELSA climatologies v{version}"
    )

    return monthly_output

def calculate_annual_temperature_climatology_for_regions(
    monthly_df: pd.DataFrame,
    start_year: int,
    end_year: int,
) -> pd.DataFrame:
    """
    Calcula a temperatura média anual climatológica
    para múltiplas regiões.

    Cada município é calculado separadamente,
    ponderando os meses pelo número real de dias
    do período climatológico.

    Parameters
    ----------
    monthly_df : pandas.DataFrame
        Deve conter:
        - municipality
        - month
        - mean_celsius

    start_year : int
        Primeiro ano do período.

    end_year : int
        Último ano do período.

    Returns
    -------
    pandas.DataFrame
        Uma linha por município com a temperatura
        média anual climatológica.
    """

    required_columns = {
        "municipality",
        "month",
        "mean_celsius",
    }

    missing_columns = (
        required_columns
        - set(monthly_df.columns)
    )

    if missing_columns:
        raise ValueError(
            f"Colunas ausentes: {missing_columns}"
        )

    years = range(
        start_year,
        end_year + 1
    )

    days_by_month = {
        month: sum(
            calendar.monthrange(year, month)[1]
            for year in years
        )
        for month in range(1, 13)
    }

    df = monthly_df.copy()

    df["days"] = (
        df["month"]
        .map(days_by_month)
    )

    df["weighted_temperature"] = (
        df["mean_celsius"]
        * df["days"]
    )

    annual = (
        df
        .groupby(
            "municipality",
            as_index=False
        )
        .agg(
            weighted_sum=(
                "weighted_temperature",
                "sum"
            ),
            total_days=(
                "days",
                "sum"
            ),
        )
    )

    annual["mean_celsius"] = (
        annual["weighted_sum"]
        / annual["total_days"]
    )

    annual = annual[
        [
            "municipality",
            "mean_celsius",
        ]
    ]

    return annual

def process_temperature_climatology_for_regions(
    chelsa_dir: Path,
    regions_gdf: gpd.GeoDataFrame,
    period: str = "1981-2010",
    version: str = "2.1",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Processa a climatologia de temperatura média (tas)
    para múltiplas regiões.

    O processamento inclui:
    - climatologia mensal para todas as regiões;
    - média anual ponderada pelos dias reais do período;
    - inclusão de metadados.

    Returns
    -------
    tuple[pandas.DataFrame, pandas.DataFrame]
        Resultado mensal e resultado anual.
    """

    # 1. Climatologia mensal regional
    monthly_output = (
        calculate_monthly_temperature_climatology_for_regions(
            chelsa_dir=chelsa_dir,
            regions_gdf=regions_gdf,
            period=period,
            version=version,
        )
    )

    # 2. Extrair anos do período
    start_year, end_year = map(
        int,
        period.split("-")
    )

    # 3. Média anual por região
    annual_output = (
        calculate_annual_temperature_climatology_for_regions(
            monthly_df=monthly_output,
            start_year=start_year,
            end_year=end_year,
        )
    )

    # 4. Metadados anuais
    annual_output["variable"] = "tas"
    annual_output["period"] = period
    annual_output["source"] = (
        f"CHELSA climatologies v{version}"
    )

    annual_output = annual_output[
        [
            "municipality",
            "variable",
            "period",
            "mean_celsius",
            "source",
        ]
    ]

    return monthly_output, annual_output