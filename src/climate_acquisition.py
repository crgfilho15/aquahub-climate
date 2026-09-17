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

# CHELSA v2.1's 5 standardised future GCMs (config/climate.toml
# [models].gcms) and their lowercase filename/path slugs, per CHELSA's
# published naming convention.
CHELSA_FUTURE_GCM_SLUGS = {
    "GFDL-ESM4": "gfdl-esm4",
    "IPSL-CM6A-LR": "ipsl-cm6a-lr",
    "MPI-ESM1-2-HR": "mpi-esm1-2-hr",
    "MRI-ESM2-0": "mri-esm2-0",
    "UKESM1-0-LL": "ukesm1-0-ll",
}


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


def build_chelsa_future_climatology_url(
    variable: str,
    month: int,
    gcm: str,
    scenario: str,
    period: str,
    version: str = CHELSA_VERSION,
) -> str:
    """
    Build the CHELSA v2.1 future monthly climatology file URL.

    NOT YET VERIFIED against the live CHELSA server: this development
    session's network policy could not reach
    os.zhdk.cloud.switch.ch (see docs/03_pilot_interactive_platform.md
    section 3), so this exact path has not been confirmed to resolve.
    It follows CHELSA's documented directory convention for future
    climatologies (period / gcm / scenario / variable), on the same
    host and version as the historical loader above, which was
    confirmed against real data during the Douro pilot. Treat the
    first real download attempt as the verification step for this
    function — see docs/04_roadmap_future_and_bioclimatic_indices.md,
    Phase 2.

    Parameters
    ----------
    variable, month, version : see build_chelsa_climatology_url.

    gcm : str
        One of config/climate.toml's [models].gcms (the 5 GCMs
        standardised by CHELSA v2.1) — see CHELSA_FUTURE_GCM_SLUGS.

    scenario : str
        SSP scenario, e.g. 'ssp370'.

    period : str
        Future climatological period, e.g. '2041-2070'.
    """

    if variable not in CHELSA_SUPPORTED_VARIABLES:
        raise ClimateAcquisitionError(
            f"CHELSA variable '{variable}' is not supported."
        )

    if not 1 <= month <= 12:
        raise ClimateAcquisitionError(
            "Month must be between 1 and 12."
        )

    if gcm not in CHELSA_FUTURE_GCM_SLUGS:
        raise ClimateAcquisitionError(
            f"GCM '{gcm}' is not one of the CHELSA v2.1 standard GCMs: "
            f"{sorted(CHELSA_FUTURE_GCM_SLUGS)}."
        )

    if not scenario.strip():
        raise ClimateAcquisitionError(
            "Scenario cannot be empty."
        )

    if not period.strip():
        raise ClimateAcquisitionError(
            "Period cannot be empty."
        )

    gcm_slug = CHELSA_FUTURE_GCM_SLUGS[gcm]

    filename = (
        f"CHELSA_{variable}_{month:02d}_{period}_"
        f"{gcm_slug}_{scenario}_V.{version}.tif"
    )

    return (
        f"{CHELSA_CLIMATOLOGY_BASE_URL}/{period}/{gcm_slug}/"
        f"{scenario}/{variable}/{filename}"
    )


def load_chelsa_future_monthly_subset(
    variable: str,
    month: int,
    gcm: str,
    scenario: str,
    period: str,
    bbox: BoundingBox,
    chunks: dict | None = None,
) -> xr.Dataset:
    """
    Load one CHELSA v2.1 future monthly climatology subset into memory.

    Same remote-subset-then-materialize approach as
    load_chelsa_monthly_subset, applied to the future GCM/SSP product.
    The remote file here is GeoTIFF (not NetCDF like the historical
    loader), opened through rioxarray's xarray backend, so the data
    variable name and any scale/offset handling GDAL already applies
    may differ from the historical loader's 'Band1' convention. This
    has not been exercised against a real file - see the caveat on
    build_chelsa_future_climatology_url above.
    """

    bbox.validate()

    url = build_chelsa_future_climatology_url(
        variable=variable,
        month=month,
        gcm=gcm,
        scenario=scenario,
        period=period,
    )

    if chunks is None:
        chunks = {
            "lat": 500,
            "lon": 500,
        }

    with fsspec.open(url, mode="rb") as remote_file:
        dataset = xr.open_dataset(
            remote_file,
            engine="rasterio",
            chunks=chunks,
        )

        subset = dataset.sel(
            lon=slice(bbox.xmin, bbox.xmax),
            lat=slice(bbox.ymin, bbox.ymax),
        )

        subset = subset.load()

    data_vars = list(subset.data_vars)

    if not data_vars:
        raise ClimateAcquisitionError(
            "CHELSA future dataset does not contain any data variable."
        )

    band = data_vars[0]

    subset[band].attrs.update(
        {
            "source": "CHELSA climatologies v2.1 (future)",
            "gcm": gcm,
            "scenario": scenario,
            "period": period,
            "variable": variable,
        }
    )

    return subset
