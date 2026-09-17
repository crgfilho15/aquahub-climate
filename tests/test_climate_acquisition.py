import numpy as np
import pytest
import xarray as xr

import src.climate_acquisition as climate_acquisition
from src.climate_acquisition import (
    BoundingBox,
    ClimateAcquisitionError,
    build_chelsa_climatology_url,
    build_chelsa_future_climatology_url,
    load_chelsa_future_monthly_subset,
    load_chelsa_monthly_subset,
)


def test_build_chelsa_climatology_url():
    url = build_chelsa_climatology_url(
        variable="tas",
        month=1,
    )

    assert url == (
        "https://os.unil.cloud.switch.ch/"
        "chelsa02/chelsa/global/climatologies/"
        "tas/1981-2010/"
        "CHELSA_tas_01_1981-2010_V.2.1.tif"
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
    """
    The synthetic dataset here mirrors the real shape confirmed
    locally (Sept 2026) for xr.open_dataset(..., engine="rasterio"):
    dims (band, y, x), y descending, values already decoded to
    physical units (GDAL auto-applies the GeoTIFF's embedded scale/
    offset) — see _open_and_subset_chelsa_geotiff's docstring. This
    replaced an earlier, unrealistic mock (dims lat/lon directly,
    raw *10 integer-like values) written before that was confirmed.
    """

    y = np.array([42.0, 41.5, 41.0])
    x = np.array([-8.0, -7.5, -7.0])

    values = np.array(
        [
            [
                [278.0, 279.0, 280.0],
                [279.0, 279.4, 281.0],
                [280.0, 281.0, 282.0],
            ]
        ],
        dtype=np.float32,
    )

    synthetic_dataset = xr.Dataset(
        {
            "band_data": (
                ("band", "y", "x"),
                values,
            ),
        },
        coords={
            "band": [1],
            "y": y,
            "x": x,
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

    assert result["band_data"].shape == (1, 1)

    assert float(result["band_data"].values[0, 0]) == pytest.approx(
        279.4
    )

    assert result["band_data"].attrs["units"] == "K"

    assert (
        result["band_data"].attrs["source"]
        == "CHELSA climatologies v2.1"
    )

    assert (
        result["band_data"].attrs["period"]
        == "1981-2010"
    )

    assert result["band_data"].attrs["scale_factor_source"].startswith(
        "auto-decoded"
    )


def test_build_chelsa_future_climatology_url():
    url = build_chelsa_future_climatology_url(
        variable="tas",
        month=4,
        gcm="MRI-ESM2-0",
        scenario="ssp370",
        period="2041-2070",
    )

    assert url == (
        "https://os.unil.cloud.switch.ch/"
        "chelsa02/chelsa/global/climatologies/"
        "tas/2041-2070/MRI-ESM2-0/ssp370/"
        "CHELSA_mri-esm2-0_r1i1p1f1_w5e5_ssp370_tas_04_2041-2070_V.2.1.tif"
    )


def test_future_url_rejects_unsupported_gcm():
    with pytest.raises(
        ClimateAcquisitionError,
        match="not one of the CHELSA v2.1 standard GCMs",
    ):
        build_chelsa_future_climatology_url(
            variable="tas",
            month=1,
            gcm="Not-A-Real-GCM",
            scenario="ssp370",
            period="2041-2070",
        )


def test_future_url_rejects_invalid_variable():
    with pytest.raises(ClimateAcquisitionError, match="is not supported"):
        build_chelsa_future_climatology_url(
            variable="invalid_var",
            month=1,
            gcm="MRI-ESM2-0",
            scenario="ssp370",
            period="2041-2070",
        )


def test_future_url_rejects_empty_scenario_or_period():
    with pytest.raises(ClimateAcquisitionError, match="Scenario cannot be empty"):
        build_chelsa_future_climatology_url(
            variable="tas",
            month=1,
            gcm="MRI-ESM2-0",
            scenario="",
            period="2041-2070",
        )

    with pytest.raises(ClimateAcquisitionError, match="Period cannot be empty"):
        build_chelsa_future_climatology_url(
            variable="tas",
            month=1,
            gcm="MRI-ESM2-0",
            scenario="ssp370",
            period="",
        )


def test_load_chelsa_future_monthly_subset_without_network(monkeypatch):
    """
    Verifies the loader wires bbox validation, URL construction and
    metadata tagging correctly, without depending on network access or
    on the still-unverified remote file format/path (see the caveat on
    build_chelsa_future_climatology_url).
    """

    lat = np.array([41.0, 41.5, 42.0])
    lon = np.array([-8.0, -7.5, -7.0])

    values = np.array(
        [
            [280.0, 281.0, 282.0],
            [281.0, 281.5, 283.0],
            [282.0, 283.0, 284.0],
        ],
        dtype=np.float32,
    )

    synthetic_dataset = xr.Dataset(
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

    class FakeRemoteFile:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    captured_open_kwargs = {}

    def fake_fsspec_open(*args, **kwargs):
        captured_open_kwargs["url"] = args[0] if args else kwargs.get("urlpath")
        return FakeRemoteFile()

    monkeypatch.setattr(
        climate_acquisition.fsspec,
        "open",
        fake_fsspec_open,
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

    result = load_chelsa_future_monthly_subset(
        variable="tas",
        month=4,
        gcm="MRI-ESM2-0",
        scenario="ssp370",
        period="2041-2070",
        bbox=bbox,
    )

    assert result["band_data"].shape == (1, 1)

    assert (
        captured_open_kwargs["url"]
        == build_chelsa_future_climatology_url(
            variable="tas",
            month=4,
            gcm="MRI-ESM2-0",
            scenario="ssp370",
            period="2041-2070",
        )
    )

    assert result["band_data"].attrs["gcm"] == "MRI-ESM2-0"
    assert result["band_data"].attrs["scenario"] == "ssp370"
    assert result["band_data"].attrs["period"] == "2041-2070"
    assert (
        result["band_data"].attrs["source"]
        == "CHELSA climatologies v2.1 (future)"
    )


def test_load_chelsa_future_monthly_subset_rejects_invalid_bbox():
    bbox = BoundingBox(-181, -7, 41, 42)

    with pytest.raises(ClimateAcquisitionError):
        load_chelsa_future_monthly_subset(
            variable="tas",
            month=1,
            gcm="MRI-ESM2-0",
            scenario="ssp370",
            period="2041-2070",
            bbox=bbox,
        )
