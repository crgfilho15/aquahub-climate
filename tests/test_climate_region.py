import geopandas as gpd
import pytest

from shapely.geometry import box

from src.climate_region import (
    ClimateRegionError,
    resolve_selection_bounding_box,
)
from src.climate_selection import FutureClimateSelection


def test_resolve_nuts3_selection_bounding_box():
    municipalities = gpd.GeoDataFrame(
        {
            "municipio": [
                "Municipality A",
                "Municipality B",
                "Municipality C",
            ],
            "nuts3": [
                "Douro",
                "Douro",
                "Other Region",
            ],
        },
        geometry=[
            box(-7.9, 41.0, -7.4, 41.3),
            box(-7.5, 40.8, -6.7, 41.5),
            box(-9.0, 39.0, -8.0, 40.0),
        ],
        crs="EPSG:4326",
    )

    selection = FutureClimateSelection(
        gcm="MRI-ESM2-0",
        scenario="ssp370",
        period="2041-2070",
        variable="tas",
        region_type="NUTS3",
        region_name="Douro",
    )

    bbox = resolve_selection_bounding_box(
        selection=selection,
        municipalities_gdf=municipalities,
    )

    assert bbox.xmin == -7.9
    assert bbox.xmax == -6.7
    assert bbox.ymin == 40.8
    assert bbox.ymax == 41.5


def test_resolve_selection_rejects_unsupported_region_type():
    municipalities = gpd.GeoDataFrame(
        {
            "municipio": ["Municipality A"],
            "nuts3": ["Douro"],
        },
        geometry=[
            box(-7.9, 41.0, -7.4, 41.3),
        ],
        crs="EPSG:4326",
    )

    selection = FutureClimateSelection(
        gcm="MRI-ESM2-0",
        scenario="ssp370",
        period="2041-2070",
        variable="tas",
        region_type="municipality",
        region_name="Vila Real",
    )

    with pytest.raises(
        ClimateRegionError,
        match="Unsupported region type",
    ):
        resolve_selection_bounding_box(
            selection=selection,
            municipalities_gdf=municipalities,
        )
