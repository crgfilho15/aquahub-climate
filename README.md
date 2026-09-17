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

## Interactive pilot platform (v1)

A first interactive map platform is available, built on the validated baseline climatology pipeline below, with a region selector (Douro is fully validated with real data; more regions can be added via `config/climate.toml`). It intentionally shows only the historical baseline (`tas`, 1981–2010) — future SSP/GCM scenarios are not yet included, pending methodological confirmation (a concrete proposal exists — see `docs/04_roadmap_future_and_bioclimatic_indices.md`).

Full details, architecture rationale and known limitations: `docs/03_pilot_interactive_platform.md`.

Quick start, once `data/raw/` is populated as described below:

```powershell
python -m scripts.build_pilot_region
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
├── notebooks/
│   └── 01_chelsa_exploration.ipynb
│
├── outputs/
│   ├── figures/
│   └── tables/
│
├── scripts/
│   ├── build_pilot_region.py
│   ├── build_future_climatology.py
│   ├── build_ensemble_climatology.py
│   ├── build_anomaly_climatology.py
│   └── validate_future_acquisition.py
│
├── src/
│   ├── bioclimatic_indices.py
│   ├── boundary_processing.py
│   ├── climate_acquisition.py
│   ├── climate_analysis.py
│   ├── climate_anomalies.py
│   ├── climate_config.py
│   ├── climate_ensemble.py
│   ├── climate_paths.py
│   ├── climate_pipeline.py
│   ├── climate_processing.py
│   ├── climate_region.py
│   ├── climate_selection.py
│   ├── data_io.py
│   ├── future_climate_experiment.py
│   ├── future_climate_pipeline.py
│   ├── future_climate_processing.py
│   └── pilot_export.py
│
├── web/
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   └── vendor/leaflet/
│
├── tests/
│   └── ... (one test module per src/ module, plus test_pilot_export.py and test_pilot_api.py)
│
├── pytest.ini
├── README.md
└── requirements.txt
```

---

## Environment

Current development environment:

- Windows
- Python 3.14
- VS Code
- JupyterLab
- pytest

Main Python libraries:

- pandas
- geopandas
- rasterio
- rioxarray
- exactextract
- matplotlib
- pyarrow
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

Install dependencies:

```powershell
pip install -r requirements.txt
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
process_nuts3_temperature(
    municipalities_gdf=municipalities,
    nuts3_name="Douro",
    chelsa_dir=chelsa_dir,
    period="1981-2010",
)
```

---

### `src/climate_analysis.py`

Responsible for analytical operations performed after climate processing.

Currently includes monthly temperature comparison between two regions.

The current difference convention is:

```text
second region - first region
```

Therefore:

```text
positive value
→ second region is warmer

negative value
→ first region is warmer
```

This logic has been validated with automated tests.

---

### `src/data_io.py`

Responsible for persistence of processed climate datasets.

Processed climate outputs are currently stored using:

```text
Parquet
```

The public saving functions share a common internal persistence implementation to ensure consistent file naming and output behaviour.

Current supported persistence levels include:

- individual municipality;
- arbitrary municipality batch;
- administrative region / NUTS III.

---

## Processing examples

### One municipality

Conceptually:

```python
monthly, annual = pipeline.process_municipality_temperature(
    municipalities_gdf=municipalities,
    municipality_name="Vila Real",
    chelsa_dir=chelsa_dir,
    period="1981-2010",
)
```

---

### Several municipalities

```python
monthly, annual = (
    pipeline.process_multiple_municipalities_temperature(
        municipalities_gdf=municipalities,
        municipality_names=[
            "Vila Real",
            "Bragança",
            "Chaves",
        ],
        chelsa_dir=chelsa_dir,
        period="1981-2010",
    )
)
```

The geometries are processed together using the regional processing core.

---

### NUTS III region

```python
monthly, annual = (
    pipeline.process_nuts3_temperature(
        municipalities_gdf=municipalities,
        nuts3_name="Douro",
        chelsa_dir=chelsa_dir,
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

## Processed outputs

Current individual municipality files include:

```text
data/processed/
├── braganca_tas_annual_1981-2010.parquet
├── braganca_tas_monthly_1981-2010.parquet
├── chaves_tas_annual_1981-2010.parquet
├── chaves_tas_monthly_1981-2010.parquet
├── vila_real_tas_annual_1981-2010.parquet
└── vila_real_tas_monthly_1981-2010.parquet
```

Consolidated municipality outputs include:

```text
municipalities_tas_monthly_1981-2010.parquet
municipalities_tas_annual_1981-2010.parquet
```

Regional NUTS III outputs include:

```text
nuts3_douro_tas_monthly_1981-2010.parquet
nuts3_douro_tas_annual_1981-2010.parquet
```

---

## Generated figures

Current figures include:

```text
outputs/figures/
├── vila_real_vs_braganca_tas_1981-2010.png
└── braganca_minus_vila_real_tas_1981-2010.png
```

The Vila Real vs Bragança comparison demonstrated that similar annual climatological means can hide relevant seasonal differences.

For example, the current prototype showed:

```text
winter
→ Bragança generally cooler than Vila Real

summer
→ Bragança generally warmer than Vila Real
```

The largest monthly difference observed in the current comparison was approximately:

```text
July: +1.32 °C
```

for Bragança relative to Vila Real.

The largest negative difference was approximately:

```text
January: -0.62 °C
```

---

## Automated tests

The project uses `pytest` for automated validation.

The pytest configuration is stored in:

```text
pytest.ini
```

Run the complete test suite from the project root with:

```powershell
pytest -v
```

Current test status:

```text
131 passed, 1 skipped
```

The skipped test is the pre-existing opt-in remote CHELSA integration check (`AQUAHUB_RUN_REMOTE_TESTS=1`), which requires live network access.

The current test suite covers five main modules.

### Boundary-processing tests

Validated behaviours include:

- single municipality selection;
- case-insensitive municipality searches;
- explicit errors for unknown municipalities;
- multiple-municipality selection;
- missing municipality detection;
- NUTS III municipality selection;
- CRS reprojection.

---

### Climate-processing tests

Validated behaviours include:

- annual climatological aggregation;
- multiple-region annual calculations;
- calendar-day weighting;
- protection against mixing multiple municipalities in a single-region function;
- synthetic raster processing;
- Kelvin to Celsius conversion;
- fractional pixel coverage;
- integration between Rasterio, GeoPandas and exactextract.

---

### Climate-analysis tests

Validated behaviours include:

- monthly comparison between regions;
- correct temperature-difference direction;
- rejection of DataFrames containing multiple mixed regions.

---

### Data-persistence tests

Validated behaviours include:

- municipality Parquet persistence;
- batch Parquet persistence;
- regional/NUTS III persistence;
- correct output file naming;
- data integrity after saving and reloading.

Temporary directories provided by pytest are used so artificial test outputs do not modify:

```text
data/processed/
```

---

### Climate-pipeline tests

Validated workflows include:

- individual municipality orchestration;
- multiple-municipality orchestration;
- NUTS III orchestration.

Pipeline tests use controlled mocked processing functions so they specifically test workflow coordination without repeatedly loading real CHELSA rasters.

---

## Synthetic raster integration tests

The test suite includes real small GeoTIFF files generated dynamically during testing.

One synthetic test uses:

```text
280 K | 282 K
284 K | 286 K
```

and verifies that the northern region returns:

```text
281 K
=
7.85 °C
```

This validates the integration between:

```text
Rasterio
+
GeoPandas
+
exactextract
+
temperature conversion
```

without depending on external CHELSA files.

---

## Fractional pixel coverage validation

A second synthetic raster test validates partial pixel coverage.

Example raster:

```text
280 K | 300 K
```

The test polygon covers:

```text
first pixel  → 100%
second pixel → 50%
```

Therefore, the expected weighted value is:

```text
(280 × 1.0 + 300 × 0.5) / 1.5

= 286.666666... K
```

The automated test confirms that the processing implementation reproduces this expected result.

This directly validates one of the important spatial assumptions of the AquaHub prototype:

**administrative boundaries intersecting climate raster pixels must contribute proportionally according to their covered area.**

---

## Test warnings

The current test suite may display a Rasterio warning similar to:

```text
PendingDeprecationWarning:
Use `@` matmul instead of `*` mul operator for matrix multiplication
```

The warning originates from Rasterio's internal transformation implementation and is not currently caused by AquaHub project code.

The tests still complete successfully.

Current status:

```text
21 passed
```

The warning is intentionally not suppressed at this stage.

---

## Reproducibility validation

The exploratory notebook has been validated using a clean Jupyter kernel.

Validation procedure:

```text
Restart Kernel
      ↓
Run All
      ↓
completed without errors
```

This confirms that the current notebook does not depend on hidden variables retained from previous interactive executions.

During this validation, legacy notebook calls were updated to match the current refactored APIs.

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

Short-term technical priorities include:

1. Consolidate the current documented and tested baseline.
2. Confirm the definitive historical climate dataset with the research team.
3. Confirm the definitive future climate dataset.
4. Confirm required future climate periods.
5. Confirm the Global Climate Models to be used.
6. Confirm SSP scenarios.
7. Define the multi-model ensemble methodology.
8. Define uncertainty metrics.
9. Extend the climate-processing core to additional variables.
10. Develop climate-change delta calculations.
11. Implement crop-specific bioclimatic indicators.
12. Define agroclimatic zoning rules.
13. Preserve high-resolution raster outputs for the scientific atlas.
14. Expand regional processing beyond the current Portuguese prototype.
15. Extend the interactive pilot platform (`docs/03_pilot_interactive_platform.md`) beyond the historical `tas` baseline, once the items above are confirmed. Region selection (Douro / Beira Interior / ...) is already generalised — see `docs/04_roadmap_future_and_bioclimatic_indices.md` Phase 10.

---

## Future scientific workflow

The expected longer-term climate workflow is conceptually:

```text
Historical climate
        +
Future climate scenarios
        ↓
multiple GCMs
        ↓
SSP scenarios
        ↓
climate normal periods
        ↓
multi-model ensemble
        ↓
climate-change anomalies
        ↓
bioclimatic indices
        ↓
crop-specific thresholds
        ↓
agroclimatic zoning
        ↓
interactive AquaHub platform
```

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

---

## Current prototype status

The current prototype has successfully demonstrated:

```text
CHELSA monthly climate rasters
        ↓
CAOP administrative boundaries
        ↓
CRS harmonisation
        ↓
fractional raster–polygon intersection
        ↓
area-weighted zonal statistics
        ↓
monthly municipality climatologies
        ↓
calendar-weighted annual climatologies
        ↓
single municipality processing
        ↓
multi-municipality processing
        ↓
NUTS III regional processing
        ↓
Parquet persistence
        ↓
climate comparisons
        ↓
scientific figures
        ↓
automated tests
```

The current software baseline is therefore considered suitable for continuing the scientific development of the AquaHub climate and agroclimatic atlas after the remaining methodological decisions are confirmed with the research team.