"""Remote climate data acquisition utilities for AquaHub."""

from dataclasses import dataclass

import fsspec
import xarray as xr


CHELSA_CLIMATOLOGY_BASE_URL = (
    "https://os.unil.cloud.switch.ch/"
    "chelsa02/chelsa/global/climatologies"
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
# [models].gcms) and their lowercase filename slugs, confirmed against
# a real directory listing of the CHELSA server (browsed via
# envicloud.wsl.ch, Sept 2026) - see build_chelsa_future_climatology_url.
CHELSA_FUTURE_GCM_SLUGS = {
    "GFDL-ESM4": "gfdl-esm4",
    "IPSL-CM6A-LR": "ipsl-cm6a-lr",
    "MPI-ESM1-2-HR": "mpi-esm1-2-hr",
    "MRI-ESM2-0": "mri-esm2-0",
    "UKESM1-0-LL": "ukesm1-0-ll",
}

# CMIP6 realization/forcing variant embedded in each GCM's CHELSA
# filename (e.g. "r1i1p1f1"). Confirmed for all 5 GCMs against real
# CHELSA listings (browsed via envicloud.wsl.ch, Sept 2026), e.g.
# "CHELSA_gfdl-esm4_r1i1p1f1_w5e5_ssp126_tas_01_2071-2100_V.2.1.tif"
# and "CHELSA_ukesm1-0-ll_r1i1p1f1_w5e5_ssp126_tas_01_2071-2100_
# V.2.1.tif" - unlike the standard ISIMIP3b protocol (where UKESM1-0-
# LL normally uses "r1i1p1f2"), CHELSA uses "r1i1p1f1" for all 5 GCMs
# uniformly in this product.
CHELSA_FUTURE_GCM_VARIANTS = {
    "GFDL-ESM4": "r1i1p1f1",
    "IPSL-CM6A-LR": "r1i1p1f1",
    "MPI-ESM1-2-HR": "r1i1p1f1",
    "MRI-ESM2-0": "r1i1p1f1",
    "UKESM1-0-LL": "r1i1p1f1",
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
    """
    Build the official CHELSA monthly climatology GeoTIFF URL.

    Path/filename pattern confirmed against a real CHELSA directory
    listing (browsed via envicloud.wsl.ch, Sept 2026): the server is
    GeoTIFF (.tif), not NetCDF, and is organised as
    climatologies/{variable}/{period}/{filename} - it does not have
    the "ncdf" subfolder or ".nc" extension previously guessed here.
    This also matches the local file naming convention already used
    by src/climate_processing.py for pre-downloaded rasters.
    """

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
        f"{period}_V.{version}.tif"
    )

    return (
        f"{CHELSA_CLIMATOLOGY_BASE_URL}/"
        f"{variable}/{period}/{filename}"
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
    materialized. CHELSA's 0.1 scale factor is applied exactly once,
    unconditionally, on the assumption that GDAL/rioxarray's
    engine="rasterio" backend does not auto-decode the GeoTIFF's
    embedded scale/offset by default. This has not been confirmed
    against a real download through this exact code path (the Douro
    pilot's confirmed-good values came from src/climate_processing.py
    reading local pre-downloaded rasters through exactextract/GDAL
    directly, which is a different code path and, per its own
    comments, applies the scale/offset automatically). Run
    scripts/validate_future_acquisition.py locally to check whether
    this assumption holds for this loader too - see the interpretation
    guidance printed by that script.
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
            "CHELSA dataset does not contain any data variable."
        )

    band = data_vars[0]

    subset[band] = (
        subset[band] * CHELSA_SCALE_FACTOR
    )

    subset[band].attrs.update(
        {
            "source": "CHELSA climatologies v2.1",
            "period": CHELSA_BASELINE_PERIOD,
            "variable": variable,
            "scale_factor_applied": CHELSA_SCALE_FACTOR,
        }
    )

    if variable in {"tas", "tasmin", "tasmax"}:
        subset[band].attrs["units"] = "K"

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

    Path/filename pattern confirmed against a real CHELSA directory
    listing (browsed via envicloud.wsl.ch, Sept 2026), e.g.:
    climatologies/tas/2071-2100/GFDL-ESM4/ssp126/
    CHELSA_gfdl-esm4_r1i1p1f1_w5e5_ssp126_tas_01_2071-2100_V.2.1.tif

    Note the folder for the GCM uses its original mixed-case name
    (e.g. "GFDL-ESM4"), while the filename itself uses the lowercase
    slug plus a CMIP6 realization/forcing variant and the "w5e5" bias-
    adjustment tag (CHELSA's future climatologies are ISIMIP3b GCM
    output bias-corrected against W5E5). The variant ("r1i1p1f1" for
    all 5 GCMs, including UKESM1-0-LL) is confirmed for every GCM
    against real CHELSA listings — see CHELSA_FUTURE_GCM_VARIANTS.

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
    gcm_variant = CHELSA_FUTURE_GCM_VARIANTS[gcm]

    filename = (
        f"CHELSA_{gcm_slug}_{gcm_variant}_w5e5_{scenario}_"
        f"{variable}_{month:02d}_{period}_V.{version}.tif"
    )

    return (
        f"{CHELSA_CLIMATOLOGY_BASE_URL}/{variable}/{period}/"
        f"{gcm}/{scenario}/{filename}"
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
    Both loaders now read GeoTIFF through the same "rasterio" xarray
    backend, and both share the same open question: whether that
    backend auto-decodes the GeoTIFF's embedded scale/offset. Unlike
    the historical loader, this one does NOT multiply by
    CHELSA_SCALE_FACTOR, on the (equally unconfirmed) opposite
    assumption. Run scripts/validate_future_acquisition.py locally
    against a real file and compare the printed min/max/mean against
    its interpretation guidance to resolve this for both loaders.
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
