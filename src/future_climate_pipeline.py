"""Orchestration utilities for AquaHub future climate experiments."""

import geopandas as gpd
import xarray as xr

from src.climate_acquisition import (
    load_chelsa_future_monthly_subset,
    load_chelsa_monthly_subset,
)
from src.future_climate_experiment import FutureClimateExperiment


def load_reference_month_for_experiment(
    experiment: FutureClimateExperiment,
    municipalities_gdf: gpd.GeoDataFrame,
    month: int,
    chunks: dict | None = None,
) -> xr.Dataset:
    """
    Load one historical CHELSA reference month
    for the geographic extent of a future climate experiment.

    This function loads the 1981-2010 CHELSA climatology used
    as the reference climate. It does not load future CMIP6 data.

    Parameters
    ----------
    experiment : FutureClimateExperiment
        Future climate experiment whose region and variable
        define the reference data request.

    municipalities_gdf : geopandas.GeoDataFrame
        Administrative municipality layer used to resolve
        the experiment geographic extent.

    month : int
        Calendar month from 1 to 12.

    chunks : dict | None
        Optional xarray chunk configuration.

    Returns
    -------
    xarray.Dataset
        CHELSA 1981-2010 monthly climatology subset
        for the experiment region.
    """

    bbox = experiment.resolve_bounding_box(
        municipalities_gdf=municipalities_gdf,
    )

    return load_chelsa_monthly_subset(
        variable=experiment.selection.variable,
        month=month,
        bbox=bbox,
        chunks=chunks,
    )


def load_future_month_for_experiment(
    experiment: FutureClimateExperiment,
    municipalities_gdf: gpd.GeoDataFrame,
    month: int,
    chunks: dict | None = None,
) -> xr.Dataset:
    """
    Load one future CMIP6/GCM month for a future climate experiment.

    This loads the GCM/SSP/period product itself (as opposed to
    load_reference_month_for_experiment, which loads the historical
    1981-2010 baseline). Relies on
    src.climate_acquisition.load_chelsa_future_monthly_subset, whose
    remote path has not been verified against the live CHELSA server —
    see that function's docstring and
    docs/04_roadmap_future_and_bioclimatic_indices.md, Phase 2.

    Parameters
    ----------
    experiment : FutureClimateExperiment
        Future climate experiment whose region, variable, GCM,
        scenario and period define the request.

    municipalities_gdf : geopandas.GeoDataFrame
        Administrative municipality layer used to resolve
        the experiment geographic extent.

    month : int
        Calendar month from 1 to 12.

    chunks : dict | None
        Optional xarray chunk configuration.

    Returns
    -------
    xarray.Dataset
        Future climatology subset for the experiment region.
    """

    bbox = experiment.resolve_bounding_box(
        municipalities_gdf=municipalities_gdf,
    )

    return load_chelsa_future_monthly_subset(
        variable=experiment.selection.variable,
        month=month,
        gcm=experiment.selection.gcm,
        scenario=experiment.selection.scenario,
        period=experiment.selection.period,
        bbox=bbox,
        chunks=chunks,
    )
