"""
Validate the Phase 2 future-climate acquisition scaffold against the
real CHELSA server.

This must be run locally, with normal internet access — the cloud
session that built this scaffold could not reach
os.zhdk.cloud.switch.ch (see docs/03, section 3; docs/04, Phase 2), so
build_chelsa_future_climatology_url's exact URL pattern and
load_chelsa_future_monthly_subset's data-format assumptions have not
been confirmed against a real file.

Usage
-----
    python -m scripts.validate_future_acquisition
    python -m scripts.validate_future_acquisition --variable tas --gcm MRI-ESM2-0 --scenario ssp370 --period 2041-2070

This does one small, fast download (Vila Real's bounding box, one
month) rather than a full region/period, since the goal here is to
confirm the URL/format assumptions, not to acquire real data yet.
"""

import argparse
import sys

from src.climate_acquisition import (
    BoundingBox,
    ClimateAcquisitionError,
    build_chelsa_future_climatology_url,
    load_chelsa_future_monthly_subset,
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
    print("Send me this whole output. What to look for, if the variable is tas/tasmin/tasmax:")
    print("  - Values roughly 250-300  => looks like Kelvin already, scale factor")
    print("    handling in the loader is probably fine as-is.")
    print("  - Values roughly 2500-3000 => the scale factor (0.1) was NOT")
    print("    auto-applied by rioxarray; the loader needs to multiply by")
    print("    CHELSA_SCALE_FACTOR, same as the historical loader does.")
    print("  - Anything else (e.g. near 0, negative, huge) => the data")
    print("    variable name/band being picked is probably wrong.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
