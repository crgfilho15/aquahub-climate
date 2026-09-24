import csv

import pytest

from src.indices_catalog import (
    IndicesCatalogError,
    indices_for_crop,
    load_indices_catalog,
    validate_against_variable_codes,
)

CSV_HEADER = [
    "Categoria",
    "Acronimo",
    "Indice",
    "Formula",
    "Referencia",
    "Vinha",
    "Olival",
    "Amendoal",
    "Cerejeira",
]


def write_csv(tmp_path, rows):
    path = tmp_path / "indices_por_cultura.csv"

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(CSV_HEADER)
        writer.writerows(rows)

    return path


def make_rows():
    return [
        [
            "Limiares e extremos de temperatura",
            "TMIN17",
            "Dias de frio severo",
            "Nº de dias com Tn ≤ −17 °C",
            "Huglin & Schneider (1998)",
            "1",
            "1",
            "1",
            "0",
        ],
        [
            "Precipitação",
            "PREC_ANNUAL",
            "Precipitação anual",
            "Σ P no ano",
            "—",
            "1",
            "1",
            "1",
            "1",
        ],
    ]


def test_load_indices_catalog_parses_rows_and_crop_flags(tmp_path):
    path = write_csv(tmp_path, make_rows())

    catalog = load_indices_catalog(path)

    assert catalog["language"] == "pt"
    assert set(catalog["indices"].keys()) == {"TMIN17", "PREC_ANNUAL"}

    tmin17 = catalog["indices"]["TMIN17"]
    assert tmin17["category"] == "Limiares e extremos de temperatura"
    assert tmin17["name"] == "Dias de frio severo"
    assert tmin17["formula"] == "Nº de dias com Tn ≤ −17 °C"
    assert tmin17["crops"] == ["grapevine", "olive", "almond"]

    prec = catalog["indices"]["PREC_ANNUAL"]
    assert prec["crops"] == ["grapevine", "olive", "almond", "cherry"]


def test_load_indices_catalog_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_indices_catalog(tmp_path / "does_not_exist.csv")


def test_load_indices_catalog_duplicate_code_raises(tmp_path):
    rows = make_rows()
    rows.append(rows[0])  # duplicate TMIN17
    path = write_csv(tmp_path, rows)

    with pytest.raises(IndicesCatalogError, match="Duplicate index code"):
        load_indices_catalog(path)


def test_load_indices_catalog_missing_column_raises(tmp_path):
    path = tmp_path / "bad.csv"
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Categoria", "Acronimo"])  # missing columns
        writer.writerow(["x", "TMIN17"])

    with pytest.raises(IndicesCatalogError, match="Missing expected columns"):
        load_indices_catalog(path)


def test_validate_against_variable_codes_matches_ok(tmp_path):
    path = write_csv(tmp_path, make_rows())
    catalog = load_indices_catalog(path)

    validate_against_variable_codes(catalog, {"TMIN17", "PREC_ANNUAL"})


def test_validate_against_variable_codes_mismatch_raises(tmp_path):
    path = write_csv(tmp_path, make_rows())
    catalog = load_indices_catalog(path)

    with pytest.raises(IndicesCatalogError):
        validate_against_variable_codes(
            catalog, {"TMIN17", "SOMETHING_ELSE"}
        )


def test_indices_for_crop_filters_correctly(tmp_path):
    path = write_csv(tmp_path, make_rows())
    catalog = load_indices_catalog(path)

    cherry_indices = indices_for_crop(catalog, "cherry")

    assert set(cherry_indices.keys()) == {"PREC_ANNUAL"}
