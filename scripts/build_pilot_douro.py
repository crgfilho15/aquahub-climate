"""
Build the Douro pilot dataset for the AquaHub interactive platform.

This script must be run locally, where the raw CHELSA rasters and the
CAOP administrative boundaries are available (data/raw/). It cannot be
run inside a network-restricted environment that has no access to
data/raw.

Usage
-----
    python -m scripts.build_pilot_douro

Output
------
    data/processed/pilot/douro_pilot.geojson
    data/processed/pilot/douro_pilot_meta.json
"""

import sys
from pathlib import Path

import geopandas as gpd

from src.boundary_processing import get_municipalities_by_nuts3
from src.climate_config import load_climate_config
from src.climate_pipeline import process_nuts3_temperature
from src.pilot_export import (
    build_pilot_feature_collection,
    build_pilot_metadata,
    save_pilot_artifacts,
)

CAOP_PATH = Path("data/raw/boundaries/Continente_CAOP2025.gpkg")
CAOP_LAYER = "cont_municipios"
CHELSA_DIR = Path("data/raw/chelsa")
OUTPUT_DIR = Path("data/processed/pilot")


def main() -> None:
    config = load_climate_config()
    pilot = config["pilot_platform"]

    region_type = pilot["region_type"]
    region_name = pilot["region_name"]
    variable = pilot["variable"]
    period = pilot["period"]
    dataset = pilot["dataset"]

    if region_type.strip().upper() != "NUTS3":
        raise SystemExit(
            f"Unsupported pilot region_type: {region_type}. "
            "Only NUTS3 is currently supported by this script."
        )

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

    print(f"Loading CAOP boundaries from {CAOP_PATH} ...")
    municipalities_gdf = gpd.read_file(CAOP_PATH, layer=CAOP_LAYER)

    print(f"Processing {variable} climatology for NUTS III '{region_name}' ...")
    monthly_df, annual_df = process_nuts3_temperature(
        municipalities_gdf=municipalities_gdf,
        nuts3_name=region_name,
        chelsa_dir=CHELSA_DIR,
        period=period,
    )

    region_gdf = get_municipalities_by_nuts3(
        municipalities_gdf=municipalities_gdf,
        nuts3_name=region_name,
        target_crs="EPSG:4326",
    )

    feature_collection = build_pilot_feature_collection(
        municipalities_gdf=region_gdf,
        monthly_df=monthly_df,
        annual_df=annual_df,
    )

    metadata = build_pilot_metadata(
        region_type=region_type,
        region_name=region_name,
        variable=variable,
        period=period,
        dataset=dataset,
        methodology_status=config["project"]["methodology_status"],
    )

    geojson_path, metadata_path = save_pilot_artifacts(
        feature_collection=feature_collection,
        metadata=metadata,
        output_dir=OUTPUT_DIR,
        region_slug=region_name.strip().lower(),
    )

    print(f"Wrote {len(feature_collection['features'])} municipalities to:")
    print(f"  {geojson_path}")
    print(f"  {metadata_path}")
    print(
        "\nNext step: run the API and open the pilot platform, e.g.\n"
        "  uvicorn api.main:app --reload\n"
        "  http://127.0.0.1:8000"
    )


if __name__ == "__main__":
    sys.exit(main())
