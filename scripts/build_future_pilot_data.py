"""
Build future/ensemble/anomaly pilot data for the interactive platform.

Phase 9 of the roadmap (docs/04_roadmap_future_and_bioclimatic_indices.md):
takes a Phase 4 ensemble CSV, computes anomalies against the historical
baseline (Phase 5), and exports one GeoJSON/metadata pair per scenario/
period found in the CSV - the same static-file architecture
scripts/build_pilot_region.py already uses for the historical baseline.

This must be run locally, where the CAOP boundaries and historical
CHELSA rasters are available (same requirement as
scripts/build_pilot_region.py and scripts/build_anomaly_climatology.py),
since it recomputes the historical baseline to compute anomalies.

Usage
-----
    python -m scripts.build_future_pilot_data data/processed/ensemble/douro_tas_future_climatology_ensemble.csv
    python -m scripts.build_future_pilot_data data/processed/ensemble/douro_tas_future_climatology_ensemble.csv --region-slug douro --nuts3 Douro --variable tas

Output (one pair per scenario/period found in the ensemble CSV)
------
    data/processed/pilot/future/{region_slug}_{variable}_{scenario}_{period}_future.geojson
    data/processed/pilot/future/{region_slug}_{variable}_{scenario}_{period}_future_meta.json
"""

import argparse
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

from src.boundary_processing import get_municipalities_by_nuts3
from src.climate_anomalies import calculate_climate_anomalies
from src.climate_config import load_climate_config
from src.climate_pipeline import process_nuts3_climatology
from src.future_pilot_export import (
    build_future_pilot_feature_collection,
    build_future_pilot_metadata,
    save_future_pilot_artifacts,
)

CAOP_PATH = Path("data/raw/boundaries/Continente_CAOP2025.gpkg")
CAOP_LAYER = "cont_municipios"
CHELSA_DIR = Path("data/raw/chelsa")
OUTPUT_DIR = Path("data/processed/pilot/future")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "ensemble_csv",
        help="Path to a Phase 4 ensemble CSV (scripts/build_ensemble_climatology.py's output).",
    )
    parser.add_argument(
        "--region-slug",
        default="douro",
        help="Pilot platform region slug, must match config/climate.toml's [[pilot_platform.regions]] (default: douro).",
    )
    parser.add_argument(
        "--nuts3",
        default="Douro",
        help="NUTS III region name used to compute the historical baseline (default: Douro).",
    )
    parser.add_argument(
        "--variable",
        default="tas",
        help="Must match the ensemble CSV's variable (default: tas).",
    )
    args = parser.parse_args()

    ensemble_path = Path(args.ensemble_csv)

    if not ensemble_path.exists():
        raise SystemExit(f"Ensemble CSV not found: {ensemble_path}")

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

    config = load_climate_config()

    print(f"Loading CAOP boundaries from {CAOP_PATH} ...")
    municipalities_gdf = gpd.read_file(CAOP_PATH, layer=CAOP_LAYER)

    print(
        f"Computing the {args.variable} 1981-2010 baseline for "
        f"{args.nuts3} ..."
    )
    historical_monthly, _ = process_nuts3_climatology(
        municipalities_gdf=municipalities_gdf,
        nuts3_name=args.nuts3,
        chelsa_dir=CHELSA_DIR,
        variable=args.variable,
    )

    ensemble_climatology = pd.read_csv(ensemble_path)

    anomaly_df = calculate_climate_anomalies(
        ensemble_climatology=ensemble_climatology,
        historical_climatology=historical_monthly,
    )

    region_municipalities = get_municipalities_by_nuts3(
        municipalities_gdf=municipalities_gdf,
        nuts3_name=args.nuts3,
        target_crs="EPSG:4326",
    )

    combinations = (
        anomaly_df[anomaly_df["variable"] == args.variable]
        [["scenario", "period"]]
        .drop_duplicates()
        .itertuples(index=False)
    )

    written = []

    for scenario, period in combinations:
        feature_collection = build_future_pilot_feature_collection(
            municipalities_gdf=region_municipalities,
            anomaly_df=anomaly_df,
            variable=args.variable,
            scenario=scenario,
            period=period,
        )

        metadata = build_future_pilot_metadata(
            region_slug=args.region_slug,
            region_name=args.nuts3,
            variable=args.variable,
            scenario=scenario,
            period=period,
            dataset=config["future"]["dataset"],
            gcms=config["models"]["gcms"],
            methodology_status=config["project"]["methodology_status"],
        )

        geojson_path, _ = save_future_pilot_artifacts(
            feature_collection=feature_collection,
            metadata=metadata,
            output_dir=OUTPUT_DIR,
            region_slug=args.region_slug,
            variable=args.variable,
            scenario=scenario,
            period=period,
        )

        written.append(geojson_path)

        print(
            f"  wrote {len(feature_collection['features'])} "
            f"municipalities for {scenario}/{period} to {geojson_path}"
        )

    if not written:
        print(
            f"No {args.variable} rows found in {ensemble_path} - "
            "nothing written."
        )
        return 1

    print(
        f"\nWrote {len(written)} scenario/period combination(s). "
        "Restart the API to serve them."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
