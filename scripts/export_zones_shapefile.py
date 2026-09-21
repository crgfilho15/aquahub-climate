"""
Export the AquaHub project's 5 intervention zones as a shapefile, for
sharing with the professor - he is calculating bioclimatic indices
worldwide and needs the project's zone boundaries to clip his own
results down to just the zones this project needs.

This must be run locally, after data/processed/pilot/zones_overview.geojson
has already been built (python -m scripts.build_zone_overview - see
docs/03, Section 4/7). It only reads that file and converts it; it
does not process any climate or boundary data itself.

Usage
-----
    python -m scripts.export_zones_shapefile
    python -m scripts.export_zones_shapefile --input data/processed/pilot/zones_overview.geojson --output data/processed/pilot/aquahub_zones

Output
------
    <output>.shp/.shx/.dbf/.prj/.cpg  (one row per zone: slug, label, geometry)
    <output>.zip                     (the same files, zipped for sharing)
"""

import argparse
import json
import sys
import zipfile
from pathlib import Path

from src.zone_overview_export import build_zones_shapefile_geodataframe

DEFAULT_INPUT = Path("data/processed/pilot/zones_overview.geojson")
DEFAULT_OUTPUT = Path("data/processed/pilot/aquahub_zones")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Path to the zones overview GeoJSON (default: {DEFAULT_INPUT}).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output path without extension (default: {DEFAULT_OUTPUT}).",
    )
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(
            f"Zone overview file not found: {args.input}\n"
            "Run 'python -m scripts.build_zone_overview' first (see "
            "docs/03, Section 7, for the --gisco-file flag needed to "
            "include the Spanish zones)."
        )

    print(f"Loading {args.input} ...")
    feature_collection = json.loads(args.input.read_text(encoding="utf-8"))

    gdf = build_zones_shapefile_geodataframe(feature_collection)

    print(f"Zones included ({len(gdf)}):")
    for _, row in gdf.iterrows():
        print(f"  {row['slug']}: {row['label']}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    shp_path = args.output.with_suffix(".shp")
    gdf.to_file(shp_path, driver="ESRI Shapefile")

    sidecar_suffixes = [".shp", ".shx", ".dbf", ".prj", ".cpg"]
    written_paths = [
        args.output.with_suffix(suffix)
        for suffix in sidecar_suffixes
        if args.output.with_suffix(suffix).exists()
    ]

    zip_path = args.output.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in written_paths:
            zf.write(path, arcname=path.name)

    print(f"\nWrote {len(written_paths)} shapefile component(s) to {args.output}.*")
    print(f"Zipped for sharing: {zip_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
