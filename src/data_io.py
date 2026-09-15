from pathlib import Path

import pandas as pd

def _save_climatology_pair(
    monthly_df: pd.DataFrame,
    annual_df: pd.DataFrame,
    output_dir: Path,
    dataset_slug: str,
    variable: str,
    period: str,
) -> tuple[Path, Path]:
    """
    Função interna responsável por salvar um par
    de resultados climatológicos mensal e anual.

    Parameters
    ----------
    monthly_df : pandas.DataFrame
        Dados climatológicos mensais.

    annual_df : pandas.DataFrame
        Dados climatológicos anuais.

    output_dir : Path
        Diretório de saída.

    dataset_slug : str
        Identificador utilizado no nome dos arquivos.
        Exemplos:
        - vila_real
        - municipalities
        - nuts3_douro

    variable : str
        Variável climática.

    period : str
        Período climatológico.

    Returns
    -------
    tuple[Path, Path]
        Caminhos dos arquivos mensal e anual.
    """

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    monthly_path = (
        output_dir
        / f"{dataset_slug}_{variable}_monthly_{period}.parquet"
    )

    annual_path = (
        output_dir
        / f"{dataset_slug}_{variable}_annual_{period}.parquet"
    )

    monthly_df.to_parquet(
        monthly_path,
        index=False,
    )

    annual_df.to_parquet(
        annual_path,
        index=False,
    )

    return monthly_path, annual_path

def save_climatology_results(
    monthly_df: pd.DataFrame,
    annual_df: pd.DataFrame,
    output_dir: Path,
    municipality_slug: str,
    variable: str,
    period: str,
) -> tuple[Path, Path]:
    """
    Salva resultados climatológicos mensal e anual
    de um município.
    """

    return _save_climatology_pair(
        monthly_df=monthly_df,
        annual_df=annual_df,
        output_dir=output_dir,
        dataset_slug=municipality_slug,
        variable=variable,
        period=period,
    )

def save_batch_climatology_results(
    monthly_df: pd.DataFrame,
    annual_df: pd.DataFrame,
    output_dir: Path,
    variable: str,
    period: str,
) -> tuple[Path, Path]:
    """
    Salva resultados climatológicos consolidados
    de múltiplos municípios.
    """

    return _save_climatology_pair(
        monthly_df=monthly_df,
        annual_df=annual_df,
        output_dir=output_dir,
        dataset_slug="municipalities",
        variable=variable,
        period=period,
    )

def save_regional_climatology_results(
    monthly_df: pd.DataFrame,
    annual_df: pd.DataFrame,
    output_dir: Path,
    region_slug: str,
    variable: str,
    period: str,
) -> tuple[Path, Path]:
    """
    Salva resultados climatológicos consolidados
    de uma região administrativa.
    """

    return _save_climatology_pair(
        monthly_df=monthly_df,
        annual_df=annual_df,
        output_dir=output_dir,
        dataset_slug=f"nuts3_{region_slug}",
        variable=variable,
        period=period,
    )