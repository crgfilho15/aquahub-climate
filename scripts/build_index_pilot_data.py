"""
Build the per-zone bioclimatic index artefacts the Climate Atlas
serves for the professor's ensemble1 delivery: for each of the 5
AquaHub zones and each of ensemble1's 3 epochs (historical,
ssp126_2041-2070, ssp585_2041-2070), writes a small per-zone raster
(for the heatmap overlay and point-query) plus a zonal-statistics JSON
(the authoritative mean/min/max, via exact_extract).

See src/index_pilot_export.py's module docstring for why the raster is
uint16-encoded (real measured total ~141MB across all 15 files, vs.
224MB as float32 - see docs/04 Section 2.1) and docs/04 Phase 7 for
why this data stays in Portuguese for now.

Usage
-----
    python -m scripts.build_index_pilot_data

Output
------
    data/processed/pilot/indices/{slug}_{epoch}.tif
    data/processed/pilot/indices/{slug}_{epoch}_stats.json
"""

import sys
from pathlib import Path

import xarray as xr

from src.index_pilot_export import (
    compute_variable_scale_offsets,
    compute_zone_index_stats,
    crop_zone_indices_raster,
    load_zone_geometries,
    save_zone_index_stats,
)

ZONES_OVERVIEW_PATH = Path("data/processed/pilot/zones_overview.geojson")
OUTPUT_DIR = Path("data/processed/pilot/indices")

EPOCHS = {
    "historical": Path(
        "data/raw/ensemble1/historical/ensemble_historical_1981-2010.nc"
    ),
    "ssp126_2041-2070": Path(
        "data/raw/ensemble1/ssp126/ensemble_ssp126_2041-2070.nc"
    ),
    "ssp585_2041-2070": Path(
        "data/raw/ensemble1/ssp585/ensemble_ssp585_2041-2070.nc"
    ),
}


def main() -> None:
    missing = [str(p) for p in EPOCHS.values() if not p.exists()]

    if missing:
        raise SystemExit(
            "ensemble1 file(s) not found: " + ", ".join(missing)
        )

    zones_gdf = load_zone_geometries(ZONES_OVERVIEW_PATH)

    print(
        f"Building index pilot data for {len(zones_gdf)} zones x "
        f"{len(EPOCHS)} epochs = {len(zones_gdf) * len(EPOCHS)} "
        "zone/epoch combinations ..."
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for epoch, nc_path in EPOCHS.items():
        print(f"\n=== {epoch} ({nc_path}) ===")

        with xr.open_dataset(nc_path) as dataset:
            variable_codes = list(dataset.data_vars.keys())
            scale_offsets = compute_variable_scale_offsets(dataset)

            print(
                f"  Computing zonal stats for {len(variable_codes)} "
                "indices via exact_extract ..."
            )
            stats_df = compute_zone_index_stats(
                nc_path, zones_gdf, variable_codes
            )

            for _, row in zones_gdf.iterrows():
                slug = row["slug"]
                raster_path = OUTPUT_DIR / f"{slug}_{epoch}.tif"

                crop_zone_indices_raster(
                    dataset=dataset,
                    zone_geometry=row.geometry,
                    scale_offsets=scale_offsets,
                    output_path=raster_path,
                )
                size_mb = raster_path.stat().st_size / 1e6

                stats_path = save_zone_index_stats(
                    stats_df, OUTPUT_DIR, slug, epoch
                )

                print(
                    f"  {slug}: {raster_path.name} ({size_mb:.2f} MB), "
                    f"{stats_path.name}"
                )

    tif_files = list(OUTPUT_DIR.glob("*.tif"))
    total_mb = sum(f.stat().st_size for f in tif_files) / 1e6

    print(
        f"\nDone. {len(tif_files)} raster files, {total_mb:.2f} MB "
        f"total, in {OUTPUT_DIR}."
    )


if __name__ == "__main__":
    sys.exit(main())
