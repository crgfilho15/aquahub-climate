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


def _open_and_subset_chelsa_geotiff(
    url: str,
    bbox: BoundingBox,
    chunks: dict | None,
) -> xr.Dataset:
    """
    Open a remote CHELSA GeoTIFF, normalize it to this module's
    (lat, lon) convention, and return the bounding-box subset,
    materialized.

    Confirmed (Sept 2026) against a local synthetic raster built with
    rasterio to mirror CHELSA's real layout — a real download reported
    dims {'band': 1, 'x': 43200, 'y': 20880} (see the KeyError this
    replaced) — that xarray's engine="rasterio" backend:
      - names dims "band"/"x"/"y", not "lat"/"lon";
      - orders "y" descending (north to south);
      - auto-decodes the GeoTIFF's embedded scale/offset into physical
        units (e.g. a raw int16 2794 with scale=0.1 comes back as
        279.4), the same way exactextract/GDAL already does for the
        local rasters src/climate_processing.py reads. Callers must
        NOT re-apply CHELSA_SCALE_FACTOR to values from this helper.
    This is a property of the rasterio/GDAL backend itself (standard
    GeoTIFF scale/offset decoding), not something specific to the one
    synthetic file tested, so it is trusted to hold for the real
    CHELSA server too — CHELSA's own documented 0.1 scale factor for
    temperature variables is exactly what was embedded in the test
    file.
    """

    if chunks is None:
        chunks = {
            "x": 500,
            "y": 500,
        }

    with fsspec.open(url, mode="rb") as remote_file:
        dataset = xr.open_dataset(
            remote_file,
            engine="rasterio",
            chunks=chunks,
        )

        rename_map = {
            source: target
            for source, target in (("x", "lon"), ("y", "lat"))
            if source in dataset.dims
        }

        if rename_map:
            dataset = dataset.rename(rename_map)

        if "band" in dataset.dims:
            dataset = dataset.squeeze("band", drop=True)

        lat_descending = bool(
            dataset["lat"].values[0] > dataset["lat"].values[-1]
        )

        lat_slice = (
            slice(bbox.ymax, bbox.ymin)
            if lat_descending
            else slice(bbox.ymin, bbox.ymax)
        )

        subset = dataset.sel(
            lon=slice(bbox.xmin, bbox.xmax),
            lat=lat_slice,
        )

        subset = subset.load()

    return subset


def load_chelsa_monthly_subset(
    variable: str,
    month: int,
    bbox: BoundingBox,
    chunks: dict | None = None,
) -> xr.Dataset:
    """
    Load one CHELSA monthly climatology subset into memory.

    The remote file is opened lazily, spatially subsetted, and only
    then materialized, via _open_and_subset_chelsa_geotiff, which
    already returns physical units — CHELSA_SCALE_FACTOR is NOT
    re-applied here (see that helper's docstring for why).
    """

    bbox.validate()

    url = build_chelsa_climatology_url(
        variable=variable,
        month=month,
    )

    subset = _open_and_subset_chelsa_geotiff(url, bbox, chunks)

    data_vars = list(subset.data_vars)

    if not data_vars:
        raise ClimateAcquisitionError(
            "CHELSA dataset does not contain any data variable."
        )

    band = data_vars[0]

    subset[band].attrs.update(
        {
            "source": "CHELSA climatologies v2.1",
            "period": CHELSA_BASELINE_PERIOD,
            "variable": variable,
            "scale_factor_source": (
                "auto-decoded by rasterio/GDAL from the GeoTIFF's "
                "embedded scale/offset metadata "
                f"(CHELSA_SCALE_FACTOR={CHELSA_SCALE_FACTOR})"
            ),
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
    load_chelsa_monthly_subset, applied to the future GCM/SSP product,
    via the same _open_and_subset_chelsa_geotiff helper — see its
    docstring for why CHELSA_SCALE_FACTOR is not re-applied here
    either.
    """

    bbox.validate()

    url = build_chelsa_future_climatology_url(
        variable=variable,
        month=month,
        gcm=gcm,
        scenario=scenario,
        period=period,
    )

    subset = _open_and_subset_chelsa_geotiff(url, bbox, chunks)

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
