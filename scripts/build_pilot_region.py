"""
Build pilot datasets for the AquaHub interactive platform.

This script must be run locally, where the raw CHELSA rasters and the
CAOP administrative boundaries are available (data/raw/). It cannot be
run inside a network-restricted environment that has no access to
data/raw.

Regions are configured in config/climate.toml, section
[[pilot_platform.regions]]. Each region is defined by one or more
NUTS III names (a project intervention area such as "Beira Interior"
does not always correspond to a single official NUTS III unit).

Usage
-----
    python -m scripts.build_pilot_region                # every configured region
    python -m scripts.build_pilot_region --region douro  # one region only

Output (per built region)
--------------------------
    data/processed/pilot/{slug}_pilot.geojson
    data/processed/pilot/{slug}_pilot_meta.json
"""

import argparse
import sys
from pathlib import Path

import geopandas as gpd

from src.boundary_processing import get_municipalities_by_nuts3_list
from src.climate_config import load_climate_config
from src.climate_pipeline import process_multi_nuts3_climatology
from src.pilot_export import (
    build_pilot_feature_collection,
    build_pilot_metadata,
    save_pilot_artifacts,
)

CAOP_PATH = Path("data/raw/boundaries/Continente_CAOP2025.gpkg")
CAOP_LAYER = "cont_municipios"
CHELSA_DIR = Path("data/raw/chelsa")
OUTPUT_DIR = Path("data/processed/pilot")


def build_region(
    municipalities_gdf: gpd.GeoDataFrame,
    region_config: dict,
    variable: str,
    period: str,
    dataset: str,
    methodology_status: str,
) -> Path | None:
    """Build one region's pilot artefacts. Returns the GeoJSON path, or
    None if the region is not yet configured (empty nuts3_names)."""

    slug = region_config["slug"]
    label = region_config["label"]
    nuts3_names = region_config.get("nuts3_names") or []

    if not nuts3_names:
        print(
            f"Skipping '{label}' ({slug}): no nuts3_names configured "
            "yet in config/climate.toml [[pilot_platform.regions]]."
        )
        return None

    print(
        f"Processing {variable} climatology for '{label}' "
        f"(NUTS III: {nuts3_names}) ..."
    )

    monthly_df, annual_df = process_multi_nuts3_climatology(
        municipalities_gdf=municipalities_gdf,
        nuts3_names=nuts3_names,
        chelsa_dir=CHELSA_DIR,
        variable=variable,
        period=period,
    )

    region_gdf = get_municipalities_by_nuts3_list(
        municipalities_gdf=municipalities_gdf,
        nuts3_names=nuts3_names,
        target_crs="EPSG:4326",
    )

    feature_collection = build_pilot_feature_collection(
        municipalities_gdf=region_gdf,
        monthly_df=monthly_df,
        annual_df=annual_df,
    )

    metadata = build_pilot_metadata(
        region_slug=slug,
        region_type="NUTS3",
        region_name=label,
        variable=variable,
        period=period,
        dataset=dataset,
        methodology_status=methodology_status,
    )

    geojson_path, metadata_path = save_pilot_artifacts(
        feature_collection=feature_collection,
        metadata=metadata,
        output_dir=OUTPUT_DIR,
        region_slug=slug,
    )

    print(
        f"  wrote {len(feature_collection['features'])} municipalities "
        f"to {geojson_path}"
    )

    return geojson_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--region",
        help="Build only this region slug (default: all configured regions).",
    )
    args = parser.parse_args()

    config = load_climate_config()
    pilot = config["pilot_platform"]

    if not CAOP_PATH.exists():
        raise SystemExit(
            f"CAOP boundaries file not found: {CAOP_PATH}\n"
            "This script must be run locally, where the AquaHub "
            "raw data directory is populated."
        )

    if not CHELSA_DIR.exists():
        raise SystemExit(
            f"CHELSA raster directory not found: {CHELSA_DIR}\n"
            "This script must be run locally, where the AquaHub "
            "raw data directory is populated."
        )

    regions = pilot["regions"]

    if args.region:
        regions = [r for r in regions if r["slug"] == args.region]

        if not regions:
            configured_slugs = [r["slug"] for r in pilot["regions"]]
            raise SystemExit(
                f"Unknown region slug: '{args.region}'. "
                f"Configured slugs: {configured_slugs}"
            )

    print(f"Loading CAOP boundaries from {CAOP_PATH} ...")
    municipalities_gdf = gpd.read_file(CAOP_PATH, layer=CAOP_LAYER)

    built_paths = []

    for region_config in regions:
        path = build_region(
            municipalities_gdf=municipalities_gdf,
            region_config=region_config,
            variable=pilot["variable"],
            period=pilot["period"],
            dataset=pilot["dataset"],
            methodology_status=config["project"]["methodology_status"],
        )

        if path is not None:
            built_paths.append(path)

    if built_paths:
        print(
            "\nNext step: run the API and open the pilot platform, e.g.\n"
            "  uvicorn api.main:app --reload\n"
            "  http://127.0.0.1:8000"
        )
    else:
        print(
            "\nNo region was built. Configure nuts3_names for at least "
            "one region in config/climate.toml first."
        )


if __name__ == "__main__":
    sys.exit(main())
