import numpy as np
import pytest
import xarray as xr

import src.climate_acquisition as climate_acquisition
from src.climate_acquisition import (
    BoundingBox,
    ClimateAcquisitionError,
    build_chelsa_climatology_url,
    load_chelsa_monthly_subset,
)


def test_build_chelsa_climatology_url():
    url = build_chelsa_climatology_url(
        variable="tas",
        month=1,
    )

    assert url == (
        "https://os.zhdk.cloud.switch.ch/"
        "chelsav2/GLOBAL/climatologies/"
        "1981-2010/ncdf/"
        "CHELSA_tas_01_1981-2010_V.2.1.nc"
    )


def test_invalid_chelsa_variable_raises_error():
    with pytest.raises(
        ClimateAcquisitionError,
        match="is not supported",
    ):
        build_chelsa_climatology_url(
            variable="invalid_var",
            month=1,
        )


def test_invalid_month_raises_error():
    with pytest.raises(
        ClimateAcquisitionError,
        match="Month must be between 1 and 12",
    ):
        build_chelsa_climatology_url(
            variable="tas",
            month=13,
        )


def test_valid_bounding_box():
    bbox = BoundingBox(
        xmin=-8.0,
        xmax=-7.0,
        ymin=41.0,
        ymax=42.0,
    )

    bbox.validate()


@pytest.mark.parametrize(
    "bbox",
    [
        BoundingBox(-181, -7, 41, 42),
        BoundingBox(-8, 181, 41, 42),
        BoundingBox(-8, -7, -91, 42),
        BoundingBox(-8, -7, 41, 91),
        BoundingBox(-7, -8, 41, 42),
        BoundingBox(-8, -7, 42, 41),
    ],
)
def test_invalid_bounding_box_raises_error(bbox):
    with pytest.raises(ClimateAcquisitionError):
        bbox.validate()


def test_load_chelsa_monthly_subset_without_network(monkeypatch):
    lat = np.array([41.0, 41.5, 42.0])
    lon = np.array([-8.0, -7.5, -7.0])

    values = np.array(
        [
            [2780.0, 2790.0, 2800.0],
            [2790.0, 2794.0, 2810.0],
            [2800.0, 2810.0, 2820.0],
        ],
        dtype=np.float32,
    )

    synthetic_dataset = xr.Dataset(
        {
            "Band1": (
                ("lat", "lon"),
                values,
            ),
        },
        coords={
            "lat": lat,
            "lon": lon,
        },
    )

    class FakeRemoteFile:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    monkeypatch.setattr(
        climate_acquisition.fsspec,
        "open",
        lambda *args, **kwargs: FakeRemoteFile(),
    )

    monkeypatch.setattr(
        climate_acquisition.xr,
        "open_dataset",
        lambda *args, **kwargs: synthetic_dataset,
    )

    bbox = BoundingBox(
        xmin=-7.75,
        xmax=-7.25,
        ymin=41.25,
        ymax=41.75,
    )

    result = load_chelsa_monthly_subset(
        variable="tas",
        month=1,
        bbox=bbox,
    )

    assert result["Band1"].shape == (1, 1)

    assert float(result["Band1"].values[0, 0]) == pytest.approx(
        279.4
    )

    assert result["Band1"].attrs["units"] == "K"

    assert (
        result["Band1"].attrs["source"]
        == "CHELSA climatologies v2.1"
    )

    assert (
        result["Band1"].attrs["period"]
        == "1981-2010"
    )

    assert (
        result["Band1"].attrs["scale_factor_applied"]
        == 0.1
    )
