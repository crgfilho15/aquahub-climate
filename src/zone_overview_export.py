"""Export utilities for the AquaHub all-zones overview map.

The professor's confirmed platform design (Sept 2026) shows all 5
intervention zones on a single map at once, clickable to open a
distribution panel - a different shape from the per-region
choropleth built by src/pilot_export.py. These functions build the
zone-level GeoJSON Feature for each of the 5 zones.

**Update (Sept 2026): the map no longer displays the temperature
index.** The professor is calculating the crop-specific bioclimatic
indices himself and delivering them directly (see
docs/04_roadmap_future_and_bioclimatic_indices.md, Phase 7) - so
`annual_mean_celsius` was never going to be the value shown to users,
and keeping it on the map risked being mistaken for the real
(pending) index. Every zone is therefore built as a "built": False
feature now, with geometry when it is known (either dissolved from an
already-built region's per-municipality pilot GeoJSON, or loaded from
a local GISCO file for Castilla y León/Extremadura) and omitted
otherwise - all 5 zones show the same "pending" treatment on the map
until the professor's indices are ingested. The underlying temperature
pipeline (src/pilot_export.py, src/climate_pipeline.py, the future/
ensemble/anomaly modules) is untouched and still produces
`{slug}_pilot.geojson` - only this module stopped surfacing it on the
zones map.
"""

import json

import geopandas as gpd


class ZoneOverviewExportError(ValueError):
    """Raised when zone overview export inputs are inconsistent."""


def build_zone_outline_from_pilot(
    slug: str,
    label: str,
    pilot_feature_collection: dict,
) -> dict:
    """
    Dissolve a built region's per-municipality pilot GeoJSON into one
    zone-level outline, with no climate properties attached (see
    module docstring: the map shows every zone as pending until the
    professor's indices are ingested).

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
        per municipality (its "annual_mean_celsius" values are not
        used, only the geometry).

    Returns
    -------
    dict
        A "built": False GeoJSON Feature for the whole zone (same
        shape as build_zone_placeholder_feature), with the
        municipality geometries dissolved into one outline.
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

    geometry = json.loads(
        gpd.GeoSeries(
            [dissolved_geometry], crs="EPSG:4326"
        ).to_json()
    )["features"][0]["geometry"]

    return build_zone_placeholder_feature(
        slug=slug, label=label, geometry=geometry
    )


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
