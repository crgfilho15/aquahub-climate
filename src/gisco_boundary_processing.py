import geopandas as gpd


def list_available_nuts_regions(
    gisco_gdf: gpd.GeoDataFrame,
    country_code: str | None = None,
    levl_code: int | None = None,
) -> list[tuple[str, str]]:
    """
    Lista as regiões NUTS disponíveis numa camada GISCO/Eurostat,
    como pares (NUTS_ID, NUTS_NAME).

    Análogo ao print(sorted(gdf["nuts3"].unique())) usado para a
    CAOP2025 (ver docs/03, Secção 7), mas para o ficheiro GISCO —
    útil para descobrir localmente os NUTS_ID exatos de Castilla y
    León e Extremadura antes de os usar em
    get_regions_by_nuts_id.

    Parameters
    ----------
    gisco_gdf : geopandas.GeoDataFrame
        Camada GISCO/Eurostat de fronteiras NUTS, com colunas
        "NUTS_ID", "NUTS_NAME" (e, opcionalmente, "CNTR_CODE" e
        "LEVL_CODE").

    country_code : str | None
        Se indicado, filtra por "CNTR_CODE" (ex. "ES" para Espanha).

    levl_code : int | None
        Se indicado, filtra por "LEVL_CODE" (ex. 2 para NUTS II).

    Returns
    -------
    list[tuple[str, str]]
        Pares (NUTS_ID, NUTS_NAME) ordenados por NUTS_ID.
    """

    selected = gisco_gdf

    if country_code is not None:
        selected = selected[
            selected["CNTR_CODE"] == country_code
        ]

    if levl_code is not None:
        selected = selected[
            selected["LEVL_CODE"] == levl_code
        ]

    pairs = (
        selected[["NUTS_ID", "NUTS_NAME"]]
        .drop_duplicates()
        .sort_values("NUTS_ID")
    )

    return list(
        pairs.itertuples(index=False, name=None)
    )


def get_regions_by_nuts_id(
    gisco_gdf: gpd.GeoDataFrame,
    nuts_ids: list[str],
    target_crs: str = "EPSG:4326",
) -> gpd.GeoDataFrame:
    """
    Seleciona uma ou mais regiões GISCO/Eurostat pelo seu NUTS_ID
    oficial e reprojeta para o CRS desejado.

    Usa NUTS_ID (código estável, ex. "ES41") em vez do nome, porque
    o nome ("NUTS_NAME") pode variar consoante a língua/transliteração
    do ficheiro GISCO descarregado - o código é a chave fiável.

    Parameters
    ----------
    gisco_gdf : geopandas.GeoDataFrame
        Camada GISCO/Eurostat de fronteiras NUTS.

    nuts_ids : list[str]
        Códigos NUTS_ID a selecionar (ex. ["ES41", "ES43"] para
        Castilla y León + Extremadura).

    target_crs : str
        CRS de destino. Por padrão, EPSG:4326 para compatibilidade
        com os rasters CHELSA e com o resto do pipeline (ver
        src/boundary_processing.py).

    Returns
    -------
    geopandas.GeoDataFrame
        Regiões selecionadas, sem duplicados, reprojetadas e
        ordenadas por NUTS_ID.
    """

    if not nuts_ids:
        raise ValueError(
            "A lista de NUTS_ID não pode estar vazia."
        )

    normalized_ids = {
        nuts_id.strip().upper()
        for nuts_id in nuts_ids
    }

    selected = gisco_gdf[
        gisco_gdf["NUTS_ID"]
        .str.strip()
        .str.upper()
        .isin(normalized_ids)
    ].copy()

    found_ids = {
        nuts_id.strip().upper()
        for nuts_id in selected["NUTS_ID"]
    }

    missing_ids = normalized_ids - found_ids

    if missing_ids:
        raise ValueError(
            "NUTS_ID não encontrados: "
            f"{sorted(missing_ids)}"
        )

    if selected.crs is None:
        raise ValueError(
            "A camada GISCO não possui CRS definido."
        )

    selected = selected.to_crs(target_crs)

    selected = (
        selected
        .drop_duplicates(subset="NUTS_ID")
        .sort_values("NUTS_ID")
        .reset_index(drop=True)
    )

    return selected


def get_region_bounds(
    gisco_gdf: gpd.GeoDataFrame,
    nuts_ids: list[str],
    target_crs: str = "EPSG:4326",
) -> dict[str, float]:
    """
    Obtém os limites espaciais combinados de uma ou mais regiões
    GISCO/Eurostat.

    Parameters
    ----------
    gisco_gdf : geopandas.GeoDataFrame
        Camada GISCO/Eurostat de fronteiras NUTS.

    nuts_ids : list[str]
        Códigos NUTS_ID a combinar.

    target_crs : str
        CRS de destino.

    Returns
    -------
    dict[str, float]
        Limites espaciais nomeados da(s) região(ões):
        xmin, xmax, ymin e ymax.
    """

    region = get_regions_by_nuts_id(
        gisco_gdf=gisco_gdf,
        nuts_ids=nuts_ids,
        target_crs=target_crs,
    )

    xmin, ymin, xmax, ymax = region.total_bounds

    return {
        "xmin": float(xmin),
        "xmax": float(xmax),
        "ymin": float(ymin),
        "ymax": float(ymax),
    }
