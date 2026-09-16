"""Remote climate data acquisition utilities for AquaHub."""

from dataclasses import dataclass

import fsspec
import xarray as xr


CHELSA_CLIMATOLOGY_BASE_URL = (
    "https://os.zhdk.cloud.switch.ch/"
    "chelsav2/GLOBAL/climatologies"
)

CHELSA_BASELINE_PERIOD = "1981-2010"
CHELSA_VERSION = "2.1"

CHELSA_SUPPORTED_VARIABLES = {
    "tas",
    "tasmin",
    "tasmax",
    "pr",
}

CHELSA_SCALE_FACTOR = 0.1


class ClimateAcquisitionError(ValueError):
    """Raised when climate data acquisition parameters are invalid."""


@dataclass(frozen=True)
class BoundingBox:
    """Geographic bounding box in decimal degrees."""

    xmin: float
    xmax: float
    ymin: float
    ymax: float

    def validate(self) -> None:
        """Validate geographic coordinate limits."""

        if not -180 <= self.xmin <= 180:
            raise ClimateAcquisitionError(
                "xmin must be between -180 and 180."
            )

        if not -180 <= self.xmax <= 180:
            raise ClimateAcquisitionError(
                "xmax must be between -180 and 180."
            )

        if not -90 <= self.ymin <= 90:
            raise ClimateAcquisitionError(
                "ymin must be between -90 and 90."
            )

        if not -90 <= self.ymax <= 90:
            raise ClimateAcquisitionError(
                "ymax must be between -90 and 90."
            )

        if self.xmin >= self.xmax:
            raise ClimateAcquisitionError(
                "xmin must be smaller than xmax."
            )

        if self.ymin >= self.ymax:
            raise ClimateAcquisitionError(
                "ymin must be smaller than ymax."
            )


def build_chelsa_climatology_url(
    variable: str,
    month: int,
    period: str = CHELSA_BASELINE_PERIOD,
    version: str = CHELSA_VERSION,
) -> str:
    """Build the official CHELSA monthly climatology NetCDF URL."""

    if variable not in CHELSA_SUPPORTED_VARIABLES:
        raise ClimateAcquisitionError(
            f"CHELSA variable '{variable}' is not supported."
        )

    if not 1 <= month <= 12:
        raise ClimateAcquisitionError(
            "Month must be between 1 and 12."
        )

    filename = (
        f"CHELSA_{variable}_{month:02d}_"
        f"{period}_V.{version}.nc"
    )

    return (
        f"{CHELSA_CLIMATOLOGY_BASE_URL}/"
        f"{period}/ncdf/{filename}"
    )


def load_chelsa_monthly_subset(
    variable: str,
    month: int,
    bbox: BoundingBox,
    chunks: dict | None = None,
) -> xr.Dataset:
    """
    Load one CHELSA monthly climatology subset into memory.

    The remote file is opened lazily, spatially subsetted, and only then
    materialized. CHELSA's 0.1 scale factor is applied exactly once.
    """

    bbox.validate()

    url = build_chelsa_climatology_url(
        variable=variable,
        month=month,
    )

    if chunks is None:
        chunks = {
            "lat": 500,
            "lon": 500,
        }

    with fsspec.open(url, mode="rb") as remote_file:
        dataset = xr.open_dataset(
            remote_file,
            engine="h5netcdf",
            chunks=chunks,
        )

        subset = dataset.sel(
            lon=slice(bbox.xmin, bbox.xmax),
            lat=slice(bbox.ymin, bbox.ymax),
        )

        subset = subset.load()

    if "Band1" not in subset:
        raise ClimateAcquisitionError(
            "CHELSA dataset does not contain expected variable 'Band1'."
        )

    subset["Band1"] = (
        subset["Band1"] * CHELSA_SCALE_FACTOR
    )

    subset["Band1"].attrs.update(
        {
            "source": "CHELSA climatologies v2.1",
            "period": CHELSA_BASELINE_PERIOD,
            "variable": variable,
            "scale_factor_applied": CHELSA_SCALE_FACTOR,
        }
    )

    if variable in {"tas", "tasmin", "tasmax"}:
        subset["Band1"].attrs["units"] = "K"

    return subset
