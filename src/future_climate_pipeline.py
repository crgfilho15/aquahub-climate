"""Orchestration utilities for AquaHub future climate experiments."""

import geopandas as gpd
import xarray as xr

from src.climate_acquisition import load_chelsa_monthly_subset
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
