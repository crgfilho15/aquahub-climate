"""
Loading and validation of the professor's crop-index catalog.

Parses data/raw/ensemble1/indices_por_cultura.csv - the professor's
first real bioclimatic-index delivery (code, name, formula, literature
reference, and per-crop relevance for the 4 target crops) - and
validates it against ensemble1's actual variable codes before it is
trusted as the Climate Atlas's Index filter data source.

Kept in Portuguese exactly as delivered - see
docs/04_roadmap_future_and_bioclimatic_indices.md, Phase 7: an English
translation pass is a deliberate, separate follow-up, not done here.
Only this module's own keys ("category", "name", "formula",
"reference", "crops") are language-neutral, so that later pass only
needs to replace values, not restructure the catalog.
"""

import csv
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_CSV_PATH = Path("data/raw/ensemble1/indices_por_cultura.csv")

# Maps the CSV's Portuguese crop columns to the same crop slugs already
# used by the platform's Crop selector (web/app.js's CULTURAS list).
CROP_COLUMNS = {
    "Vinha": "grapevine",
    "Olival": "olive",
    "Amendoal": "almond",
    "Cerejeira": "cherry",
}


class IndicesCatalogError(ValueError):
    """Raised when the indices catalog is invalid or inconsistent."""


def load_indices_catalog(csv_path: str | Path = DEFAULT_CSV_PATH) -> dict:
    """
    Parse the professor's crop-index CSV into a catalog dict, keyed by
    index code (the CSV's "Acronimo" column).

    Returns
    -------
    dict
        {"language": "pt", "source": str, "generated_at": str,
         "indices": {code: {"category", "name", "formula",
         "reference", "crops": [...]}}}
    """

    path = Path(csv_path)

    if not path.exists():
        raise FileNotFoundError(f"Indices catalog CSV not found: {path}")

    with path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise IndicesCatalogError(f"No rows found in: {path}")

    required_columns = (
        {"Categoria", "Acronimo", "Indice", "Formula", "Referencia"}
        | CROP_COLUMNS.keys()
    )
    missing_columns = required_columns - set(rows[0].keys())

    if missing_columns:
        raise IndicesCatalogError(
            f"Missing expected columns in {path}: {sorted(missing_columns)}"
        )

    indices: dict[str, dict] = {}

    for row in rows:
        code = row["Acronimo"].strip()

        if not code:
            raise IndicesCatalogError(f"Row with empty 'Acronimo' in: {path}")

        if code in indices:
            raise IndicesCatalogError(
                f"Duplicate index code '{code}' in: {path}"
            )

        crops = [
            slug
            for column, slug in CROP_COLUMNS.items()
            if row.get(column, "").strip() == "1"
        ]

        indices[code] = {
            "category": row["Categoria"].strip(),
            "name": row["Indice"].strip(),
            "formula": row["Formula"].strip(),
            "reference": row["Referencia"].strip(),
            "crops": crops,
        }

    return {
        "language": "pt",
        "source": str(path),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "indices": indices,
    }


def validate_against_variable_codes(
    catalog: dict, variable_codes: set[str]
) -> None:
    """
    Confirm the catalog's index codes exactly match a known set of
    variable codes (e.g. ensemble1's real NetCDF variables) - raise
    loudly on any mismatch rather than silently ingesting a partial or
    stale catalog. Same defensive pattern as CHELSA_VARIABLE_UNITS in
    src/climate_processing.py.
    """

    catalog_codes = set(catalog["indices"].keys())

    missing_from_catalog = variable_codes - catalog_codes
    missing_from_variables = catalog_codes - variable_codes

    if missing_from_catalog or missing_from_variables:
        raise IndicesCatalogError(
            "Indices catalog does not match the given variable codes. "
            f"In variables but not catalog: {sorted(missing_from_catalog)}. "
            f"In catalog but not variables: {sorted(missing_from_variables)}."
        )


def indices_for_crop(catalog: dict, crop: str) -> dict[str, dict]:
    """Subset of catalog['indices'] whose 'crops' includes the given
    crop slug (e.g. 'grapevine')."""

    return {
        code: entry
        for code, entry in catalog["indices"].items()
        if crop in entry["crops"]
    }
