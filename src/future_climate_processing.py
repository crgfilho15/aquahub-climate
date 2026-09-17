"""Zonal-statistics processing for AquaHub future CHELSA climatologies.

Phase 3 of the roadmap (docs/04_roadmap_future_and_bioclimatic_indices.md):
loops the already-validated single-month future acquisition
(src/future_climate_pipeline.py) over every configured GCM, persists
each downloaded month as a local raster, and reuses the same generic
zonal-statistics core the historical pipeline uses
(src/climate_processing.py) instead of duplicating it. Each GCM's
result is kept separate (config/climate.toml's
processing.preserve_individual_gcm_results) - averaging across GCMs is
Phase 4 (ensemble), not this module.
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd
import rioxarray  # noqa: F401 - registers the .rio accessor used below
import xarray as xr

from src.boundary_processing import get_municipalities_by_nuts3
from src.climate_processing import calculate_monthly_value_for_regions
from src.climate_selection import FutureClimateSelection
from src.future_climate_experiment import FutureClimateExperiment
from src.future_climate_pipeline import load_future_month_for_experiment


def persist_future_month_raster(
    monthly_dataset: xr.Dataset,
    raw_directory: Path,
    variable: str,
    period: str,
    month: int,
) -> Path:
    """
    Persist one downloaded future-climatology month subset as a local
    GeoTIFF, so repeated runs (e.g. re-running a failed later GCM) can
    reuse it instead of re-downloading - config/climate.toml's
    processing.preserve_rasters.
    """

    data_vars = list(monthly_dataset.data_vars)

    if not data_vars:
        raise ValueError(
            "Future climatology dataset has no data variable to persist."
        )

    band = data_vars[0]

    data_array = monthly_dataset[band]

    # _open_and_subset_chelsa_geotiff (src/climate_acquisition.py)
    # renames the raw "x"/"y" dims to "lon"/"lat" for this module's
    # convention, but rioxarray's own spatial-dim auto-detection does
    # not recognize "lon"/"lat" reliably - without this, .rio.to_raster
    # below fails with MissingSpatialDimensionError.
    if "lon" in data_array.dims and "lat" in data_array.dims:
        data_array = data_array.rio.set_spatial_dims(
            x_dim="lon",
            y_dim="lat",
        )

    raw_directory.mkdir(parents=True, exist_ok=True)

    raster_path = (
        raw_directory
        / f"CHELSA_{variable}_{month:02d}_{period}.tif"
    )

    data_array.rio.to_raster(raster_path)

    return raster_path


def calculate_future_monthly_climatology_for_gcm(
    config: dict,
    municipalities_gdf: gpd.GeoDataFrame,
    gcm: str,
    scenario: str,
    period: str,
    variable: str,
    region_type: str,
    region_name: str,
    chunks: dict | None = None,
    force_download: bool = False,
) -> pd.DataFrame:
    """
    Compute the monthly future climatology (all 12 months) for one
    GCM/scenario/period/variable combination, for one region's
    municipalities.

    Downloads and persists each month's raster, skipping any already
    on disk unless force_download=True, then runs
    calculate_monthly_value_for_regions (the same generic zonal-
    statistics core the historical pipeline uses) on each persisted
    raster. Output mirrors
    calculate_monthly_climatology_for_regions's shape, with added
    gcm/scenario/period columns identifying this result among the
    many the full Phase 3 loop produces.
    """

    selection = FutureClimateSelection(
        gcm=gcm,
        scenario=scenario,
        period=period,
        variable=variable,
        region_type=region_type,
        region_name=region_name,
    )

    selection.validate(config)

    experiment = FutureClimateExperiment.from_selection(
        config=config,
        selection=selection,
    )

    region_municipalities = get_municipalities_by_nuts3(
        municipalities_gdf=municipalities_gdf,
        nuts3_name=region_name,
    )

    monthly_results = []

    for month in range(1, 13):

        raster_path = (
            experiment.raw_directory
            / f"CHELSA_{variable}_{month:02d}_{period}.tif"
        )

        if force_download or not raster_path.exists():

            monthly_dataset = load_future_month_for_experiment(
                experiment=experiment,
                municipalities_gdf=municipalities_gdf,
                month=month,
                chunks=chunks,
            )

            raster_path = persist_future_month_raster(
                monthly_dataset=monthly_dataset,
                raw_directory=experiment.raw_directory,
                variable=variable,
                period=period,
                month=month,
            )

        month_result = calculate_monthly_value_for_regions(
            raster_path=raster_path,
            regions_gdf=region_municipalities,
            month=month,
            variable=variable,
        )

        monthly_results.append(month_result)

    monthly_output = pd.concat(
        monthly_results,
        ignore_index=True,
    )

    monthly_output["variable"] = variable
    monthly_output["gcm"] = gcm
    monthly_output["scenario"] = scenario
    monthly_output["period"] = period
    monthly_output["source"] = (
        f"{config['future']['dataset']} (future)"
    )

    return monthly_output


def calculate_future_monthly_climatology_for_all_gcms(
    config: dict,
    municipalities_gdf: gpd.GeoDataFrame,
    scenario: str,
    period: str,
    variable: str,
    region_type: str,
    region_name: str,
    chunks: dict | None = None,
    force_download: bool = False,
) -> pd.DataFrame:
    """
    Loop calculate_future_monthly_climatology_for_gcm over every
    configured GCM (config/climate.toml's [models].gcms), preserving
    each GCM's result individually rather than averaging them -
    ensembling across GCMs is Phase 4, not this function.
    """

    gcms = config["models"].get("gcms", [])

    if not gcms:
        raise ValueError(
            "No GCMs configured in config/climate.toml's [models].gcms."
        )

    gcm_results = [
        calculate_future_monthly_climatology_for_gcm(
            config=config,
            municipalities_gdf=municipalities_gdf,
            gcm=gcm,
            scenario=scenario,
            period=period,
            variable=variable,
            region_type=region_type,
            region_name=region_name,
            chunks=chunks,
            force_download=force_download,
        )
        for gcm in gcms
    ]

    return pd.concat(
        gcm_results,
        ignore_index=True,
    )
