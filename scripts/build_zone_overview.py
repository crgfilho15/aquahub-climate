"""
Build the all-zones overview GeoJSON for the AquaHub interactive
platform's map (the professor's confirmed design, Sept 2026): all 5
intervention zones shown on one map at once, clickable to open a
distribution panel.

This script must be run locally, after scripts/build_pilot_region.py
has already built whichever Portuguese zones it can (data/raw/chelsa +
data/raw/boundaries/Continente_CAOP2025.gpkg must be available for
those, exactly as build_pilot_region.py requires) - that data is used
to dissolve each zone's outline, not to display a temperature value
(see below).

**Update (Sept 2026):** every zone is written as "built": False now -
the professor is calculating the crop-specific bioclimatic indices
himself and delivering them directly, so the map no longer shows the
temperature index. What varies per zone is only whether its outline is
known: the Portuguese zones get theirs by dissolving
scripts/build_pilot_region.py's output; the 2 Spanish zones (Castilla
y León, Extremadura), which still have no climate-data pipeline (see
docs/03 Section 7), get theirs from a local GISCO NUTS boundaries file
passed via --gisco-file. A zone with neither source available is
silently omitted from the output (the frontend only draws zones with
known geometry) - all zones with a known outline render identically,
pending.

Usage
-----
    python -m scripts.build_zone_overview
    python -m scripts.build_zone_overview --gisco-file data/raw/boundaries/NUTS_RG_01M_2024_4326.gpkg

Output
------
    data/processed/pilot/zones_overview.geojson
"""

import argparse
import json
import sys
from pathlib import Path

import geopandas as gpd

from src.climate_config import load_climate_config
from src.gisco_boundary_processing import get_regions_by_nuts_id
from src.zone_overview_export import (
    build_zone_outline_from_pilot,
    build_zone_overview_feature_collection,
    build_zone_placeholder_feature,
)

PILOT_DATA_DIR = Path("data/processed/pilot")
OUTPUT_PATH = PILOT_DATA_DIR / "zones_overview.geojson"


def build_zone(
    region_config: dict,
    pilot_data_dir: Path,
    gisco_gdf: gpd.GeoDataFrame | None,
) -> dict:
    """Build one zone's overview feature: always "built": False (see
    module docstring) - its outline comes from dissolving the region's
    pilot municipalities if already built, from GISCO if a source is
    available, or is omitted if neither exists."""

    slug = region_config["slug"]
    label = region_config["label"]

    pilot_path = pilot_data_dir / f"{slug}_pilot.geojson"

    if pilot_path.exists():
        pilot_feature_collection = json.loads(
            pilot_path.read_text(encoding="utf-8")
        )
        print(f"  {label} ({slug}): dissolving outline from pilot data ...")
        return build_zone_outline_from_pilot(
            slug=slug,
            label=label,
            pilot_feature_collection=pilot_feature_collection,
        )

    gisco_nuts_ids = region_config.get("gisco_nuts_ids") or []

    if gisco_nuts_ids and gisco_gdf is not None:
        print(
            f"  {label} ({slug}): not built, loading outline from GISCO "
            f"({gisco_nuts_ids}) ..."
        )
        region_gdf = get_regions_by_nuts_id(
            gisco_gdf=gisco_gdf,
            nuts_ids=gisco_nuts_ids,
        )
        geometry = json.loads(region_gdf.to_json())["features"][0][
            "geometry"
        ]
        return build_zone_placeholder_feature(
            slug=slug, label=label, geometry=geometry
        )

    print(
        f"  {label} ({slug}): not built and no geometry source "
        "available, omitting from the overview."
    )
    return build_zone_placeholder_feature(slug=slug, label=label)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gisco-file",
        type=Path,
        default=None,
        help="Path to a locally-downloaded GISCO NUTS boundaries file, "
        "for the Spanish zones' outlines (see "
        "scripts/inspect_gisco_boundaries.py).",
    )
    parser.add_argument(
        "--gisco-layer",
        default=None,
        help="Layer name, if --gisco-file is a multi-layer GeoPackage.",
    )
    args = parser.parse_args()

    config = load_climate_config()
    regions = config["pilot_platform"]["regions"]

    gisco_gdf = None
    if args.gisco_file:
        if not args.gisco_file.exists():
            raise SystemExit(
                f"GISCO boundaries file not found: {args.gisco_file}"
            )
        print(f"Loading GISCO boundaries from {args.gisco_file} ...")
        gisco_gdf = gpd.read_file(args.gisco_file, layer=args.gisco_layer)

    print("Building zone overview ...")
    zone_features = [
        build_zone(
            region_config=region_config,
            pilot_data_dir=PILOT_DATA_DIR,
            gisco_gdf=gisco_gdf,
        )
        for region_config in regions
    ]

    feature_collection = build_zone_overview_feature_collection(
        zone_features
    )

    PILOT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(feature_collection, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(
        f"\nWrote {len(feature_collection['features'])} zones "
        f"(all pending - awaiting the professor's bioclimatic indices) "
        f"to {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    sys.exit(main())
