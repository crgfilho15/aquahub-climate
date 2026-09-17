import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import xarray as xr

from shapely.geometry import box

from src.future_climate_processing import (
    calculate_future_monthly_climatology_for_all_gcms,
    calculate_future_monthly_climatology_for_gcm,
    persist_future_month_raster,
)


def make_config():
    return {
        "future": {
            "dataset": "CHELSA-climatologies-v2.1-CMIP6",
            "periods": ["2041-2070"],
            "scenarios": ["ssp126", "ssp585"],
        },
        "models": {
            "gcms": ["GFDL-ESM4", "MRI-ESM2-0"],
        },
        "variables": {
            "core": ["tas", "tasmin", "tasmax", "pr"],
            "optional": [],
        },
    }


def make_municipalities():
    return gpd.GeoDataFrame(
        {
            "municipio": ["Vila Real", "Peso da Regua"],
            "nuts3": ["Douro", "Douro"],
        },
        geometry=[
            box(-7.9, 41.2, -7.6, 41.4),
            box(-7.85, 41.1, -7.6, 41.25),
        ],
        crs="EPSG:4326",
    )


def make_month_dataset(value: float) -> xr.Dataset:
    lat = np.array([41.4, 41.3, 41.2, 41.1])
    lon = np.array([-7.9, -7.8, -7.7, -7.6])

    values = np.full((4, 4), value, dtype=np.float32)

    dataset = xr.Dataset(
        {
            "band_data": (
                ("lat", "lon"),
                values,
            ),
        },
        coords={
            "lat": lat,
            "lon": lon,
        },
    )

    dataset = dataset.rio.write_crs("EPSG:4326")

    return dataset


def test_persist_future_month_raster(tmp_path):
    dataset = make_month_dataset(280.0)

    raster_path = persist_future_month_raster(
        monthly_dataset=dataset,
        raw_directory=tmp_path,
        variable="tas",
        period="2041-2070",
        month=7,
    )

    assert raster_path.exists()
    assert raster_path.name == "CHELSA_tas_07_2041-2070.tif"


def test_calculate_future_monthly_climatology_for_gcm(
    monkeypatch,
    tmp_path,
):
    monkeypatch.chdir(tmp_path)

    config = make_config()
    municipalities = make_municipalities()

    def fake_load_future_month_for_experiment(
        experiment,
        municipalities_gdf,
        month,
        chunks=None,
    ):
        # value shifts with month just so months are distinguishable
        return make_month_dataset(270.0 + month)

    monkeypatch.setattr(
        "src.future_climate_processing.load_future_month_for_experiment",
        fake_load_future_month_for_experiment,
    )

    result = calculate_future_monthly_climatology_for_gcm(
        config=config,
        municipalities_gdf=municipalities,
        gcm="MRI-ESM2-0",
        scenario="ssp585",
        period="2041-2070",
        variable="tas",
        region_type="NUTS3",
        region_name="Douro",
    )

    assert len(result) == 12 * 2

    assert set(result["gcm"]) == {"MRI-ESM2-0"}
    assert set(result["scenario"]) == {"ssp585"}
    assert set(result["period"]) == {"2041-2070"}
    assert set(result["municipality"]) == {
        "Vila Real",
        "Peso da Regua",
    }

    january = result[result["month"] == 1]

    assert january["mean_native"].iloc[0] == pytest.approx(271.0)

    assert january["mean_value"].iloc[0] == pytest.approx(
        271.0 - 273.15
    )

    def failing_loader(*args, **kwargs):
        raise AssertionError(
            "should not re-download a persisted raster"
        )

    monkeypatch.setattr(
        "src.future_climate_processing.load_future_month_for_experiment",
        failing_loader,
    )

    result_again = calculate_future_monthly_climatology_for_gcm(
        config=config,
        municipalities_gdf=municipalities,
        gcm="MRI-ESM2-0",
        scenario="ssp585",
        period="2041-2070",
        variable="tas",
        region_type="NUTS3",
        region_name="Douro",
    )

    pd.testing.assert_frame_equal(
        result.reset_index(drop=True),
        result_again.reset_index(drop=True),
    )


def test_calculate_future_monthly_climatology_for_all_gcms(
    monkeypatch,
    tmp_path,
):
    monkeypatch.chdir(tmp_path)

    config = make_config()
    municipalities = make_municipalities()

    def fake_load_future_month_for_experiment(
        experiment,
        municipalities_gdf,
        month,
        chunks=None,
    ):
        return make_month_dataset(280.0)

    monkeypatch.setattr(
        "src.future_climate_processing.load_future_month_for_experiment",
        fake_load_future_month_for_experiment,
    )

    result = calculate_future_monthly_climatology_for_all_gcms(
        config=config,
        municipalities_gdf=municipalities,
        scenario="ssp126",
        period="2041-2070",
        variable="tas",
        region_type="NUTS3",
        region_name="Douro",
    )

    assert set(result["gcm"]) == {"GFDL-ESM4", "MRI-ESM2-0"}
    assert len(result) == 2 * 12 * 2


def test_calculate_future_monthly_climatology_for_all_gcms_requires_gcms(
    monkeypatch,
    tmp_path,
):
    monkeypatch.chdir(tmp_path)

    config = make_config()
    config["models"]["gcms"] = []

    with pytest.raises(ValueError, match="No GCMs configured"):
        calculate_future_monthly_climatology_for_all_gcms(
            config=config,
            municipalities_gdf=make_municipalities(),
            scenario="ssp126",
            period="2041-2070",
            variable="tas",
            region_type="NUTS3",
            region_name="Douro",
        )
