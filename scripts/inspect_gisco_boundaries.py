"""
Inspect a locally-downloaded GISCO/Eurostat NUTS boundaries file to find
the exact NUTS_ID codes for Castilla y León and Extremadura.

This mirrors the CAOP nuts3-inspection snippet in
docs/03_pilot_interactive_platform.md Section 7: run it once, locally,
against the real GISCO file, read off the NUTS_ID values, then use them
with src/gisco_boundary_processing.get_regions_by_nuts_id.

This script must be run locally. It does not download anything itself -
this session's network policy cannot reach ec.europa.eu/GISCO (same
restriction already documented for CHELSA in docs/03 Section 3), so the
GISCO NUTS boundaries file (any resolution/format Eurostat publishes -
shapefile, GeoJSON or GeoPackage, EPSG:4326) must be fetched separately
and placed under data/raw/boundaries/.

Usage
-----
    python -m scripts.inspect_gisco_boundaries <path to GISCO file> [--layer LAYER]
"""

import argparse
import sys
from pathlib import Path

import geopandas as gpd

from src.gisco_boundary_processing import list_available_nuts_regions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        type=Path,
        help="Path to the locally-downloaded GISCO NUTS boundaries file.",
    )
    parser.add_argument(
        "--layer",
        default=None,
        help="Layer name, if the file is a multi-layer GeoPackage.",
    )
    parser.add_argument(
        "--country",
        default="ES",
        help="CNTR_CODE to filter by (default: ES, for Spain).",
    )
    parser.add_argument(
        "--level",
        type=int,
        default=2,
        help="LEVL_CODE to filter by (default: 2, NUTS II - the level "
        "Castilla y León and Extremadura are defined at).",
    )
    args = parser.parse_args()

    if not args.path.exists():
        raise SystemExit(
            f"GISCO boundaries file not found: {args.path}\n"
            "This script must be run locally, where the file has been "
            "downloaded to."
        )

    print(f"Loading GISCO boundaries from {args.path} ...")
    gisco_gdf = gpd.read_file(args.path, layer=args.layer)

    pairs = list_available_nuts_regions(
        gisco_gdf=gisco_gdf,
        country_code=args.country,
        levl_code=args.level,
    )

    if not pairs:
        print(
            "No regions matched "
            f"CNTR_CODE={args.country!r}, LEVL_CODE={args.level}. "
            "Run without --country/--level to see every region in the "
            "file, then re-check the column names/values."
        )
        return

    print(
        f"\nNUTS_ID / NUTS_NAME pairs "
        f"(CNTR_CODE={args.country}, LEVL_CODE={args.level}):"
    )
    for nuts_id, nuts_name in pairs:
        print(f"  {nuts_id}  {nuts_name}")

    print(
        "\nNext: fill in the NUTS_ID codes for Castilla y León and "
        "Extremadura wherever the Spain zones are configured, and use "
        "src/gisco_boundary_processing.get_regions_by_nuts_id to load them."
    )


if __name__ == "__main__":
    sys.exit(main())
