import json

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

from src.pilot_export import (
    PilotExportError,
    build_pilot_feature_collection,
    build_pilot_metadata,
    save_pilot_artifacts,
)


def make_municipalities_gdf(crs="EPSG:4326"):
    return gpd.GeoDataFrame(
        {
            "municipio": ["Vila Real", "Sabrosa"],
            "nuts3": ["Douro", "Douro"],
        },
        geometry=[
            box(-7.9, 41.2, -7.6, 41.4),
            box(-7.6, 41.1, -7.4, 41.3),
        ],
        crs=crs,
    )


def make_monthly_df():
    """
    'mean_value' here (not 'mean_celsius') matches what the real
    generic pipeline actually returns
    (climate_pipeline.process_nuts3_climatology /
    process_multi_nuts3_climatology, via
    climate_processing.process_climatology_for_regions). An earlier
    version of this fixture used 'mean_celsius', which happened to
    match build_pilot_feature_collection's old (wrong) expectation but
    not reality - a real run of scripts/build_pilot_region.py would
    have raised KeyError: 'mean_celsius'. Keep this matching the real
    pipeline's output, not whatever the function under test currently
    expects.
    """

    rows = []
    for municipality, base in [("Vila Real", 5.0), ("Sabrosa", 6.0)]:
        for month in range(1, 13):
            rows.append(
                {
                    "municipality": municipality,
                    "month": month,
                    "mean_value": base + month * 0.5,
                    "variable": "tas",
                    "period": "1981-2010",
                    "source": "CHELSA climatologies v2.1",
                }
            )
    return pd.DataFrame(rows)


def make_annual_df():
    return pd.DataFrame(
        [
            {
                "municipality": "Vila Real",
                "variable": "tas",
                "period": "1981-2010",
                "mean_value": 12.03,
                "source": "CHELSA climatologies v2.1",
            },
            {
                "municipality": "Sabrosa",
                "variable": "tas",
                "period": "1981-2010",
                "mean_value": 13.10,
                "source": "CHELSA climatologies v2.1",
            },
        ]
    )


def test_build_pilot_feature_collection_structure():
    result = build_pilot_feature_collection(
        municipalities_gdf=make_municipalities_gdf(),
        monthly_df=make_monthly_df(),
        annual_df=make_annual_df(),
    )

    assert result["type"] == "FeatureCollection"
    assert len(result["features"]) == 2

    names = {f["properties"]["municipio"] for f in result["features"]}
    assert names == {"Vila Real", "Sabrosa"}

    vila_real = next(
        f
        for f in result["features"]
        if f["properties"]["municipio"] == "Vila Real"
    )

    assert vila_real["properties"]["annual_mean_celsius"] == 12.03
    assert len(vila_real["properties"]["monthly_mean_celsius"]) == 12
    assert vila_real["properties"]["monthly_mean_celsius"][0] == 5.5
    assert vila_real["geometry"]["type"] == "Polygon"


def test_build_pilot_feature_collection_requires_epsg4326():
    with pytest.raises(PilotExportError, match="EPSG:4326"):
        build_pilot_feature_collection(
            municipalities_gdf=make_municipalities_gdf(crs="EPSG:3763"),
            monthly_df=make_monthly_df(),
            annual_df=make_annual_df(),
        )


def test_build_pilot_feature_collection_missing_annual_data():
    annual_df = make_annual_df()
    annual_df = annual_df[annual_df["municipality"] != "Sabrosa"]

    with pytest.raises(PilotExportError, match="Sabrosa"):
        build_pilot_feature_collection(
            municipalities_gdf=make_municipalities_gdf(),
            monthly_df=make_monthly_df(),
            annual_df=annual_df,
        )


def test_build_pilot_feature_collection_missing_month():
    monthly_df = make_monthly_df()
    monthly_df = monthly_df[
        ~(
            (monthly_df["municipality"] == "Vila Real")
            & (monthly_df["month"] == 12)
        )
    ]

    with pytest.raises(PilotExportError, match="Vila Real"):
        build_pilot_feature_collection(
            municipalities_gdf=make_municipalities_gdf(),
            monthly_df=monthly_df,
            annual_df=make_annual_df(),
        )


def test_build_pilot_metadata_fields():
    metadata = build_pilot_metadata(
        region_slug="douro",
        region_type="NUTS3",
        region_name="Douro",
        variable="tas",
        period="1981-2010",
        dataset="CHELSA climatologies v2.1",
        methodology_status="provisional",
    )

    assert metadata["slug"] == "douro"
    assert metadata["region_name"] == "Douro"
    assert metadata["future_scenarios_included"] is False
    assert "generated_at" in metadata


def test_save_pilot_artifacts_writes_files(tmp_path):
    feature_collection = build_pilot_feature_collection(
        municipalities_gdf=make_municipalities_gdf(),
        monthly_df=make_monthly_df(),
        annual_df=make_annual_df(),
    )

    metadata = build_pilot_metadata(
        region_slug="douro",
        region_type="NUTS3",
        region_name="Douro",
        variable="tas",
        period="1981-2010",
        dataset="CHELSA climatologies v2.1",
        methodology_status="provisional",
    )

    geojson_path, metadata_path = save_pilot_artifacts(
        feature_collection=feature_collection,
        metadata=metadata,
        output_dir=tmp_path,
        region_slug="douro",
    )

    assert geojson_path.exists()
    assert metadata_path.exists()

    saved_geojson = json.loads(geojson_path.read_text(encoding="utf-8"))
    assert len(saved_geojson["features"]) == 2

    saved_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert saved_metadata["region_name"] == "Douro"
