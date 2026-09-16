import geopandas as gpd
import xarray as xr

from shapely.geometry import box

from src.climate_selection import FutureClimateSelection
from src.future_climate_experiment import FutureClimateExperiment
from src.future_climate_pipeline import (
    load_reference_month_for_experiment,
)


def make_config():
    return {
        "future": {
            "dataset": "CHELSA-climatologies-v2.1-CMIP6",
            "periods": [
                "2011-2040",
                "2041-2070",
                "2071-2100",
            ],
            "scenarios": [
                "ssp126",
                "ssp370",
                "ssp585",
            ],
        },
        "models": {
            "gcms": [],
        },
        "variables": {
            "core": [
                "tas",
                "tasmin",
                "tasmax",
                "pr",
            ],
            "optional": [],
        },
        "pilot": {
            "region_type": "NUTS3",
            "region_name": "Douro",
            "variable": "tas",
            "scenario": "ssp370",
            "period": "2041-2070",
            "gcm": "",
        },
    }


def test_load_reference_month_for_experiment(monkeypatch):
    config = make_config()

    selection = FutureClimateSelection.from_pilot(
        config,
        "MRI-ESM2-0",
    )

    experiment = FutureClimateExperiment.from_selection(
        config,
        selection,
    )

    municipalities = gpd.GeoDataFrame(
        {
            "municipio": [
                "Municipality A",
                "Municipality B",
            ],
            "nuts3": [
                "Douro",
                "Douro",
            ],
        },
        geometry=[
            box(-7.9, 41.0, -7.4, 41.3),
            box(-7.5, 40.8, -6.7, 41.5),
        ],
        crs="EPSG:4326",
    )

    expected = xr.Dataset(
        {
            "Band1": (
                ("lat", "lon"),
                [[279.0]],
            )
        },
        coords={
            "lat": [41.0],
            "lon": [-7.0],
        },
    )

    captured = {}

    def fake_load_chelsa_monthly_subset(
        variable,
        month,
        bbox,
        chunks=None,
    ):
        captured["variable"] = variable
        captured["month"] = month
        captured["bbox"] = bbox
        captured["chunks"] = chunks

        return expected

    monkeypatch.setattr(
        "src.future_climate_pipeline.load_chelsa_monthly_subset",
        fake_load_chelsa_monthly_subset,
    )

    result = load_reference_month_for_experiment(
        experiment=experiment,
        municipalities_gdf=municipalities,
        month=1,
        chunks={
            "lat": 250,
            "lon": 250,
        },
    )

    assert result is expected
    assert captured["variable"] == "tas"
    assert captured["month"] == 1
    assert captured["chunks"] == {
        "lat": 250,
        "lon": 250,
    }

    assert captured["bbox"].xmin == -7.9
    assert captured["bbox"].xmax == -6.7
    assert captured["bbox"].ymin == 40.8
    assert captured["bbox"].ymax == 41.5
