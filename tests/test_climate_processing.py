import pandas as pd
import pytest

from src.climate_processing import (
    calculate_annual_temperature_climatology,
    calculate_annual_temperature_climatology_for_regions,
)

from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio

from rasterio.transform import from_origin
from shapely.geometry import box

from src.climate_processing import (
    calculate_annual_climatology_for_regions,
    calculate_annual_temperature_climatology,
    calculate_annual_temperature_climatology_for_regions,
    calculate_monthly_climatology_for_regions,
    calculate_monthly_temperature_for_regions,
    calculate_monthly_value_for_regions,
    process_climatology_for_regions,
)

def test_annual_temperature_single_region_constant_values():
    """
    Se todos os meses possuem temperatura de 10 °C,
    a média anual também deve ser 10 °C,
    independentemente da ponderação pelos dias.
    """

    monthly_df = pd.DataFrame(
        {
            "municipality": ["Test Region"] * 12,
            "month": range(1, 13),
            "mean_celsius": [10.0] * 12,
        }
    )

    result = calculate_annual_temperature_climatology(
        monthly_df=monthly_df,
        start_year=1981,
        end_year=2010,
    )

    assert abs(result - 10.0) < 1e-10

def test_annual_temperature_multiple_regions():
    """
    Verifica se regiões diferentes são calculadas
    separadamente.
    """

    monthly_df = pd.DataFrame(
        {
            "municipality": (
                ["Region A"] * 12
                + ["Region B"] * 12
            ),
            "month": (
                list(range(1, 13))
                + list(range(1, 13))
            ),
            "mean_celsius": (
                [10.0] * 12
                + [20.0] * 12
            ),
        }
    )

    result = (
        calculate_annual_temperature_climatology_for_regions(
            monthly_df=monthly_df,
            start_year=1981,
            end_year=2010,
        )
    )

    region_a = result.loc[
        result["municipality"] == "Region A",
        "mean_celsius",
    ].iloc[0]

    region_b = result.loc[
        result["municipality"] == "Region B",
        "mean_celsius",
    ].iloc[0]

    assert abs(region_a - 10.0) < 1e-10
    assert abs(region_b - 20.0) < 1e-10
    
def test_annual_temperature_uses_calendar_day_weighting():
    """
    Verifica se a média anual utiliza corretamente
    o número real de dias representado por cada mês
    durante o período 1981-2010.

    Apenas fevereiro possui temperatura diferente
    de zero, permitindo verificar diretamente
    o peso temporal aplicado.
    """

    temperatures = [0.0] * 12

    # Fevereiro
    temperatures[1] = 10.0

    monthly_df = pd.DataFrame(
        {
            "municipality": ["Test Region"] * 12,
            "month": range(1, 13),
            "mean_celsius": temperatures,
        }
    )

    result = calculate_annual_temperature_climatology(
        monthly_df=monthly_df,
        start_year=1981,
        end_year=2010,
    )

    # 1981-2010 contém:
    # 847 dias de fevereiro
    # 10 957 dias no total
    expected = (
        10.0 * 847
        / 10957
    )

    assert abs(
        result - expected
    ) < 1e-10
    
def test_single_region_annual_temperature_rejects_multiple_regions():
    """
    A função destinada a uma única região deve rejeitar
    DataFrames contendo mais de um município.
    """

    monthly_df = pd.DataFrame(
        {
            "municipality": (
                ["Region A"] * 12
                + ["Region B"] * 12
            ),
            "month": (
                list(range(1, 13))
                + list(range(1, 13))
            ),
            "mean_celsius": (
                [10.0] * 12
                + [20.0] * 12
            ),
        }
    )

    with pytest.raises(
        ValueError,
        match="exatamente uma região",
    ):
        calculate_annual_temperature_climatology(
            monthly_df=monthly_df,
            start_year=1981,
            end_year=2010,
        )
        
def test_monthly_temperature_for_regions_with_synthetic_raster(
    tmp_path,
):
    """
    Teste de integração entre:

    Rasterio
    + GeoPandas
    + exactextract

    utilizando um raster artificial com valores conhecidos.
    """

    raster_path = (
        tmp_path
        / "synthetic_temperature.tif"
    )

    # Raster 2 x 2:
    #
    # 280 K | 282 K
    # 284 K | 286 K

    raster_data = np.array(
        [
            [280.0, 282.0],
            [284.0, 286.0],
        ],
        dtype=np.float32,
    )

    transform = from_origin(
        west=0,
        north=2,
        xsize=1,
        ysize=1,
    )

    with rasterio.open(
        raster_path,
        "w",
        driver="GTiff",
        height=2,
        width=2,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
    ) as dst:
        dst.write(
            raster_data,
            1,
        )

    regions = gpd.GeoDataFrame(
        {
            "municipio": [
                "North Region",
                "South Region",
            ],
        },
        geometry=[
            # cobre exatamente os dois pixels superiores
            box(0, 1, 2, 2),

            # cobre exatamente os dois pixels inferiores
            box(0, 0, 2, 1),
        ],
        crs="EPSG:4326",
    )

    result = (
        calculate_monthly_temperature_for_regions(
            raster_path=raster_path,
            regions_gdf=regions,
            month=1,
        )
    )

    north_kelvin = result.loc[
        result["municipality"] == "North Region",
        "mean_kelvin",
    ].iloc[0]

    south_kelvin = result.loc[
        result["municipality"] == "South Region",
        "mean_kelvin",
    ].iloc[0]

    # Norte:
    # (280 + 282) / 2 = 281 K

    assert abs(
        north_kelvin - 281.0
    ) < 1e-6

    # Sul:
    # (284 + 286) / 2 = 285 K

    assert abs(
        south_kelvin - 285.0
    ) < 1e-6

    north_celsius = result.loc[
        result["municipality"] == "North Region",
        "mean_celsius",
    ].iloc[0]

    assert abs(
        north_celsius - 7.85
    ) < 1e-6
    
def test_monthly_temperature_uses_partial_pixel_coverage(
    tmp_path,
):
    """
    Verifica se pixels parcialmente intersectados
    contribuem proporcionalmente para a média espacial.

    Raster:

    280 K | 300 K

    O polígono cobre:
    - 100% do primeiro pixel;
    - 50% do segundo pixel.

    Média esperada:

    (280 * 1.0 + 300 * 0.5) / 1.5
    = 286.666666... K
    """

    raster_path = (
        tmp_path
        / "partial_coverage.tif"
    )

    raster_data = np.array(
        [
            [280.0, 300.0],
        ],
        dtype=np.float32,
    )

    transform = from_origin(
        west=0,
        north=1,
        xsize=1,
        ysize=1,
    )

    with rasterio.open(
        raster_path,
        "w",
        driver="GTiff",
        height=1,
        width=2,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
    ) as dst:
        dst.write(
            raster_data,
            1,
        )

    regions = gpd.GeoDataFrame(
        {
            "municipio": [
                "Partial Region",
            ],
        },
        geometry=[
            # Primeiro pixel completo:
            # x = 0 até 1
            #
            # Segundo pixel pela metade:
            # x = 1 até 1.5
            box(0, 0, 1.5, 1),
        ],
        crs="EPSG:4326",
    )

    result = (
        calculate_monthly_temperature_for_regions(
            raster_path=raster_path,
            regions_gdf=regions,
            month=1,
        )
    )

    mean_kelvin = result.loc[
        0,
        "mean_kelvin",
    ]

    expected_kelvin = (
        (280.0 * 1.0)
        + (300.0 * 0.5)
    ) / 1.5

    assert abs(
        mean_kelvin
        - expected_kelvin
    ) < 1e-6

# ---------------------------------------------------------------------
# Núcleo genérico (multi-variável): calculate_monthly_value_for_regions,
# calculate_monthly_climatology_for_regions,
# calculate_annual_climatology_for_regions, process_climatology_for_regions.
# ---------------------------------------------------------------------

def _write_synthetic_raster(path, values):
    """Grava um raster 1x2 EPSG:4326 com os valores fornecidos."""

    raster_data = np.array([values], dtype=np.float32)

    transform = from_origin(west=0, north=1, xsize=1, ysize=1)

    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=1,
        width=2,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
    ) as dst:
        dst.write(raster_data, 1)

def _one_pixel_region(name):
    return gpd.GeoDataFrame(
        {"municipio": [name]},
        geometry=[box(0, 0, 1, 1)],
        crs="EPSG:4326",
    )

def test_monthly_value_for_regions_converts_temperature_variable(tmp_path):
    """
    Para variáveis de temperatura (tas, tasmin, tasmax), o valor
    nativo (Kelvin) deve ser convertido para Celsius.
    """

    raster_path = tmp_path / "synthetic_tasmin.tif"
    _write_synthetic_raster(raster_path, [280.0, 280.0])

    result = calculate_monthly_value_for_regions(
        raster_path=raster_path,
        regions_gdf=_one_pixel_region("Region"),
        month=1,
        variable="tasmin",
    )

    row = result.iloc[0]

    assert abs(row["mean_native"] - 280.0) < 1e-6
    assert abs(row["mean_value"] - 6.85) < 1e-6
    assert row["unit"] == "celsius"

def test_monthly_value_for_regions_does_not_convert_precipitation(tmp_path):
    """
    Precipitação (pr) já é entregue pelo CHELSA na unidade final
    (mm) e não deve sofrer a conversão Kelvin -> Celsius.
    """

    raster_path = tmp_path / "synthetic_pr.tif"
    _write_synthetic_raster(raster_path, [45.0, 45.0])

    result = calculate_monthly_value_for_regions(
        raster_path=raster_path,
        regions_gdf=_one_pixel_region("Region"),
        month=1,
        variable="pr",
    )

    row = result.iloc[0]

    assert abs(row["mean_native"] - 45.0) < 1e-6
    assert abs(row["mean_value"] - 45.0) < 1e-6
    assert row["unit"] == "mm"

def test_monthly_value_for_regions_rejects_unsupported_variable(tmp_path):
    raster_path = tmp_path / "synthetic_unknown.tif"
    _write_synthetic_raster(raster_path, [45.0, 45.0])

    with pytest.raises(ValueError, match="não suportada"):
        calculate_monthly_value_for_regions(
            raster_path=raster_path,
            regions_gdf=_one_pixel_region("Region"),
            month=1,
            variable="rsds",
        )

def test_monthly_climatology_for_regions_builds_variable_specific_filenames(
    tmp_path,
):
    """
    O núcleo genérico deve procurar os rasters usando o padrão
    de nome de arquivo CHELSA_{variable}_MM_{period}_V.{version}.tif,
    para qualquer variável suportada — não apenas 'tas'.
    """

    for month in range(1, 13):
        raster_path = (
            tmp_path / f"CHELSA_tasmax_{month:02d}_1981-2010_V.2.1.tif"
        )
        _write_synthetic_raster(raster_path, [300.0, 300.0])

    monthly_output = calculate_monthly_climatology_for_regions(
        chelsa_dir=tmp_path,
        regions_gdf=_one_pixel_region("Region"),
        variable="tasmax",
        period="1981-2010",
        version="2.1",
    )

    assert len(monthly_output) == 12
    assert (monthly_output["variable"] == "tasmax").all()
    assert (monthly_output["unit"] == "celsius").all()
    assert monthly_output["mean_value"].round(2).eq(26.85).all()

def test_annual_climatology_for_regions_uses_calendar_day_weighting():
    """
    Equivalente genérico de
    test_annual_temperature_uses_calendar_day_weighting, operando
    sobre a coluna 'mean_value' em vez de 'mean_celsius'.
    """

    values = [0.0] * 12
    values[1] = 10.0  # Fevereiro

    monthly_df = pd.DataFrame(
        {
            "municipality": ["Test Region"] * 12,
            "month": range(1, 13),
            "mean_value": values,
        }
    )

    annual = calculate_annual_climatology_for_regions(
        monthly_df=monthly_df,
        start_year=1981,
        end_year=2010,
    )

    expected = 10.0 * 847 / 10957

    assert abs(annual.loc[0, "mean_value"] - expected) < 1e-10

def test_process_climatology_for_regions_end_to_end_precipitation(tmp_path):
    """
    Teste de integração do núcleo genérico para 'pr', confirmando
    que o pipeline completo (mensal + anual) preserva a unidade
    correta e não aplica a conversão de temperatura.
    """

    for month in range(1, 13):
        raster_path = tmp_path / f"CHELSA_pr_{month:02d}_1981-2010_V.2.1.tif"
        _write_synthetic_raster(raster_path, [60.0, 60.0])

    monthly_output, annual_output = process_climatology_for_regions(
        chelsa_dir=tmp_path,
        regions_gdf=_one_pixel_region("Region"),
        variable="pr",
        period="1981-2010",
        version="2.1",
    )

    assert (monthly_output["unit"] == "mm").all()

    annual_row = annual_output.iloc[0]

    assert annual_row["variable"] == "pr"
    assert annual_row["unit"] == "mm"
    assert abs(annual_row["mean_value"] - 60.0) < 1e-6
    assert annual_row["source"] == "CHELSA climatologies v2.1"