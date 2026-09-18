"""Export utilities for the AquaHub interactive pilot platform.

These functions convert already-validated climate processing results
(municipality geometries + monthly/annual climatology) into the static
JSON artefacts served by the pilot API. They do not perform any climate
processing themselves and do not require CHELSA or CAOP access.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd


class PilotExportError(ValueError):
    """Raised when pilot export inputs are inconsistent."""


def build_pilot_feature_collection(
    municipalities_gdf: gpd.GeoDataFrame,
    monthly_df: pd.DataFrame,
    annual_df: pd.DataFrame,
) -> dict:
    """
    Build a GeoJSON FeatureCollection combining municipality
    geometries with their climatology.

    Parameters
    ----------
    municipalities_gdf : geopandas.GeoDataFrame
        Must contain a 'municipio' column and be in EPSG:4326.

    monthly_df : pandas.DataFrame
        Must contain 'municipality', 'month', 'mean_value', as
        returned by the generic climate pipeline
        (src/climate_pipeline.py's process_nuts3_climatology /
        process_multi_nuts3_climatology).

    annual_df : pandas.DataFrame
        Must contain 'municipality', 'mean_value', 'variable',
        'period', 'source', as returned by the generic climate
        pipeline.

    Returns
    -------
    dict
        A GeoJSON FeatureCollection. One feature per municipality,
        with 'annual_mean_celsius' and a 12-value
        'monthly_mean_celsius' array ordered by calendar month.
    """

    if municipalities_gdf.crs is None:
        raise PilotExportError(
            "municipalities_gdf must have a defined CRS."
        )

    if str(municipalities_gdf.crs).upper() != "EPSG:4326":
        raise PilotExportError(
            "municipalities_gdf must be reprojected to EPSG:4326."
        )

    annual_lookup = annual_df.set_index("municipality")

    monthly_lookup = {
        name: (
            group
            .sort_values("month")
            .set_index("month")["mean_value"]
        )
        for name, group in monthly_df.groupby("municipality")
    }

    features = []

    for _, row in municipalities_gdf.iterrows():
        municipio = row["municipio"]

        if municipio not in annual_lookup.index:
            raise PilotExportError(
                f"Missing annual climatology for: {municipio}"
            )

        if municipio not in monthly_lookup:
            raise PilotExportError(
                f"Missing monthly climatology for: {municipio}"
            )

        monthly_series = monthly_lookup[municipio]

        missing_months = set(range(1, 13)) - set(monthly_series.index)

        if missing_months:
            raise PilotExportError(
                f"Missing months {sorted(missing_months)} "
                f"for: {municipio}"
            )

        annual_row = annual_lookup.loc[municipio]

        properties = {
            "municipio": municipio,
            "nuts3": row.get("nuts3"),
            "variable": annual_row["variable"],
            "period": annual_row["period"],
            "source": annual_row["source"],
            "annual_mean_celsius": round(
                float(annual_row["mean_value"]), 3
            ),
            "monthly_mean_celsius": [
                round(float(monthly_series.loc[month]), 3)
                for month in range(1, 13)
            ],
        }

        features.append(
            {
                "type": "Feature",
                "properties": properties,
                "geometry": json.loads(
                    gpd.GeoSeries(
                        [row.geometry],
                        crs=municipalities_gdf.crs,
                    ).to_json()
                )["features"][0]["geometry"],
            }
        )

    return {
        "type": "FeatureCollection",
        "features": features,
    }


def build_pilot_metadata(
    region_slug: str,
    region_type: str,
    region_name: str,
    variable: str,
    period: str,
    dataset: str,
    methodology_status: str,
) -> dict:
    """Build the metadata record describing the pilot dataset."""

    return {
        "slug": region_slug,
        "region_type": region_type,
        "region_name": region_name,
        "variable": variable,
        "period": period,
        "dataset": dataset,
        "methodology_status": methodology_status,
        "future_scenarios_included": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def save_pilot_artifacts(
    feature_collection: dict,
    metadata: dict,
    output_dir: str | Path,
    region_slug: str,
) -> tuple[Path, Path]:
    """
    Persist the pilot GeoJSON and metadata files to disk.

    Returns
    -------
    tuple[pathlib.Path, pathlib.Path]
        Paths of the written GeoJSON and metadata files.
    """

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    geojson_path = output_dir / f"{region_slug}_pilot.geojson"
    metadata_path = output_dir / f"{region_slug}_pilot_meta.json"

    geojson_path.write_text(
        json.dumps(feature_collection, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return geojson_path, metadata_path
