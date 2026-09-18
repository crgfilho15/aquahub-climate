import pytest
from shapely.geometry import box, mapping

from src.zone_overview_export import (
    ZoneOverviewExportError,
    build_zone_feature_from_pilot,
    build_zone_overview_feature_collection,
    build_zone_placeholder_feature,
)


def make_pilot_feature_collection():
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "municipio": "Vila Real",
                    "annual_mean_celsius": 12.0,
                    "monthly_mean_celsius": [5.0] * 12,
                },
                "geometry": mapping(box(-7.9, 41.2, -7.6, 41.4)),
            },
            {
                "type": "Feature",
                "properties": {
                    "municipio": "Sabrosa",
                    "annual_mean_celsius": 14.0,
                    "monthly_mean_celsius": [6.0] * 12,
                },
                "geometry": mapping(box(-7.6, 41.1, -7.4, 41.3)),
            },
        ],
    }


def test_build_zone_feature_from_pilot_dissolves_and_averages():
    result = build_zone_feature_from_pilot(
        slug="douro",
        label="Douro",
        pilot_feature_collection=make_pilot_feature_collection(),
    )

    assert result["type"] == "Feature"
    assert result["properties"]["slug"] == "douro"
    assert result["properties"]["label"] == "Douro"
    assert result["properties"]["built"] is True

    assert result["properties"]["annual_mean_celsius"] == 13.0

    assert result["properties"]["municipality_values"] == [
        {"municipio": "Vila Real", "annual_mean_celsius": 12.0},
        {"municipio": "Sabrosa", "annual_mean_celsius": 14.0},
    ]

    assert result["geometry"]["type"] in {"Polygon", "MultiPolygon"}


def test_build_zone_feature_from_pilot_rejects_empty_features():
    with pytest.raises(ZoneOverviewExportError, match="no features"):
        build_zone_feature_from_pilot(
            slug="douro",
            label="Douro",
            pilot_feature_collection={"type": "FeatureCollection", "features": []},
        )


def test_build_zone_placeholder_feature_with_known_geometry():
    geometry = mapping(box(-6.5, 40.0, -4.0, 42.5))

    result = build_zone_placeholder_feature(
        slug="castilla-y-leon",
        label="Castilla y León",
        geometry=geometry,
    )

    assert result["properties"]["built"] is False
    assert "annual_mean_celsius" not in result["properties"]
    assert result["geometry"] == geometry


def test_build_zone_placeholder_feature_without_geometry():
    result = build_zone_placeholder_feature(
        slug="castilla-y-leon",
        label="Castilla y León",
    )

    assert result["properties"]["built"] is False
    assert result["geometry"] is None


def test_build_zone_overview_feature_collection_combines_features():
    built = build_zone_feature_from_pilot(
        slug="douro",
        label="Douro",
        pilot_feature_collection=make_pilot_feature_collection(),
    )
    placeholder = build_zone_placeholder_feature(
        slug="castilla-y-leon",
        label="Castilla y León",
        geometry=mapping(box(-6.5, 40.0, -4.0, 42.5)),
    )

    result = build_zone_overview_feature_collection([built, placeholder])

    assert result["type"] == "FeatureCollection"
    assert len(result["features"]) == 2
    assert {f["properties"]["slug"] for f in result["features"]} == {
        "douro",
        "castilla-y-leon",
    }


def test_build_zone_overview_feature_collection_drops_missing_geometry():
    built = build_zone_feature_from_pilot(
        slug="douro",
        label="Douro",
        pilot_feature_collection=make_pilot_feature_collection(),
    )
    no_geometry = build_zone_placeholder_feature(
        slug="extremadura",
        label="Extremadura",
    )

    result = build_zone_overview_feature_collection([built, no_geometry])

    assert len(result["features"]) == 1
    assert result["features"][0]["properties"]["slug"] == "douro"


def test_build_zone_overview_feature_collection_rejects_empty_list():
    with pytest.raises(ZoneOverviewExportError, match="At least one"):
        build_zone_overview_feature_collection([])
