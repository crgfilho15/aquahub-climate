# AquaHub Climate Platform

## Baseline Climate Processing Methodology — Prototype v0.2

## 1. Objective

The objective of this prototype is to validate a reproducible geospatial workflow for extracting, aggregating and analysing high-resolution climate information for the AquaHub study area.

The first validation case used the municipality of Vila Real, Portugal, and near-surface mean air temperature (`tas`) for the climatological reference period 1981–2010.

The workflow was subsequently extended and validated for:

- additional municipalities;
- multiple municipalities processed simultaneously;
- complete NUTS III administrative regions;
- automated climate-data processing;
- reproducible data persistence;
- automated software and scientific validation.

The prototype is intended to validate the GIS, climate-data and software-processing workflow before scaling the methodology to:

- additional climate variables;
- future climate scenarios;
- multiple Global Climate Models (GCMs);
- Shared Socioeconomic Pathways (SSPs);
- multi-model ensembles;
- bioclimatic indices;
- crop-specific agroclimatic zoning;
- the complete AquaHub intervention area.

The current implementation must therefore be interpreted as a validated methodological baseline rather than the definitive AquaHub climate methodology.

---

## 2. Climate dataset

The current technical prototype uses:

**Dataset:**

CHELSA climatologies v2.1

**Variable:**

`tas` — Daily Mean Near-Surface Air Temperature

**Reference period:**

1981–2010

**Temporal resolution:**

Monthly climatologies

**Spatial reference system:**

EPSG:4326

**Spatial resolution:**

Approximately 1 km.

The CHELSA raster grid corresponds approximately to 30 arc-seconds, or about:

```text
0.008333° × 0.008333°
```

The physical ground resolution varies with latitude.

**Original unit:**

Kelvin (K)

**Raster format:**

Cloud Optimized GeoTIFF (COG)

The current raster filenames follow the pattern:

```text
CHELSA_tas_MM_1981-2010_V.2.1.tif
```

where `MM` represents the month from `01` to `12`.

The temperature rasters contain a scale factor of:

```text
0.1
```

When values are accessed directly using Rasterio:

```text
real_value = raw_value × scale + offset
```

Temperature values are subsequently converted from Kelvin to Celsius:

```text
temperature_C = temperature_K - 273.15
```

When using `exactextract`, raster scale and offset metadata are automatically applied before the zonal statistic is calculated.

This behaviour was verified during the exploratory phase to avoid applying the scale factor twice.

---

## 3. Administrative boundaries

Administrative boundaries were obtained from:

**CAOP2025 — Carta Administrativa Oficial de Portugal**

Dataset:

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
- number of parishes;
- municipality geometry.

The original coordinate reference system is:

```text
EPSG:3763
ETRS89 / Portugal TM06
```

For intersection with CHELSA climate rasters, administrative geometries are reprojected to:

```text
EPSG:4326
```

### Initial validation municipality

The first municipality used to validate the methodology was:

**Vila Real**

Administrative information:

- District: Vila Real
- NUTS III: Douro
- NUTS II: Norte
- Official area: 37,880.28 ha
- Number of parishes: 20

The approximate EPSG:4326 bounding box obtained for Vila Real was:

```text
min longitude: -7.92136692
min latitude:   41.17968515
max longitude: -7.60029964
max latitude:   41.42152517
```

---

## 4. Spatial processing

The CHELSA raster is not reduced to a single point representing a municipality.

The complete administrative polygon is used.

The basic workflow is:

```text
CHELSA raster
      ↓
administrative polygon
      ↓
spatial intersection
      ↓
fractional pixel coverage
      ↓
area-weighted zonal statistics
      ↓
municipality climate value
```

The zonal statistic is calculated using:

```text
exactextract
```

Pixel contributions along administrative boundaries are weighted according to the fraction of each raster cell covered by the polygon.

The current area-weighting configuration uses:

```python
coverage_weight=area_spherical_m2
```

This prevents a partially intersected boundary pixel from being treated as if the complete raster cell belonged to the municipality.

Conceptually:

```text
100% pixel coverage
→ full contribution

50% pixel coverage
→ proportional contribution

10% pixel coverage
→ proportional contribution
```

This behaviour is particularly important for administrative boundaries, which generally do not coincide with the CHELSA raster grid.

---

## 5. Spatial validation

The official CAOP area of Vila Real is:

```text
37,880.28 ha
```

The area represented during the raster/polygon processing was approximately:

```text
37,912.31 ha
```

The difference is approximately:

```text
0.085%
```

This small difference was considered coherent for the current prototype and indicates consistency between:

- the CAOP administrative geometry;
- the EPSG:4326 reprojection;
- the CHELSA raster grid;
- the spherical area weighting used by `exactextract`.

This comparison is used as a methodological sanity check rather than as a replacement for the official CAOP area.

---

## 6. Monthly climatology

The area-weighted monthly mean temperatures obtained for Vila Real for 1981–2010 are:

| Month | Mean temperature (°C) |
|---|---:|
| January | 5.277 |
| February | 6.500 |
| March | 8.983 |
| April | 10.039 |
| May | 12.907 |
| June | 17.161 |
| July | 19.454 |
| August | 19.433 |
| September | 16.925 |
| October | 12.690 |
| November | 8.526 |
| December | 6.116 |

The monthly climatology preserves the seasonal behaviour that would be hidden if only the annual mean were presented.

---

## 7. Annual climatological mean

The annual temperature is not calculated using a simple arithmetic mean of the twelve monthly climatologies.

Monthly climatologies are weighted according to the actual number of calendar days represented during the complete 1981–2010 period.

The exact number of represented days per month is:

| Month | Days represented in 1981–2010 |
|---|---:|
| January | 930 |
| February | 847 |
| March | 930 |
| April | 900 |
| May | 930 |
| June | 900 |
| July | 930 |
| August | 930 |
| September | 900 |
| October | 930 |
| November | 900 |
| December | 930 |

Total:

```text
10,957 days
```

The resulting annual climatological mean temperature for Vila Real is:

**12.029871 °C**

The difference between this exact calendar-weighted calculation and a simplified weighting using a standard 365-day year was approximately:

```text
-0.0035 °C
```

Although small in this case, the exact calendar-based approach was retained for methodological consistency and reproducibility.

---

## 8. Additional municipality validation

After Vila Real, the same climate-processing methodology was applied without municipality-specific scientific logic to additional municipalities.

Validated annual climatologies include:

| Municipality | Mean annual temperature (°C) |
|---|---:|
| Vila Real | 12.029871 |
| Bragança | 12.178043 |
| Chaves | 12.865129 |

These results demonstrated that the workflow could be generalised to different administrative units using the same processing core.

### Vila Real × Bragança monthly comparison

A monthly comparison between Vila Real and Bragança demonstrated that similar annual means may hide relevant seasonal differences.

The comparison uses:

```text
Bragança - Vila Real
```

Interpretation:

```text
positive difference
→ Bragança warmer

negative difference
→ Vila Real warmer
```

The observed pattern was approximately:

```text
winter
→ Bragança cooler

spring
→ transition

summer
→ Bragança warmer

autumn
→ differences decrease and reverse
```

The largest positive monthly difference was approximately:

```text
July: +1.318 °C
```

The largest negative monthly difference was approximately:

```text
January: -0.622 °C
```

This confirms that annual summaries should not replace monthly or seasonal climate information in the future AquaHub platform.

---

## 9. Regional processing strategy

The initial prototype processed one municipality at a time.

The methodology was subsequently refactored into a regional-first processing strategy.

Instead of processing all twelve rasters separately for each municipality:

```text
municipality 1
→ January
→ February
→ ...
→ December

municipality 2
→ January
→ February
→ ...
→ December
```

the current processing core follows:

```text
January raster
→ all selected municipalities

February raster
→ all selected municipalities

...

December raster
→ all selected municipalities
```

This strategy reduces unnecessary repeated raster-processing operations and is more appropriate for scaling the workflow to complete administrative regions.

The scientific core is therefore based on multi-region processing.

Single-municipality functions are retained as compatibility interfaces but internally delegate to the same regional processing functions.

This means:

```text
single municipality
        ┐
        ├── same regional scientific core
multiple municipalities
        ┘
```

This refactoring reduces duplicated scientific logic and helps prevent different processing paths from producing inconsistent results.

---

## 10. NUTS III validation

The regional workflow was validated using:

**NUTS III Douro**

Using CAOP2025, the system automatically identified:

```text
19 municipalities
```

The municipalities identified were:

- Alijó
- Armamar
- Carrazeda de Ansiães
- Freixo de Espada à Cinta
- Lamego
- Mesão Frio
- Moimenta da Beira
- Murça
- Penedono
- Peso da Régua
- Sabrosa
- Santa Marta de Penaguião
- Sernancelhe
- São João da Pesqueira
- Tabuaço
- Tarouca
- Torre de Moncorvo
- Vila Nova de Foz Côa
- Vila Real

For the 1981–2010 temperature climatology:

```text
19 municipalities
×
12 months
=
228 monthly municipality records
```

The annual aggregation produced:

```text
19 annual municipality climatologies
```

Vila Real was used as a reference to compare the regional workflow against the previously validated individual workflow.

The observed differences were:

```text
Maximum monthly difference:
0.0000000000 °C

Annual difference:
0.0000000000 °C
```

This confirms numerical consistency between individual and regional processing.

---

## 11. Software architecture

The current prototype uses a modular architecture.

### `src/boundary_processing.py`

Responsible for administrative geometry selection and preparation.

Current responsibilities include:

- selecting a single municipality;
- selecting multiple municipalities by name;
- selecting municipality names belonging to a NUTS III;
- selecting complete municipality geometries belonging to a NUTS III;
- case-insensitive administrative searches;
- missing administrative-unit validation;
- CRS reprojection.

Main functions include:

```python
get_municipality_geometry(...)
get_municipalities_by_names(...)
get_municipality_names_by_nuts3(...)
get_municipalities_by_nuts3(...)
```

---

### `src/climate_processing.py`

Contains the scientific climate-processing core.

Responsibilities include:

- raster zonal statistics;
- fractional pixel coverage;
- area-weighted means;
- Kelvin-to-Celsius conversion;
- monthly climatology;
- calendar-weighted annual climatology;
- individual-region compatibility interfaces;
- multiple-region processing.

The regional functions now represent the primary scientific implementation.

Legacy single-region functions remain available as wrappers to preserve compatibility with existing notebook calls.

**Multi-variable core (September 2026):** the processing core was generalised beyond `tas`. `calculate_monthly_value_for_regions`, `calculate_monthly_climatology_for_regions`, `calculate_annual_climatology_for_regions` and `process_climatology_for_regions` accept any CHELSA variable registered in `CHELSA_VARIABLE_UNITS` (currently `tas`, `tasmin`, `tasmax`, `pr`), applying the correct unit conversion for each (Kelvin → Celsius for temperature variables; no conversion for precipitation, already delivered in mm). The original `tas`-specific functions (`calculate_monthly_temperature_for_regions`, `process_temperature_climatology_for_regions`, etc.) are unchanged in signature and behaviour — they are now thin wrappers around this generic core, so existing notebook cells, the pilot export pipeline and existing tests did not need to change. See `docs/04_roadmap_future_and_bioclimatic_indices.md` Phase 1.

---

### `src/climate_pipeline.py`

Coordinates higher-level workflows.

Current supported workflows include:

```text
single municipality
```

```text
arbitrary municipality list
```

and:

```text
complete NUTS III
```

A NUTS III workflow conceptually performs:

```text
NUTS III name
      ↓
CAOP municipality selection
      ↓
geometry reprojection
      ↓
12 CHELSA rasters
      ↓
multi-region zonal statistics
      ↓
monthly climatologies
      ↓
annual climatologies
```

Each workflow also has a generic, variable-parameterised counterpart (`process_municipality_climatology`, `process_multiple_municipalities_climatology`, `process_nuts3_climatology`), which accepts any variable from `CHELSA_VARIABLE_UNITS` instead of being fixed to `tas`. The `_temperature` functions above are unchanged and now call the same underlying generic processing core with `variable="tas"`.

---

### `src/climate_analysis.py`

Responsible for analytical operations after climate processing.

The current implementation includes monthly temperature comparison between two regions.

The temperature-difference convention is:

```text
second region - first region
```

---

### `src/data_io.py`

Responsible for persistence of processed datasets.

The current processed-data format is:

```text
Parquet
```

The public persistence functions use a common internal saving implementation to reduce duplicated file-writing logic.

Current persistence levels include:

- individual municipality;
- municipality batch;
- NUTS III regional result.

---

## 12. Software environment

The current development and processing environment includes:

- Windows
- Python 3.14
- VS Code
- JupyterLab
- Pandas
- GeoPandas
- Rasterio
- Rioxarray
- exactextract
- Matplotlib
- PyArrow
- pytest

The environment dependencies are recorded in:

```text
requirements.txt
```

The project uses a dedicated virtual environment:

```text
.venv/
```

---

## 13. Processed outputs

Processed results are stored in:

```text
data/processed/
```

### Individual municipality outputs

Current files include:

```text
vila_real_tas_monthly_1981-2010.parquet
vila_real_tas_annual_1981-2010.parquet

braganca_tas_monthly_1981-2010.parquet
braganca_tas_annual_1981-2010.parquet

chaves_tas_monthly_1981-2010.parquet
chaves_tas_annual_1981-2010.parquet
```

### Consolidated municipality outputs

```text
municipalities_tas_monthly_1981-2010.parquet
municipalities_tas_annual_1981-2010.parquet
```

### NUTS III Douro outputs

```text
nuts3_douro_tas_monthly_1981-2010.parquet
nuts3_douro_tas_annual_1981-2010.parquet
```

A consistent filename convention is currently used:

```text
dataset_variable_temporal-resolution_period.parquet
```

The climatological period is represented using a hyphen:

```text
1981-2010
```

rather than:

```text
1981_2010
```

Older prototype files using the underscore convention were removed.

---

## 14. Generated visual outputs

Current climate figures are stored in:

```text
outputs/figures/
```

Generated figures include:

```text
vila_real_vs_braganca_tas_1981-2010.png
```

and:

```text
braganca_minus_vila_real_tas_1981-2010.png
```

Figures are currently exported at:

```text
300 dpi
```

for high-quality scientific and reporting use.

---

## 15. Automated validation

The prototype includes an automated test suite implemented with:

```text
pytest
```

Current validated status:

```text
21 tests passed
```

The test suite covers:

### Administrative geometry

- municipality selection;
- case-insensitive lookup;
- unknown municipality detection;
- multiple municipality selection;
- missing requested municipalities;
- NUTS III selection;
- CRS reprojection.

### Climate processing

- annual climatological aggregation;
- multiple-region annual aggregation;
- calendar-day weighting;
- invalid multi-region input in single-region interfaces;
- Kelvin-to-Celsius conversion;
- synthetic raster processing;
- fractional pixel coverage.

### Climate analysis

- monthly regional comparison;
- temperature-difference direction;
- mixed-region input protection.

### Data persistence

- municipality Parquet persistence;
- batch persistence;
- regional persistence;
- output filename conventions;
- data integrity after writing and reading.

### Pipeline orchestration

- municipality workflow;
- multiple-municipality workflow;
- NUTS III workflow.

---

## 16. Synthetic raster validation

The automated test suite includes synthetic GeoTIFF datasets with known values.

This enables the scientific raster-processing logic to be validated independently from the external CHELSA files.

One synthetic raster contains:

```text
280 K | 282 K
284 K | 286 K
```

A polygon covering the northern row should produce:

```text
(280 + 282) / 2
=
281 K
```

Converted to Celsius:

```text
281 - 273.15
=
7.85 °C
```

The implemented processing reproduced this expected result.

This test validates the integration between:

```text
Rasterio
+
GeoPandas
+
exactextract
+
Kelvin-to-Celsius conversion
```

---

## 17. Fractional pixel coverage validation

An additional synthetic raster test validates the treatment of partially intersected pixels.

Synthetic raster:

```text
280 K | 300 K
```

The artificial polygon covers:

```text
100% of the first pixel
50% of the second pixel
```

The expected weighted mean is:

```text
(280 × 1.0 + 300 × 0.5) / 1.5
```

which gives:

```text
286.666666... K
```

The automated test reproduced the expected result.

This provides an explicit automated validation of the fractional pixel methodology used for real administrative boundaries.

---

## 18. Reproducibility validation

The complete exploratory notebook was tested from a clean Jupyter environment.

Validation procedure:

```text
Restart Kernel
      ↓
Run All
```

The complete notebook executed successfully without errors after outdated calls from earlier prototype stages were updated.

This confirms that the current workflow does not depend on hidden variables remaining from previous interactive executions.

The main exploratory notebook is:

```text
notebooks/01_chelsa_exploration.ipynb
```

---

## 19. Data-management principles

Original datasets must not be manually modified.

Raw source data are stored under:

```text
data/raw/
```

Current structure:

```text
data/raw/
├── chelsa/
└── boundaries/
```

Derived datasets must be stored under:

```text
data/processed/
```

Scientific figures are stored under:

```text
outputs/figures/
```

Tabular reporting outputs may be stored under:

```text
outputs/tables/
```

Methodological documentation is stored under:

```text
docs/
```

Automated tests are stored under:

```text
tests/
```

This separation supports:

- reproducibility;
- traceability;
- scientific provenance;
- safer code refactoring;
- collaborative development.

---

## 20. Important spatial interpretation

Municipality-level climate averages are useful for:

- interactive municipality selection;
- dashboards;
- statistical summaries;
- comparison between territories;
- reporting;
- administrative indicators.

However:

```text
municipality mean
≠
high-resolution climate map
```

The AquaHub project requires a high-spatial-resolution climate and agroclimatic atlas.

Therefore, the municipality-level workflow developed in the current prototype should be interpreted primarily as:

```text
interaction layer
+
summary layer
+
validation layer
```

The future scientific product must preserve the underlying approximately 1 km climate information.

The expected architecture is therefore:

```text
high-resolution climate raster
        +
administrative summaries
```

The raster layer will be particularly important for:

- spatial climate patterns;
- crop-specific bioclimatic indices;
- climate-change anomalies;
- agroclimatic zoning;
- suitability mapping.

---

## 21. Current methodological status

The current workflow represents a technically and scientifically validated prototype for:

```text
CHELSA climatologies v2.1
+
tas
+
1981–2010
+
CAOP2025
+
municipality polygons
+
area-weighted zonal statistics
+
monthly climatologies
+
calendar-weighted annual climatologies
+
regional processing
```

The use of CHELSA climatologies v2.1 as the definitive AquaHub historical climate dataset has **not yet been confirmed**.

Therefore, the current implementation validates the processing methodology and software architecture rather than fixing the final climate-data source.

The workflow currently validates:

- raster processing;
- coordinate reference systems;
- administrative geometries;
- fractional raster intersections;
- spatial aggregation;
- climatological aggregation;
- municipality processing;
- regional processing;
- reproducible output persistence;
- automated scientific validation.

These components remain useful even if the definitive climate dataset changes.

---

## 22. Pending methodological decisions

The following decisions must still be confirmed with the AquaHub research team.

### Historical climate

- definitive historical dataset;
- reference climatological period;
- validation/reference datasets.

### Future climate

- definitive future climate dataset;
- GCM selection;
- SSP selection;
- medium-term period;
- long-term period;
- bias-adjustment requirements.

### Multi-model processing

- ensemble methodology;
- ensemble mean or median;
- uncertainty representation;
- percentiles or model spread;
- whether individual GCMs should remain accessible.

### Climate variables

Priority variables may include, depending on the final methodology:

- mean temperature;
- minimum temperature;
- maximum temperature;
- precipitation;
- evapotranspiration;
- additional water-balance variables.

The definitive variable list is not yet fixed.

### Bioclimatic indicators

The following still require scientific definition:

- crop-specific indices;
- formulas;
- temporal windows;
- threshold values;
- suitability classes.

### Crops

The project documentation indicates potential focus on crops such as:

- vineyard;
- olive;
- almond;
- cherry.

The exact index and threshold methodology for each crop still requires confirmation.

### Agroclimatic zoning

The following remain to be defined:

- zoning methodology;
- classification rules;
- suitability thresholds;
- combination of climate indicators;
- agricultural land masks;
- representation of uncertainty.

### Geographic extent

The complete AquaHub intervention area includes regions in Portugal and Spain.

The final processing extent and responsibilities must still be confirmed for:

- Trás-os-Montes e Alto Douro;
- Beira Interior;
- Castilla y León;
- Extremadura.

---

## 23. Methodological relationship with future climate scenarios

The current baseline workflow establishes the processing structure that can later be extended to climate-change scenarios.

A possible future conceptual workflow is:

```text
historical climate
        +
future climate
        ↓
GCM
        ↓
SSP
        ↓
future climatological period
        ↓
climate indicators
        ↓
multi-model ensemble
        ↓
climate-change anomaly
        ↓
bioclimatic indices
        ↓
crop-specific zoning
```

However, future climate-data processing should not be implemented at scale until the definitive dataset, GCMs, SSPs and climatological periods are confirmed by the research team.

---

## 24. Current prototype achievements

The current baseline prototype has demonstrated the complete chain:

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
Kelvin-to-Celsius conversion
        ↓
monthly climatologies
        ↓
calendar-weighted annual climatologies
        ↓
single-municipality processing
        ↓
multi-municipality processing
        ↓
NUTS III processing
        ↓
Parquet persistence
        ↓
climate comparisons
        ↓
scientific figures
        ↓
automated validation
        ↓
clean-kernel reproducibility validation
```

The current software baseline is therefore considered sufficiently validated to support the next scientific development stage of the AquaHub climate and agroclimatic atlas.

---

## 25. Next scientific development stage

Before substantially expanding the codebase, the next stage should prioritise methodological alignment with the AquaHub research team.

The immediate scientific questions are:

1. Which historical climate dataset should be considered definitive?
2. Which future climate dataset should be used?
3. Which GCMs should be included?
4. Which SSP scenarios should be included?
5. Which historical and future climatological periods should be presented?
6. How should the multi-model ensemble be calculated?
7. How should model uncertainty be represented?
8. Which climate variables are required?
9. Which bioclimatic indices are required for each crop?
10. Which thresholds define agroclimatic suitability?
11. Which geographic units should be available in the interactive platform?
12. Which high-resolution raster products must be generated and preserved?
13. Which outputs must be available for researchers, farmers and public institutions?

Once these decisions are confirmed, the existing processing architecture can be extended while preserving the validated spatial and computational methodology.