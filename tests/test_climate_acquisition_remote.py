import os

import pytest

from src.climate_acquisition import (
    BoundingBox,
    load_chelsa_monthly_subset,
)


RUN_REMOTE_TESTS = (
    os.getenv("AQUAHUB_RUN_REMOTE_TESTS") == "1"
)


@pytest.mark.integration
@pytest.mark.skipif(
    not RUN_REMOTE_TESTS,
    reason="Remote CHELSA integration tests are disabled.",
)
def test_remote_chelsa_temperature_subset():
    bbox = BoundingBox(
        xmin=-7.80,
        xmax=-7.70,
        ymin=41.25,
        ymax=41.35,
    )

    dataset = load_chelsa_monthly_subset(
        variable="tas",
        month=1,
        bbox=bbox,
    )

    temperature = dataset["Band1"]

    assert temperature.size > 0

    assert temperature.attrs["units"] == "K"

    assert (
        temperature.attrs["source"]
        == "CHELSA climatologies v2.1"
    )

    assert (
        temperature.attrs["period"]
        == "1981-2010"
    )

    mean_kelvin = float(temperature.mean())

    assert 270.0 < mean_kelvin < 290.0

    assert float(temperature.lon.min()) >= bbox.xmin
    assert float(temperature.lon.max()) <= bbox.xmax
    assert float(temperature.lat.min()) >= bbox.ymin
    assert float(temperature.lat.max()) <= bbox.ymax
