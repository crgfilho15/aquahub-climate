"""
Compute climate-change anomalies (future minus 1981-2010 baseline) for
one AquaHub region/variable, from a Phase 4 ensemble CSV.

Phase 5 of the roadmap (docs/04_roadmap_future_and_bioclimatic_indices.md):
these are the numbers the platform should actually display - "how much
warmer/wetter/drier will it get" - not the raw future absolute value
alone.

This must be run locally, where the CAOP boundaries and historical
CHELSA rasters are available (same requirement as
scripts/build_pilot_region.py), since it recomputes the historical
baseline climatology to compare the ensemble against.

Usage
-----
    python -m scripts.build_anomaly_climatology data/processed/ensemble/douro_tas_future_climatology_ensemble.csv
    python -m scripts.build_anomaly_climatology data/processed/ensemble/douro_tas_future_climatology_ensemble.csv --region Douro --variable tas

Output
------
    data/processed/anomalies/{input filename with "_ensemble" replaced by "_anomalies"}.csv
"""

import argparse
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

from src.climate_anomalies import calculate_climate_anomalies
from src.climate_pipeline import process_nuts3_climatology

CAOP_PATH = Path("data/raw/boundaries/Continente_CAOP2025.gpkg")
CAOP_LAYER = "cont_municipios"
CHELSA_DIR = Path("data/raw/chelsa")
OUTPUT_DIR = Path("data/processed/anomalies")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "ensemble_csv",
        help="Path to a Phase 4 ensemble CSV (scripts/build_ensemble_climatology.py's output).",
    )
    parser.add_argument(
        "--region",
        default="Douro",
        help="NUTS III region name (default: Douro).",
    )
    parser.add_argument(
        "--variable",
        default="tas",
        help="CHELSA variable, must match the ensemble CSV's variable (default: tas).",
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

    print(f"Loading CAOP boundaries from {CAOP_PATH} ...")
    municipalities_gdf = gpd.read_file(CAOP_PATH, layer=CAOP_LAYER)

    print(
        f"Computing the {args.variable} 1981-2010 baseline for "
        f"{args.region} ..."
    )
    historical_monthly, _ = process_nuts3_climatology(
        municipalities_gdf=municipalities_gdf,
        nuts3_name=args.region,
        chelsa_dir=CHELSA_DIR,
        variable=args.variable,
    )

    ensemble_climatology = pd.read_csv(ensemble_path)

    result = calculate_climate_anomalies(
        ensemble_climatology=ensemble_climatology,
        historical_climatology=historical_monthly,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_name = ensemble_path.name.replace(
        "_ensemble.csv",
        "_anomalies.csv",
    )

    output_path = OUTPUT_DIR / output_name

    result.to_csv(output_path, index=False)

    print(f"Wrote {len(result)} anomaly rows to {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
