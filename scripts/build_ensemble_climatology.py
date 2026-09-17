"""
Compute multi-GCM ensemble statistics from a Phase 3 future
climatology CSV (scripts/build_future_climatology.py's output).

Phase 4 of the roadmap (docs/04_roadmap_future_and_bioclimatic_indices.md):
averages each municipality/month/variable/scenario/period's individual
GCM results into one ensemble mean plus uncertainty (min/max/std), per
config/climate.toml's [ensemble] section. Scenario and period are kept
as separate groups - never averaged together (see docs/04 Section 3).

Usage
-----
    python -m scripts.build_ensemble_climatology data/processed/future/douro_tas_future_climatology.csv

Output
------
    data/processed/ensemble/{input filename}_ensemble.csv
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

from src.climate_config import load_climate_config
from src.climate_ensemble import calculate_ensemble_climatology

OUTPUT_DIR = Path("data/processed/ensemble")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input_csv",
        help=(
            "Path to a Phase 3 future-climatology CSV (one row per "
            "municipality/month/GCM, e.g. "
            "data/processed/future/douro_tas_future_climatology.csv)."
        ),
    )
    args = parser.parse_args()

    input_path = Path(args.input_csv)

    if not input_path.exists():
        raise SystemExit(f"Input CSV not found: {input_path}")

    config = load_climate_config()

    gcm_results = pd.read_csv(input_path)

    result = calculate_ensemble_climatology(
        gcm_results=gcm_results,
        config=config,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_path = OUTPUT_DIR / input_path.name.replace(
        ".csv",
        "_ensemble.csv",
    )

    result.to_csv(output_path, index=False)

    print(
        f"Wrote {len(result)} ensemble rows "
        f"(averaging {gcm_results['gcm'].nunique()} GCMs per group) "
        f"to {output_path}"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
