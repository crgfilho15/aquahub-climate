"""
Validate the Phase 2 future-climate acquisition scaffold against the
real CHELSA server.

This must be run locally, with normal internet access — the cloud
session that built this scaffold could not reach
os.zhdk.cloud.switch.ch or os.unil.cloud.switch.ch (see docs/03,
section 3; docs/04, Phase 2). The URL/path pattern below was corrected
in Sept 2026 from a real directory listing (browsed manually via
envicloud.wsl.ch) after the original guessed URL 404'd, so the path
itself is now trusted. What is NOT yet confirmed is whether
load_chelsa_future_monthly_subset's data-format assumptions (data
variable name, whether the GeoTIFF's scale/offset is auto-decoded by
the "rasterio" xarray backend) are correct — that is what this script
checks. It now runs the same check against the historical loader too,
since that loader was switched to the same GeoTIFF/rasterio code path
and shares the same open question (previously it was untested in a
different way: NetCDF/h5netcdf, never verified against a live file).

Usage
-----
    python -m scripts.validate_future_acquisition
    python -m scripts.validate_future_acquisition --variable tas --gcm MRI-ESM2-0 --scenario ssp370 --period 2041-2070

This does small, fast downloads (Vila Real's bounding box, one month
each for the historical and future loaders) rather than a full
region/period, since the goal here is to confirm the URL/format
assumptions, not to acquire real data yet.
"""

import argparse
import sys

from src.climate_acquisition import (
    BoundingBox,
    ClimateAcquisitionError,
    build_chelsa_climatology_url,
    build_chelsa_future_climatology_url,
    load_chelsa_future_monthly_subset,
    load_chelsa_monthly_subset,
)

# Vila Real bounding box (EPSG:4326) - small and already validated
# against real CHELSA historical data in the Douro pilot, so it is a
# good minimal test extent here too.
VILA_REAL_BBOX = BoundingBox(
    xmin=-7.92136692,
    xmax=-7.60029964,
    ymin=41.17968515,
    ymax=41.42152517,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variable", default="tas")
    parser.add_argument("--gcm", default="MRI-ESM2-0")
    parser.add_argument("--scenario", default="ssp370")
    parser.add_argument("--period", default="2041-2070")
    parser.add_argument("--month", type=int, default=7)
    args = parser.parse_args()

    print("=" * 70)
    print("Step 1/2: historical loader (same host/format, now GeoTIFF)")
    print("=" * 70)

    historical_url = build_chelsa_climatology_url(
        variable=args.variable,
        month=args.month,
    )

    print(f"URL being requested:\n  {historical_url}\n")

    try:
        historical_result = load_chelsa_monthly_subset(
            variable=args.variable,
            month=args.month,
            bbox=VILA_REAL_BBOX,
        )
    except Exception as exc:
        print(f"FAILED: {type(exc).__name__}: {exc}")
        print()
        print(
            "If this looks like a 404 / file-not-found / path error, "
            "the URL pattern in build_chelsa_climatology_url "
            "(src/climate_acquisition.py) still needs fixing. Send me "
            "the exact error."
        )
    else:
        for name, data_array in historical_result.data_vars.items():
            print(f"  '{name}': shape={data_array.shape}, dtype={data_array.dtype}")
            print(
                f"    min={float(data_array.min()):.3f} "
                f"max={float(data_array.max()):.3f} "
                f"mean={float(data_array.mean()):.3f}"
            )
            print(f"    attrs={dict(data_array.attrs)}")

    print()
    print("=" * 70)
    print("Step 2/2: future loader (GCM/SSP/period)")
    print("=" * 70)

    try:
        url = build_chelsa_future_climatology_url(
            variable=args.variable,
            month=args.month,
            gcm=args.gcm,
            scenario=args.scenario,
            period=args.period,
        )
    except ClimateAcquisitionError as exc:
        print(f"Could not even build the URL: {exc}")
        return 1

    print("URL being requested:")
    print(f"  {url}")
    print()
    print(
        "If you want, paste that URL directly into a browser first - "
        "a 404/Not Found there means the same thing as a failure below."
    )
    print()

    try:
        result = load_chelsa_future_monthly_subset(
            variable=args.variable,
            month=args.month,
            gcm=args.gcm,
            scenario=args.scenario,
            period=args.period,
            bbox=VILA_REAL_BBOX,
        )
    except Exception as exc:
        print(f"FAILED: {type(exc).__name__}: {exc}")
        print()
        print(
            "If this looks like a 404 / file-not-found / path error, "
            "the URL pattern in build_chelsa_future_climatology_url "
            "(src/climate_acquisition.py) needs fixing to match the "
            "real CHELSA directory layout for this file. Send me the "
            "exact error and, if you found it, the correct URL from "
            "browsing the CHELSA server manually."
        )
        return 1

    print("SUCCESS - the file was found and loaded.")
    print()
    print(f"Data variables: {list(result.data_vars)}")

    for name, data_array in result.data_vars.items():
        print(f"  '{name}': shape={data_array.shape}, dtype={data_array.dtype}")
        print(
            f"    min={float(data_array.min()):.3f} "
            f"max={float(data_array.max()):.3f} "
            f"mean={float(data_array.mean()):.3f}"
        )
        print(f"    attrs={dict(data_array.attrs)}")

    print()
    print("Send me this whole output (both steps). What to look for, if the")
    print("variable is tas/tasmin/tasmax:")
    print("  - Historical step values roughly 25-30 (already Celsius-ish after")
    print("    x0.1) or ~250-300 before the loader's x0.1 multiply => the")
    print("    unconditional CHELSA_SCALE_FACTOR multiply in")
    print("    load_chelsa_monthly_subset is correct as-is.")
    print("  - Historical step values roughly ~2500-3000 (i.e. x0.1 made it")
    print("    10x too small) => rasterio/rioxarray already auto-decoded the")
    print("    scale/offset, so the manual x0.1 in load_chelsa_monthly_subset")
    print("    is double-applying it and must be removed.")
    print("  - Future step values roughly 250-300 => looks like Kelvin")
    print("    already, load_chelsa_future_monthly_subset's decision not to")
    print("    multiply by CHELSA_SCALE_FACTOR is correct as-is.")
    print("  - Future step values roughly 2500-3000 => the scale factor (0.1)")
    print("    was NOT auto-applied; load_chelsa_future_monthly_subset needs")
    print("    to multiply by CHELSA_SCALE_FACTOR too.")
    print("  - Anything else (e.g. near 0, negative, huge) => the data")
    print("    variable name/band being picked is probably wrong.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
