# AquaHub Climate Platform

Prototype geospatial climate-data processing workflow developed within the AquaHub project at UTAD.

## Project context

AquaHub is focused on climate, water, soil and sustainable management of traditional crops in mountain regions across the Spain–Portugal cooperation area.

The current prototype validates the geospatial and climatological processing workflow required for the future climate and agroclimatic atlas.

The final AquaHub solution is expected to include:

- high-resolution climate information (~1 km);
- present and future climate conditions;
- SSP climate scenarios;
- multiple Global Climate Models (GCMs);
- multi-model ensembles;
- bioclimatic indices;
- crop-specific agroclimatic zoning;
- interactive maps and climate visualisations.

The definitive climate datasets and modelling methodology are still under discussion with the research team.

---

## Interactive pilot platform (v2)

An interactive map platform is available, built on the validated baseline climatology pipeline below. Per the professor's confirmed design (Sept 2026), it shows all 5 intervention zones on a single map at once (Douro, Terras de Trás-os-Montes and Beira Interior in Portugal; Castilla y León and Extremadura in Spain), clickable to open a distribution chart, with Cultura/Índice/Período/SSP filters above the map — Cultura/Índice are shown (the 4 confirmed crops) but disabled until the professor delivers real bioclimatic index data. Douro and Terras de Trás-os-Montes are fully validated with real data; Beira Interior needs a CHELSA/CAOP run; the 2 Spanish zones have confirmed boundaries but no climate-data pipeline yet — see `config/climate.toml`.

Full details, architecture rationale and known limitations: `docs/03_pilot_interactive_platform.md`.

Quick start, once `data/raw/` is populated as described below:

```powershell
python -m scripts.build_pilot_region
python -m scripts.build_zone_overview
uvicorn api.main:app --reload
# open http://127.0.0.1:8000
```

---

## Current prototype

The current proof of concept uses:

- Climate variable: `tas`
- Variable meaning: mean near-surface air temperature
- Climate period: 1981–2010
- Climate source: CHELSA climatologies v2.1
- Administrative boundaries: CAOP2025
- Climate raster spatial resolution: approximately 1 km
- Climate raster CRS: EPSG:4326

The prototype initially used Vila Real as the reference municipality and was subsequently extended to multiple municipalities and complete NUTS III regions.

The objective is to validate the complete workflow:

```text
CHELSA raster
      ↓
Administrative geometry
      ↓
CRS harmonisation
      ↓
Raster–polygon intersection
      ↓
Area-weighted zonal statistics
      ↓
Monthly climatology
      ↓
Annual climatological aggregation
      ↓
Processed datasets
```

---

## Current validated results

For the municipality of Vila Real, the area-weighted mean annual temperature climatology for 1981–2010 is:

**12.029871 °C**

Additional validated annual climatologies include:

| Municipality | Mean annual temperature |
|---|---:|
| Vila Real | 12.029871 °C |
| Bragança | 12.178043 °C |
| Chaves | 12.865129 °C |

Monthly climate values have also been calculated and validated.

The regional workflow has additionally been validated for the NUTS III region:

**Douro**

The current Douro processing includes:

- 19 municipalities;
- 12 monthly climatologies per municipality;
- 228 monthly municipality records;
- 19 annual municipality climatologies.

---

## Project structure

```text
aquahub-climate/
│
├── .venv/
│
├── api/
│   └── main.py
│
├── config/
│   └── climate.toml
│
├── data/
│   ├── raw/
│   │   ├── chelsa/
│   │   └── boundaries/
│   └── processed/
│       └── pilot/            (generated locally, not versioned)
│
├── docs/
│   ├── 01_climate_baseline_methodology.md
│   ├── 02_methodological_questions_for_team.md
│   ├── 03_pilot_interactive_platform.md
│   └── 04_roadmap_future_and_bioclimatic_indices.md
│
├── outputs/
│   ├── figures/
│   └── tables/
│
├── scripts/
│   ├── build_pilot_region.py
│   ├── build_zone_overview.py
│   ├── export_zones_shapefile.py
│   ├── inspect_gisco_boundaries.py
│   ├── build_indices_catalog.py
│   └── build_index_pilot_data.py
│
├── src/
│   ├── boundary_processing.py
│   ├── climate_config.py
│   ├── climate_pipeline.py
│   ├── climate_processing.py
│   ├── gisco_boundary_processing.py
│   ├── index_pilot_export.py
│   ├── indices_catalog.py
│   ├── pilot_export.py
│   └── zone_overview_export.py
│
├── web/
│   ├── index.html
│   ├── atlas.html
│   ├── app.js
│   ├── site.css
│   ├── style.css
│   ├── site-chrome.js
│   └── vendor/leaflet/
│
├── tests/
│   └── ... (one test module per src/ module, plus test_pilot_export.py and test_pilot_api.py)
│
├── pytest.ini
├── README.md
├── requirements.txt          (Vercel runtime deps - see the file itself)
├── requirements-pipeline.txt (local data-pipeline + test deps)
├── vercel.json                (trims the deployed function bundle)
└── .vercelignore
```

---

## Environment

Current development environment:

- Windows
- Python 3.14
- VS Code
- pytest

Main Python libraries:

- pandas
- geopandas
- rasterio
- rioxarray
- exactextract
- pytest

---

## Installation

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies. `requirements.txt` alone is enough to run the API
(`uvicorn api.main:app`) - it's deliberately minimal, since it's also
what Vercel installs for the deployed function (see the file's own
comments). For local data-pipeline work and the full test suite, also
install `requirements-pipeline.txt`:

```powershell
pip install -r requirements.txt -r requirements-pipeline.txt
```

---

## Data sources

### CHELSA

Climate raster data are currently obtained from:

**CHELSA climatologies v2.1**

Current prototype configuration:

```text
Variable: tas
Period: 1981–2010
Temporal resolution: monthly climatology
Unit: Kelvin
CRS: EPSG:4326
Spatial resolution: approximately 1 km
```

The current files follow the naming pattern:

```text
CHELSA_tas_MM_1981-2010_V.2.1.tif
```

where `MM` represents the month from `01` to `12`.

The raster metadata contain a scale factor of `0.1`.

When raster values are accessed directly through Rasterio:

```text
real_value = raw_value × scale + offset
```

Temperature is converted from Kelvin to Celsius using:

```text
temperature_C = temperature_K - 273.15
```

When zonal statistics are calculated using `exactextract`, raster scale and offset metadata are applied automatically.

---

### CAOP2025

Official Portuguese administrative boundaries are obtained from:

**Carta Administrativa Oficial de Portugal — CAOP2025**

Current source file:

```text
Continente_CAOP2025.gpkg
```

Main layer:

```text
cont_municipios
```

Relevant administrative attributes include:

- municipality;
- district;
- NUTS III;
- NUTS II;
- administrative area;
- municipality geometry.

The original CRS is:

```text
EPSG:3763
ETRS89 / Portugal TM06
```

Administrative geometries are reprojected to:

```text
EPSG:4326
```

before intersection with CHELSA climate rasters.

---

## Spatial processing methodology

The climate workflow does not represent a municipality using only a city centroid or a single raster pixel.

Instead, the complete administrative polygon is used.

The spatial workflow is:

```text
CHELSA raster
      ↓
Municipality polygon
      ↓
Raster–polygon intersection
      ↓
Fractional pixel coverage
      ↓
Area-weighted zonal mean
```

Zonal statistics are calculated with `exactextract`.

The current weighting approach uses:

```python
coverage_weight=area_spherical_m2
```

This means that raster cells intersected only partially by an administrative boundary contribute proportionally to the calculated spatial mean.

For example:

```text
100% pixel coverage → full contribution
50% pixel coverage  → half contribution
```

This is important because real administrative boundaries do not normally coincide exactly with the CHELSA raster grid.

---

## Annual climatological aggregation

The annual temperature is not calculated using a simple arithmetic mean of the twelve monthly climatologies.

Instead, each monthly climatology is weighted by the actual number of calendar days represented in the complete climatological period.

For 1981–2010:

```text
Total number of days: 10,957
```

For example, February contributes according to the total number of February days occurring during the 30-year period, including leap years.

This produces the validated Vila Real annual mean:

```text
12.029871 °C
```

---

## Software architecture

The current prototype is organised into independent modules with different responsibilities.

### `src/boundary_processing.py`

Responsible for administrative geometry selection and preparation.

Main responsibilities:

- select a single municipality;
- select multiple municipalities;
- select municipality names belonging to a NUTS III;
- select all municipality geometries belonging to a NUTS III;
- perform case-insensitive administrative searches;
- validate missing administrative units;
- reproject administrative geometries to the CRS required by the climate rasters.

Current examples include:

```python
get_municipality_geometry(...)
get_municipalities_by_names(...)
get_municipalities_by_nuts3(...)
get_municipality_names_by_nuts3(...)
```

---

### `src/climate_processing.py`

Contains the core scientific climate-processing logic.

The current processing strategy is **regional-first**.

Multiple geometries are processed simultaneously against each monthly climate raster, avoiding repeated raster processing for each municipality.

Conceptually:

```text
January raster
      ↓
all municipalities
      ↓
municipality means

February raster
      ↓
all municipalities
      ↓
municipality means

...

December raster
```

Instead of:

```text
municipality 1 → 12 raster operations
municipality 2 → 12 raster operations
municipality 3 → 12 raster operations
...
```

The same regional processing core is also used internally by the single-municipality compatibility functions.

Main responsibilities include:

- area-weighted raster zonal statistics;
- fractional pixel coverage;
- Kelvin to Celsius conversion;
- monthly climatology processing;
- annual climatological aggregation;
- calendar-day weighting;
- multiple-region processing.

The regional processing functions form the scientific core of the current implementation.

Legacy single-region interfaces are retained as wrappers to preserve notebook and API compatibility.

---

### `src/climate_pipeline.py`

Coordinates the processing modules into higher-level workflows.

Current supported workflows include:

- processing one municipality by name;
- processing an arbitrary list of municipalities;
- processing all municipalities belonging to a NUTS III region.

Example municipality workflow:

```text
"Vila Real"
     ↓
CAOP municipality selection
     ↓
EPSG:4326
     ↓
12 CHELSA rasters
     ↓
monthly climatology
     ↓
annual climatology
```

Example regional workflow:

```text
"Douro"
   ↓
municipalities from CAOP
   ↓
19 municipality geometries
   ↓
reprojection to EPSG:4326
   ↓
12 CHELSA monthly rasters
   ↓
area-weighted zonal statistics
   ↓
228 monthly municipality records
   ↓
19 annual municipality climatologies
```

The high-level NUTS III workflow can be executed conceptually as:

```python
process_nuts3_climatology(
    municipalities_gdf=municipalities,
    nuts3_name="Douro",
    chelsa_dir=chelsa_dir,
    variable="tas",
    period="1981-2010",
)
```

---

## Processing examples

### NUTS III region

```python
monthly, annual = (
    pipeline.process_nuts3_climatology(
        municipalities_gdf=municipalities,
        nuts3_name="Douro",
        chelsa_dir=chelsa_dir,
        variable="tas",
        period="1981-2010",
    )
)
```

This automatically:

```text
selects NUTS III
      ↓
selects municipalities
      ↓
reprojects geometries
      ↓
processes monthly CHELSA rasters
      ↓
calculates monthly climatologies
      ↓
calculates annual climatologies
```

---

## Automated tests

The project uses `pytest` for automated validation (configuration in `pytest.ini`). Run the complete suite from the project root with:

```powershell
pytest -v
```

All suites run without CHELSA, CAOP, GISCO, or network access (synthetic fixtures only), except one pre-existing opt-in remote CHELSA integration check (`AQUAHUB_RUN_REMOTE_TESTS=1`, skipped by default). There is roughly one test module per `src/` module, plus `tests/test_pilot_export.py`, `tests/test_zone_overview_export.py` and `tests/test_pilot_api.py` for the interactive platform's export/API layer.

---

## Methodological documentation

Detailed methodology for the current baseline prototype is available at:

```text
docs/01_climate_baseline_methodology.md
```

The documentation records:

- climate source;
- administrative source;
- coordinate systems;
- zonal-statistics methodology;
- spatial-area validation;
- monthly climatology;
- annual climatological aggregation;
- software environment;
- methodological uncertainties;
- pending scientific decisions.

---

## Scientific status

This repository currently represents a validated methodological prototype.

The current CHELSA climatologies v2.1 workflow is being used to validate the architecture and geospatial processing methodology.

The following scientific decisions are **not yet final**:

- definitive historical climate dataset;
- definitive future climate dataset;
- selected GCMs;
- selected SSP scenarios;
- climate-normal periods;
- ensemble methodology;
- uncertainty representation;
- priority climate variables;
- bioclimatic indices;
- crop suitability thresholds;
- agroclimatic zoning methodology;
- final geographical study area;
- validation datasets;
- final platform user groups.

These decisions must be aligned with the AquaHub research team before the workflow is scaled to the complete scientific product.

---

## Important methodological distinction

The current municipality climatologies are useful for:

- statistical summaries;
- regional comparisons;
- dashboard indicators;
- interactive municipality selection;
- validation of the processing pipeline.

However, the final AquaHub climatic atlas is expected to preserve high-resolution spatial climate information.

Therefore:

```text
municipality averages
≠
final scientific raster product
```

The expected final architecture includes both:

```text
high-resolution raster information
+
administrative summaries
```

Municipality-level values represent an interaction and summarisation layer, not a replacement for the underlying ~1 km climate raster information.

---

## Next technical steps

Short-term priorities, given what is done vs. still pending confirmation from the research team (see `docs/04_roadmap_future_and_bioclimatic_indices.md` for the full phase-by-phase roadmap):

1. Receive and ingest the remaining bioclimatic-index periods (2071-2100) once the professor delivers them — `scripts/build_index_pilot_data.py` already handles this, no new code needed (see `docs/04` Phase 7).
2. Implement the whole-region zonal-statistics aggregation needed for real climate data in Castilla y León/Extremadura (their boundaries are already wired up — see `docs/03` Section 7).
3. Translate `data/processed/pilot/indices_catalog.json`'s Portuguese content (index names/formulas/references) to English — deliberately deferred, tracked in `docs/04` Phase 7.
4. Get the professor's written confirmation on the still-open questions in `docs/02` (e.g. dataset provenance, GCM count) — the platform already runs against his real delivery as a working hypothesis.

**Retired (Sept 2026):** the earlier plan to download and ensemble CHELSA v2.1 future climatologies ourselves (GCM acquisition, ensembling, anomalies, a generic GDD/Winkler cross-check) was removed from the codebase once the professor started delivering pre-computed bioclimatic indices directly (`ensemble1`) — see `docs/04` Section 1.

---

## Research principle

Raw datasets are never manually modified.

```text
data/raw/
```

contains original source data.

Any derived or transformed data must be stored under:

```text
data/processed/
```

Generated visual products should be stored under:

```text
outputs/
```

Scientific and technical methodological decisions should be documented under:

```text
docs/
```

Automated validation belongs under:

```text
tests/
```

This separation ensures:

- reproducibility;
- traceability;
- clearer scientific provenance;
- safer code refactoring;
- easier collaboration;
- easier future platform development.

The current software baseline is considered suitable for continuing the scientific development of the AquaHub climate and agroclimatic atlas after the remaining methodological decisions are confirmed with the research team.