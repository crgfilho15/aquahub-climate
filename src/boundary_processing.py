import geopandas as gpd


def get_municipality_geometry(
    municipalities_gdf: gpd.GeoDataFrame,
    municipality_name: str,
    target_crs: str = "EPSG:4326",
) -> gpd.GeoDataFrame:
    """
    Seleciona um município da camada administrativa
    e reprojeta a geometria para o CRS desejado.

    Parameters
    ----------
    municipalities_gdf : geopandas.GeoDataFrame
        Camada contendo todos os municípios.

    municipality_name : str
        Nome do município a selecionar.

    target_crs : str
        CRS de destino.
        Por padrão, EPSG:4326 para compatibilidade
        com os rasters CHELSA.

    Returns
    -------
    geopandas.GeoDataFrame
        GeoDataFrame contendo exatamente um município,
        reprojetado para o CRS solicitado.
    """

    selected = municipalities_gdf[
        municipalities_gdf["municipio"]
        .str.strip()
        .str.casefold()
        == municipality_name.strip().casefold()
    ].copy()

    if len(selected) == 0:
        raise ValueError(
            f"Município não encontrado: {municipality_name}"
        )

    if len(selected) > 1:
        raise ValueError(
            f"Mais de um município encontrado para: "
            f"{municipality_name}"
        )

    if selected.crs is None:
        raise ValueError(
            "A camada de municípios não possui CRS definido."
        )

    selected = selected.to_crs(target_crs)

    return selected

def get_municipality_names_by_nuts3(
    municipalities_gdf: gpd.GeoDataFrame,
    nuts3_name: str,
) -> list[str]:
    """
    Obtém os nomes dos municípios pertencentes
    a uma determinada região NUTS III.

    Parameters
    ----------
    municipalities_gdf : geopandas.GeoDataFrame
        Camada contendo os municípios.

    nuts3_name : str
        Nome da região NUTS III.

    Returns
    -------
    list[str]
        Lista ordenada dos municípios encontrados.
    """

    selected = municipalities_gdf[
        municipalities_gdf["nuts3"]
        .str.strip()
        .str.casefold()
        == nuts3_name.strip().casefold()
    ].copy()

    if selected.empty:
        raise ValueError(
            f"NUTS III não encontrada: {nuts3_name}"
        )

    municipality_names = (
        selected["municipio"]
        .dropna()
        .drop_duplicates()
        .sort_values()
        .tolist()
    )

    return municipality_names

def get_municipalities_by_nuts3(
    municipalities_gdf: gpd.GeoDataFrame,
    nuts3_name: str,
    target_crs: str = "EPSG:4326",
) -> gpd.GeoDataFrame:
    """
    Seleciona todos os municípios pertencentes
    a uma determinada região NUTS III.

    Parameters
    ----------
    municipalities_gdf : geopandas.GeoDataFrame
        Camada contendo os municípios.

    nuts3_name : str
        Nome da região NUTS III.

    target_crs : str
        CRS de destino.

    Returns
    -------
    geopandas.GeoDataFrame
        Municípios da NUTS III selecionada,
        reprojetados para o CRS solicitado.
    """

    selected = municipalities_gdf[
        municipalities_gdf["nuts3"]
        .str.strip()
        .str.casefold()
        == nuts3_name.strip().casefold()
    ].copy()

    if selected.empty:
        raise ValueError(
            f"NUTS III não encontrada: {nuts3_name}"
        )

    if selected.crs is None:
        raise ValueError(
            "A camada de municípios não possui CRS definido."
        )

    selected = selected.to_crs(target_crs)

    selected = (
        selected
        .sort_values("municipio")
        .reset_index(drop=True)
    )

    return selected

def get_nuts3_bounds(
    municipalities_gdf: gpd.GeoDataFrame,
    nuts3_name: str,
    target_crs: str = "EPSG:4326",
) -> dict[str, float]:
    """
    Obtém os limites espaciais de uma região NUTS III.

    Parameters
    ----------
    municipalities_gdf : geopandas.GeoDataFrame
        Camada contendo os municípios.

    nuts3_name : str
        Nome da região NUTS III.

    target_crs : str
        CRS de destino.
        Por padrão, EPSG:4326 para compatibilidade
        com os dados climáticos CHELSA.

    Returns
    -------
    dict[str, float]
        Limites espaciais nomeados da região:
        xmin, xmax, ymin e ymax.
    """

    region = get_municipalities_by_nuts3(
        municipalities_gdf=municipalities_gdf,
        nuts3_name=nuts3_name,
        target_crs=target_crs,
    )

    xmin, ymin, xmax, ymax = region.total_bounds

    return {
        "xmin": float(xmin),
        "xmax": float(xmax),
        "ymin": float(ymin),
        "ymax": float(ymax),
    }

def get_municipalities_by_names(
    municipalities_gdf: gpd.GeoDataFrame,
    municipality_names: list[str],
    target_crs: str = "EPSG:4326",
) -> gpd.GeoDataFrame:
    """
    Seleciona múltiplos municípios pelos seus nomes
    e reprojeta as geometrias para o CRS desejado.

    Parameters
    ----------
    municipalities_gdf : geopandas.GeoDataFrame
        Camada contendo todos os municípios.

    municipality_names : list[str]
        Lista de municípios a selecionar.

    target_crs : str
        CRS de destino.

    Returns
    -------
    geopandas.GeoDataFrame
        GeoDataFrame contendo os municípios selecionados.
    """

    if not municipality_names:
        raise ValueError(
            "A lista de municípios não pode estar vazia."
        )

    normalized_names = {
        name.strip().casefold()
        for name in municipality_names
    }

    selected = municipalities_gdf[
        municipalities_gdf["municipio"]
        .str.strip()
        .str.casefold()
        .isin(normalized_names)
    ].copy()

    found_names = {
        name.strip().casefold()
        for name in selected["municipio"]
    }

    missing_names = (
        normalized_names
        - found_names
    )

    if missing_names:
        raise ValueError(
            "Municípios não encontrados: "
            f"{sorted(missing_names)}"
        )

    if selected.crs is None:
        raise ValueError(
            "A camada de municípios não possui CRS definido."
        )

    selected = selected.to_crs(
        target_crs
    )

    selected = (
        selected
        .sort_values("municipio")
        .reset_index(drop=True)
    )

    return selected
