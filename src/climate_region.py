"""Resolve climate selections into geographic bounding boxes."""

import geopandas as gpd

from src.boundary_processing import get_nuts3_bounds
from src.climate_acquisition import BoundingBox
from src.climate_selection import FutureClimateSelection


class ClimateRegionError(ValueError):
    """Raised when a climate region cannot be resolved."""


def resolve_selection_bounding_box(
    selection: FutureClimateSelection,
    municipalities_gdf: gpd.GeoDataFrame,
) -> BoundingBox:
    """
    Resolve the geographic extent of a climate selection.

    Parameters
    ----------
    selection : FutureClimateSelection
        Climate experiment selection containing
        region type and region name.

    municipalities_gdf : geopandas.GeoDataFrame
        Administrative municipality layer used
        to resolve the selected region.

    Returns
    -------
    BoundingBox
        Geographic bounding box in EPSG:4326.
    """

    region_type = selection.region_type.strip().casefold()

    if region_type != "nuts3":
        raise ClimateRegionError(
            f"Unsupported region type: "
            f"{selection.region_type}"
        )

    bounds = get_nuts3_bounds(
        municipalities_gdf=municipalities_gdf,
        nuts3_name=selection.region_name,
        target_crs="EPSG:4326",
    )

    bbox = BoundingBox(**bounds)

    bbox.validate()

    return bbox
