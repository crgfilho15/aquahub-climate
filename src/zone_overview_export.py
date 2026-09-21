"""Export utilities for the AquaHub all-zones overview map.

The professor's confirmed platform design (Sept 2026) shows all 5
intervention zones on a single map at once, clickable to open a
distribution panel - a different shape from the per-region
choropleth built by src/pilot_export.py. These functions turn an
already-built region's per-municipality pilot GeoJSON
(src/pilot_export.build_pilot_feature_collection's output) into one
dissolved zone-level feature, and build placeholder features for
zones that are configured but not yet built (e.g. Castilla y León and
Extremadura, pending the whole-region zonal-stats aggregation step -
see docs/03). They do not perform any climate processing or boundary
loading themselves.
"""

import json

import geopandas as gpd


class ZoneOverviewExportError(ValueError):
    """Raised when zone overview export inputs are inconsistent."""


def build_zone_feature_from_pilot(
    slug: str,
    label: str,
    pilot_feature_collection: dict,
) -> dict:
    """
    Dissolve a built region's per-municipality pilot GeoJSON into one
    zone-level GeoJSON Feature.

    Parameters
    ----------
    slug : str
        The region's slug (config/climate.toml's
        [[pilot_platform.regions]] "slug").

    label : str
        The region's display label.

    pilot_feature_collection : dict
        The GeoJSON FeatureCollection produced by
        src/pilot_export.build_pilot_feature_collection - one feature
        per municipality, each with an "annual_mean_celsius" property.

    Returns
    -------
    dict
        A GeoJSON Feature for the whole zone, with the municipality
        geometries dissolved into one outline and properties:
        "slug", "label", "built" (True), "annual_mean_celsius" (the
        simple mean across municipalities - not area-weighted) and
        "municipality_values" (the per-municipality annual means, used
        to draw a distribution chart for the zone).
    """

    features = pilot_feature_collection.get("features") or []

    if not features:
        raise ZoneOverviewExportError(
            f"Pilot feature collection for '{slug}' has no features."
        )

    municipalities_gdf = gpd.GeoDataFrame.from_features(
        features, crs="EPSG:4326"
    )

    dissolved_geometry = municipalities_gdf.geometry.union_all()

    municipality_values = [
        {
            "municipio": feature["properties"]["municipio"],
            "annual_mean_celsius": feature["properties"][
                "annual_mean_celsius"
            ],
        }
        for feature in features
    ]

    annual_mean_celsius = sum(
        value["annual_mean_celsius"] for value in municipality_values
    ) / len(municipality_values)

    geometry = json.loads(
        gpd.GeoSeries(
            [dissolved_geometry], crs="EPSG:4326"
        ).to_json()
    )["features"][0]["geometry"]

    return {
        "type": "Feature",
        "properties": {
            "slug": slug,
            "label": label,
            "built": True,
            "annual_mean_celsius": round(annual_mean_celsius, 3),
            "municipality_values": municipality_values,
        },
        "geometry": geometry,
    }


def build_zone_placeholder_feature(
    slug: str,
    label: str,
    geometry: dict | None = None,
) -> dict:
    """
    Build a GeoJSON Feature for a zone that is configured but not yet
    built (no climate data available) - e.g. Castilla y León and
    Extremadura today, or a Portuguese zone whose CAOP/CHELSA build
    hasn't been run locally yet.

    Parameters
    ----------
    slug : str
        The region's slug.

    label : str
        The region's display label.

    geometry : dict | None
        The zone's outline geometry, if known (e.g. loaded from GISCO
        for a Spanish zone), as a GeoJSON geometry dict. None if not
        yet available - the frontend must then skip drawing this zone
        rather than treat a missing outline as an empty one.

    Returns
    -------
    dict
        A GeoJSON Feature with "built": False and no climate
        properties.
    """

    return {
        "type": "Feature",
        "properties": {
            "slug": slug,
            "label": label,
            "built": False,
        },
        "geometry": geometry,
    }


def build_zones_shapefile_geodataframe(
    feature_collection: dict,
) -> gpd.GeoDataFrame:
    """
    Turn the all-zones overview FeatureCollection (GET /api/pilot/zones'
    output) into a GeoDataFrame ready to export as a shapefile - e.g.
    for the professor to clip his own worldwide bioclimatic index
    calculations to just AquaHub's intervention zones.

    Only "slug" and "label" are kept as attributes: a shapefile's .dbf
    format cannot store the nested "municipality_values" list
    zone_overview_export produces for built zones, and the professor
    only needs the zone boundaries and names, not our internal
    "built"/temperature bookkeeping.

    Parameters
    ----------
    feature_collection : dict
        A GeoJSON FeatureCollection of zone features, each with
        "slug"/"label" properties and a polygon/multipolygon geometry
        (as built by build_zone_overview_feature_collection).

    Returns
    -------
    geopandas.GeoDataFrame
        One row per zone, columns "slug", "label", "geometry", in
        EPSG:4326, sorted by slug for a deterministic file.
    """

    features = feature_collection.get("features") or []

    if not features:
        raise ZoneOverviewExportError(
            "Zone overview feature collection has no features."
        )

    for feature in features:
        if feature.get("geometry") is None:
            raise ZoneOverviewExportError(
                f"Zone '{feature.get('properties', {}).get('slug')}' "
                "has no geometry."
            )

    gdf = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
    gdf = gdf[["slug", "label", "geometry"]]
    gdf = gdf.sort_values("slug").reset_index(drop=True)

    return gdf


def build_zone_overview_feature_collection(
    zone_features: list[dict],
) -> dict:
    """
    Combine zone-level features (built and/or placeholder) into the
    single FeatureCollection served by GET /api/pilot/zones.

    Placeholder features with geometry=None are dropped, since a null
    geometry cannot be rendered on the map (see
    build_zone_placeholder_feature's docstring).
    """

    if not zone_features:
        raise ZoneOverviewExportError(
            "At least one zone feature is required."
        )

    return {
        "type": "FeatureCollection",
        "features": [
            feature
            for feature in zone_features
            if feature.get("geometry") is not None
        ],
    }
