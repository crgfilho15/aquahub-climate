"""
Build future (GCM/SSP) monthly climatology for one AquaHub region.

Phase 3 of the roadmap (docs/04_roadmap_future_and_bioclimatic_indices.md):
downloads (or reuses already-persisted) future CHELSA v2.1 rasters for
every configured GCM, scenario and period, and computes per-municipality
monthly statistics for each one individually (no ensembling across GCMs
yet - that is Phase 4).

This must be run locally, with normal internet access and the CAOP
boundaries file available (same requirement as
scripts/build_pilot_region.py). Each (GCM, scenario, period) needs 12
real downloads (one per month), so the default scope - config/climate.toml's
full GCM list, both configured scenarios, all three periods, one
variable - is already 5 x 2 x 3 x 12 = 360 downloads. Use --scenario/
--period/--variable to narrow this for a first, faster run.

Usage
-----
    python -m scripts.build_future_climatology
    python -m scripts.build_future_climatology --region Douro --variable tas --scenario ssp585 --period 2041-2070
    python -m scripts.build_future_climatology --force-download

Output
------
    data/processed/future/{region_slug}_{variable}_future_climatology.csv
"""

import argparse
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

from src.climate_config import load_climate_config
from src.climate_paths import slugify
from src.future_climate_processing import (
    calculate_future_monthly_climatology_for_all_gcms,
)

CAOP_PATH = Path("data/raw/boundaries/Continente_CAOP2025.gpkg")
CAOP_LAYER = "cont_municipios"
OUTPUT_DIR = Path("data/processed/future")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--region",
        default="Douro",
        help="NUTS III region name (default: Douro).",
    )
    parser.add_argument(
        "--variable",
        default="tas",
        help="CHELSA variable to process (default: tas).",
    )
    parser.add_argument(
        "--scenario",
        action="append",
        help=(
            "SSP scenario to process. Repeat for multiple. "
            "Default: every scenario in config/climate.toml."
        ),
    )
    parser.add_argument(
        "--period",
        action="append",
        help=(
            "Future period to process. Repeat for multiple. "
            "Default: every period in config/climate.toml."
        ),
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Re-download every month even if already persisted locally.",
    )
    args = parser.parse_args()

    config = load_climate_config()

    if not CAOP_PATH.exists():
        raise SystemExit(
            f"CAOP boundaries file not found: {CAOP_PATH}\n"
            "This script must be run locally, where the AquaHub "
            "raw data directory is populated."
        )

    scenarios = args.scenario or config["future"]["scenarios"]
    periods = args.period or config["future"]["periods"]
    gcms = config["models"]["gcms"]

    combinations = len(scenarios) * len(periods)
    downloads = combinations * len(gcms) * 12

    print(
        f"Region: {args.region} | variable: {args.variable}\n"
        f"Scenarios: {scenarios}\n"
        f"Periods: {periods}\n"
        f"GCMs: {gcms}\n"
        f"=> {combinations} scenario/period combinations, up to "
        f"{downloads} real downloads (already-persisted months are "
        "reused unless --force-download is set)."
    )

    print(f"Loading CAOP boundaries from {CAOP_PATH} ...")
    municipalities_gdf = gpd.read_file(CAOP_PATH, layer=CAOP_LAYER)

    results = []

    for scenario in scenarios:
        for period in periods:
            print(
                f"\n--- {args.variable} | {scenario} | {period} "
                f"({len(gcms)} GCMs x 12 months) ---"
            )

            result = calculate_future_monthly_climatology_for_all_gcms(
                config=config,
                municipalities_gdf=municipalities_gdf,
                scenario=scenario,
                period=period,
                variable=args.variable,
                region_type="NUTS3",
                region_name=args.region,
                force_download=args.force_download,
            )

            results.append(result)

    combined = pd.concat(results, ignore_index=True)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_path = (
        OUTPUT_DIR
        / f"{slugify(args.region)}_{args.variable}_future_climatology.csv"
    )

    combined.to_csv(output_path, index=False)

    print(
        f"\nWrote {len(combined)} rows "
        f"({combined['gcm'].nunique()} GCMs x "
        f"{combined['scenario'].nunique()} scenarios x "
        f"{combined['period'].nunique()} periods x 12 months x "
        f"{combined['municipality'].nunique()} municipalities) "
        f"to {output_path}"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
