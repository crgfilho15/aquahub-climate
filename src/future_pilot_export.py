"""Export utilities for future/ensemble/anomaly data on the pilot platform.

Phase 9 of the roadmap (docs/04_roadmap_future_and_bioclimatic_indices.md):
converts Phase 5's anomaly output (which already carries Phase 4's
ensemble values) into the same kind of static GeoJSON/metadata artefact
src/pilot_export.py produces for the historical baseline, so the
existing API-serves-static-files architecture extends to future data
without becoming a live-computation backend.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd

from src.climate_processing import calculate_annual_climatology_for_regions


class FuturePilotExportError(ValueError):
    """Raised when future pilot export inputs are inconsistent."""


def _parse_period_years(period: str) -> tuple[int, int]:
    """Parse a 'YYYY-YYYY' period string into (start_year, end_year)."""

    parts = period.split("-")

    if len(parts) != 2 or not all(p.strip().isdigit() for p in parts):
        raise FuturePilotExportError(
            f"period must look like 'YYYY-YYYY', got: '{period}'."
        )

    start_year, end_year = (int(p) for p in parts)

    if start_year >= end_year:
        raise FuturePilotExportError(
            f"period's start year must be before its end year: '{period}'."
        )

    return start_year, end_year


def _annualize(
    monthly_df: pd.DataFrame,
    value_column: str,
    start_year: int,
    end_year: int,
) -> pd.Series:
    """
    Weighted annual mean of one monthly column, reusing the same
    days-in-month weighting the historical pipeline uses
    (calculate_annual_climatology_for_regions), indexed by
    municipality.
    """

    renamed = monthly_df[["municipality", "month", value_column]].rename(
        columns={value_column: "mean_value"}
    )

    annual = calculate_annual_climatology_for_regions(
        monthly_df=renamed,
        start_year=start_year,
        end_year=end_year,
    )

    return annual.set_index("municipality")["mean_value"]


def build_future_pilot_feature_collection(
    municipalities_gdf: gpd.GeoDataFrame,
    anomaly_df: pd.DataFrame,
    variable: str,
    scenario: str,
    period: str,
) -> dict:
    """
    Build a GeoJSON FeatureCollection combining municipality
    geometries with one variable/scenario/period slice of Phase 5's
    anomaly output (which already carries Phase 4's ensemble values).

    Parameters
    ----------
    municipalities_gdf : geopandas.GeoDataFrame
        Must contain a 'municipio' column and be in EPSG:4326.

    anomaly_df : pandas.DataFrame
        Output of src.climate_anomalies.calculate_climate_anomalies,
        already filtered (or not - this function filters internally)
        to one variable/scenario/period.

    variable, scenario, period : str
        The slice of anomaly_df to export.

    Returns
    -------
    dict
        A GeoJSON FeatureCollection. One feature per municipality,
        with annual and 12-value monthly arrays for the ensemble mean
        and the anomaly (absolute, and percent where computed - see
        src.climate_anomalies.PERCENT_ANOMALY_VARIABLES).
    """

    if municipalities_gdf.crs is None:
        raise FuturePilotExportError(
            "municipalities_gdf must have a defined CRS."
        )

    if str(municipalities_gdf.crs).upper() != "EPSG:4326":
        raise FuturePilotExportError(
            "municipalities_gdf must be reprojected to EPSG:4326."
        )

    start_year, end_year = _parse_period_years(period)

    slice_df = anomaly_df[
        (anomaly_df["variable"] == variable)
        & (anomaly_df["scenario"] == scenario)
        & (anomaly_df["period"] == period)
    ]

    if slice_df.empty:
        raise FuturePilotExportError(
            f"anomaly_df has no rows for variable='{variable}', "
            f"scenario='{scenario}', period='{period}'."
        )

    has_percent = slice_df["anomaly_percent"].notna().any()

    annual_ensemble = _annualize(
        slice_df, "ensemble_mean", start_year, end_year
    )
    annual_anomaly = _annualize(
        slice_df, "anomaly_absolute", start_year, end_year
    )

    monthly_ensemble_lookup = {
        name: group.sort_values("month").set_index("month")["ensemble_mean"]
        for name, group in slice_df.groupby("municipality")
    }
    monthly_anomaly_lookup = {
        name: group.sort_values("month").set_index("month")["anomaly_absolute"]
        for name, group in slice_df.groupby("municipality")
    }

    unit_lookup = (
        slice_df
        .drop_duplicates("municipality")
        .set_index("municipality")["unit"]
    )

    n_gcms_lookup = None
    if "n_gcms" in slice_df.columns:
        n_gcms_lookup = (
            slice_df
            .drop_duplicates("municipality")
            .set_index("municipality")["n_gcms"]
        )

    features = []

    for _, row in municipalities_gdf.iterrows():
        municipio = row["municipio"]

        if municipio not in monthly_ensemble_lookup:
            raise FuturePilotExportError(
                f"Missing future climatology for: {municipio}"
            )

        monthly_ensemble = monthly_ensemble_lookup[municipio]
        monthly_anomaly = monthly_anomaly_lookup[municipio]

        missing_months = set(range(1, 13)) - set(monthly_ensemble.index)

        if missing_months:
            raise FuturePilotExportError(
                f"Missing months {sorted(missing_months)} for: {municipio}"
            )

        properties = {
            "municipio": municipio,
            "nuts3": row.get("nuts3"),
            "variable": variable,
            "scenario": scenario,
            "period": period,
            "unit": str(unit_lookup.loc[municipio]),
            "annual_ensemble_mean": round(
                float(annual_ensemble.loc[municipio]), 3
            ),
            "annual_anomaly_absolute": round(
                float(annual_anomaly.loc[municipio]), 3
            ),
            "monthly_ensemble_mean": [
                round(float(monthly_ensemble.loc[month]), 3)
                for month in range(1, 13)
            ],
            "monthly_anomaly_absolute": [
                round(float(monthly_anomaly.loc[month]), 3)
                for month in range(1, 13)
            ],
        }

        if n_gcms_lookup is not None:
            properties["n_gcms"] = int(n_gcms_lookup.loc[municipio])

        if has_percent:
            monthly_percent = (
                slice_df[slice_df["municipality"] == municipio]
                .sort_values("month")
                .set_index("month")["anomaly_percent"]
            )
            properties["monthly_anomaly_percent"] = [
                round(float(monthly_percent.loc[month]), 1)
                for month in range(1, 13)
            ]

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


def build_future_pilot_metadata(
    region_slug: str,
    region_name: str,
    variable: str,
    scenario: str,
    period: str,
    dataset: str,
    gcms: list[str],
    methodology_status: str,
) -> dict:
    """Build the metadata record describing one future pilot slice."""

    return {
        "slug": region_slug,
        "region_name": region_name,
        "variable": variable,
        "scenario": scenario,
        "period": period,
        "dataset": dataset,
        "gcms": gcms,
        "ensemble_method": "equal_weight_mean",
        "methodology_status": methodology_status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def save_future_pilot_artifacts(
    feature_collection: dict,
    metadata: dict,
    output_dir: str | Path,
    region_slug: str,
    variable: str,
    scenario: str,
    period: str,
) -> tuple[Path, Path]:
    """
    Persist one future pilot GeoJSON/metadata pair to disk, named so
    api/main.py's future endpoints can find it from
    (region, variable, scenario, period) alone.
    """

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    stem = f"{region_slug}_{variable}_{scenario}_{period}_future"

    geojson_path = output_dir / f"{stem}.geojson"
    metadata_path = output_dir / f"{stem}_meta.json"

    geojson_path.write_text(
        json.dumps(feature_collection, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return geojson_path, metadata_path
