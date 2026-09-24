"""
Build data/processed/pilot/indices_catalog.json from the professor's
data/raw/ensemble1/indices_por_cultura.csv delivery, validated against
ensemble1's real NetCDF variable codes so the Climate Atlas never
serves an Index filter that has silently drifted out of sync with the
actual raster data.

Usage
-----
    python -m scripts.build_indices_catalog

Output
------
    data/processed/pilot/indices_catalog.json
"""

import json
import sys
from pathlib import Path

import xarray as xr

from src.indices_catalog import (
    load_indices_catalog,
    validate_against_variable_codes,
)

ENSEMBLE_HISTORICAL_PATH = Path(
    "data/raw/ensemble1/historical/ensemble_historical_1981-2010.nc"
)
OUTPUT_PATH = Path("data/processed/pilot/indices_catalog.json")


def main() -> None:
    if not ENSEMBLE_HISTORICAL_PATH.exists():
        raise SystemExit(
            "ensemble1 historical file not found - see docs/04 Section "
            f"2.1 for where it should live: {ENSEMBLE_HISTORICAL_PATH}"
        )

    print(f"Reading variable codes from {ENSEMBLE_HISTORICAL_PATH} ...")
    with xr.open_dataset(ENSEMBLE_HISTORICAL_PATH) as ds:
        variable_codes = set(ds.data_vars.keys())

    print(f"Parsing catalog from data/raw/ensemble1/indices_por_cultura.csv ...")
    catalog = load_indices_catalog()

    print(
        f"Validating {len(catalog['indices'])} catalog codes against "
        f"{len(variable_codes)} ensemble1 variables ..."
    )
    validate_against_variable_codes(catalog, variable_codes)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(
        f"\nWrote {len(catalog['indices'])} indices to {OUTPUT_PATH} "
        "(language: pt, pending an English translation pass - see "
        "docs/04 Phase 7)."
    )


if __name__ == "__main__":
    sys.exit(main())
