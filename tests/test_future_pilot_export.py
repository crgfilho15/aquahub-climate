import json

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

from src.future_pilot_export import (
    FuturePilotExportError,
    build_future_pilot_feature_collection,
    build_future_pilot_metadata,
    save_future_pilot_artifacts,
)


def make_municipalities_gdf(crs="EPSG:4326"):
    return gpd.GeoDataFrame(
        {
            "municipio": ["Vila Real", "Alijó"],
            "nuts3": ["Douro", "Douro"],
        },
        geometry=[
            box(-7.9, 41.2, -7.6, 41.4),
            box(-7.6, 41.1, -7.4, 41.3),
        ],
        crs=crs,
    )


def make_anomaly_df():
    rows = []
    for municipality, base_ensemble, base_baseline in [
        ("Vila Real", 12.0, 9.0),
        ("Alijó", 13.0, 9.5),
    ]:
        for month in range(1, 13):
            ensemble = base_ensemble + month * 0.1
            baseline = base_baseline + month * 0.05
            rows.append(
                {
                    "municipality": municipality,
                    "month": month,
                    "variable": "tas",
                    "scenario": "ssp585",
                    "period": "2041-2070",
                    "ensemble_mean": ensemble,
                    "baseline_value": baseline,
                    "anomaly_absolute": ensemble - baseline,
                    "anomaly_percent": float("nan"),
                    "unit": "celsius",
                }
            )
    return pd.DataFrame(rows)


def test_build_future_pilot_feature_collection_structure():
    result = build_future_pilot_feature_collection(
        municipalities_gdf=make_municipalities_gdf(),
        anomaly_df=make_anomaly_df(),
        variable="tas",
        scenario="ssp585",
        period="2041-2070",
    )

    assert result["type"] == "FeatureCollection"
    assert len(result["features"]) == 2

    vila_real = next(
        f
        for f in result["features"]
        if f["properties"]["municipio"] == "Vila Real"
    )

    props = vila_real["properties"]

    assert props["variable"] == "tas"
    assert props["scenario"] == "ssp585"
    assert props["period"] == "2041-2070"
    assert len(props["monthly_ensemble_mean"]) == 12
    assert len(props["monthly_anomaly_absolute"]) == 12
    assert "monthly_anomaly_percent" not in props

    # January: ensemble=12.1, baseline=9.05 -> anomaly=3.05
    assert props["monthly_ensemble_mean"][0] == pytest.approx(12.1)
    assert props["monthly_anomaly_absolute"][0] == pytest.approx(
        3.05
    )

    # Annual value should land within the monthly range (sanity check
    # on the weighted-average helper, not an exact literal).
    assert min(props["monthly_ensemble_mean"]) <= props[
        "annual_ensemble_mean"
    ] <= max(props["monthly_ensemble_mean"])


def test_percent_anomaly_included_only_when_present():
    anomaly_df = make_anomaly_df()
    anomaly_df["variable"] = "pr"
    anomaly_df["anomaly_percent"] = -8.5

    result = build_future_pilot_feature_collection(
        municipalities_gdf=make_municipalities_gdf(),
        anomaly_df=anomaly_df,
        variable="pr",
        scenario="ssp585",
        period="2041-2070",
    )

    props = result["features"][0]["properties"]

    assert "monthly_anomaly_percent" in props
    assert len(props["monthly_anomaly_percent"]) == 12
    assert props["monthly_anomaly_percent"][0] == pytest.approx(-8.5)


def test_requires_epsg4326():
    with pytest.raises(FuturePilotExportError, match="EPSG:4326"):
        build_future_pilot_feature_collection(
            municipalities_gdf=make_municipalities_gdf(crs="EPSG:3763"),
            anomaly_df=make_anomaly_df(),
            variable="tas",
            scenario="ssp585",
            period="2041-2070",
        )


def test_empty_slice_raises_error():
    with pytest.raises(FuturePilotExportError, match="no rows"):
        build_future_pilot_feature_collection(
            municipalities_gdf=make_municipalities_gdf(),
            anomaly_df=make_anomaly_df(),
            variable="tas",
            scenario="ssp126",
            period="2041-2070",
        )


def test_missing_municipality_raises_error():
    anomaly_df = make_anomaly_df()
    anomaly_df = anomaly_df[anomaly_df["municipality"] != "Alijó"]

    with pytest.raises(
        FuturePilotExportError,
        match="Missing future climatology",
    ):
        build_future_pilot_feature_collection(
            municipalities_gdf=make_municipalities_gdf(),
            anomaly_df=anomaly_df,
            variable="tas",
            scenario="ssp585",
            period="2041-2070",
        )


def test_invalid_period_format_raises_error():
    with pytest.raises(FuturePilotExportError, match="YYYY-YYYY"):
        build_future_pilot_feature_collection(
            municipalities_gdf=make_municipalities_gdf(),
            anomaly_df=make_anomaly_df(),
            variable="tas",
            scenario="ssp585",
            period="mid-century",
        )


def test_save_future_pilot_artifacts_naming(tmp_path):
    feature_collection = build_future_pilot_feature_collection(
        municipalities_gdf=make_municipalities_gdf(),
        anomaly_df=make_anomaly_df(),
        variable="tas",
        scenario="ssp585",
        period="2041-2070",
    )

    metadata = build_future_pilot_metadata(
        region_slug="douro",
        region_name="Douro",
        variable="tas",
        scenario="ssp585",
        period="2041-2070",
        dataset="CHELSA-climatologies-v2.1-CMIP6",
        gcms=["GFDL-ESM4", "MRI-ESM2-0"],
        methodology_status="provisional",
    )

    geojson_path, metadata_path = save_future_pilot_artifacts(
        feature_collection=feature_collection,
        metadata=metadata,
        output_dir=tmp_path,
        region_slug="douro",
        variable="tas",
        scenario="ssp585",
        period="2041-2070",
    )

    assert geojson_path.name == "douro_tas_ssp585_2041-2070_future.geojson"
    assert metadata_path.name == "douro_tas_ssp585_2041-2070_future_meta.json"

    saved = json.loads(geojson_path.read_text(encoding="utf-8"))
    assert saved["type"] == "FeatureCollection"

    saved_meta = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert saved_meta["slug"] == "douro"
    assert saved_meta["gcms"] == ["GFDL-ESM4", "MRI-ESM2-0"]
