import pandas as pd

from src.data_io import (
    save_climatology_results,
    save_batch_climatology_results,
    save_regional_climatology_results,
)

def create_test_data():
    """
    Cria dados climatológicos artificiais
    para testes de persistência.
    """

    monthly = pd.DataFrame(
        {
            "municipality": ["Test Region"] * 12,
            "month": range(1, 13),
            "mean_celsius": [10.0] * 12,
        }
    )

    annual = pd.DataFrame(
        {
            "municipality": ["Test Region"],
            "variable": ["tas"],
            "period": ["1981-2010"],
            "mean_celsius": [10.0],
            "source": ["Test Source"],
        }
    )

    return monthly, annual

def test_save_climatology_results(tmp_path):
    """
    Verifica o salvamento de resultados
    de um município.
    """

    monthly, annual = create_test_data()

    monthly_path, annual_path = (
        save_climatology_results(
            monthly_df=monthly,
            annual_df=annual,
            output_dir=tmp_path,
            municipality_slug="test_region",
            variable="tas",
            period="1981-2010",
        )
    )

    assert monthly_path.exists()
    assert annual_path.exists()

    assert (
        monthly_path.name
        == "test_region_tas_monthly_1981-2010.parquet"
    )

    assert (
        annual_path.name
        == "test_region_tas_annual_1981-2010.parquet"
    )

    monthly_loaded = pd.read_parquet(
        monthly_path
    )

    annual_loaded = pd.read_parquet(
        annual_path
    )

    pd.testing.assert_frame_equal(
        monthly_loaded,
        monthly,
    )

    pd.testing.assert_frame_equal(
        annual_loaded,
        annual,
    )

def test_save_batch_climatology_results(tmp_path):
    """
    Verifica o padrão de nomes dos arquivos
    consolidados de múltiplos municípios.
    """

    monthly, annual = create_test_data()

    monthly_path, annual_path = (
        save_batch_climatology_results(
            monthly_df=monthly,
            annual_df=annual,
            output_dir=tmp_path,
            variable="tas",
            period="1981-2010",
        )
    )

    assert (
        monthly_path.name
        == "municipalities_tas_monthly_1981-2010.parquet"
    )

    assert (
        annual_path.name
        == "municipalities_tas_annual_1981-2010.parquet"
    )

    assert monthly_path.exists()
    assert annual_path.exists()

def test_save_regional_climatology_results(tmp_path):
    """
    Verifica o padrão de nomes dos arquivos
    de uma NUTS III.
    """

    monthly, annual = create_test_data()

    monthly_path, annual_path = (
        save_regional_climatology_results(
            monthly_df=monthly,
            annual_df=annual,
            output_dir=tmp_path,
            region_slug="douro",
            variable="tas",
            period="1981-2010",
        )
    )

    assert (
        monthly_path.name
        == "nuts3_douro_tas_monthly_1981-2010.parquet"
    )

    assert (
        annual_path.name
        == "nuts3_douro_tas_annual_1981-2010.parquet"
    )

    assert monthly_path.exists()
    assert annual_path.exists()