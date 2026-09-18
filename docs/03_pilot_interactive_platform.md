# AquaHub Climate Platform

## Interactive Pilot Platform (v2 — all-zones map, per the professor's
confirmed design)

### 1. Purpose and scope

This is the first interactive deliverable of the AquaHub climate atlas: a
map-based platform, built on top of the already-validated baseline
climatology pipeline (see `docs/01_climate_baseline_methodology.md`). It
started as a Douro-only pilot, was generalised (September 2026, roadmap
Phase 10) to support any number of regions each selectable from a
dropdown, and was redesigned again (September 2026, after a meeting with
the professor) to the architecture he sketched: a single map showing all
5 intervention zones at once, clickable to open a distribution panel,
with Cultura/Índice/Período/SSP filters above the map instead of a region
dropdown. Section 6 below describes the current (v2) behaviour; earlier
sections' historical detail (v1's per-region dropdown, still how
`scripts/build_pilot_region.py` builds Portuguese zones underneath) is
kept where it remains accurate.

**Scope is deliberately limited:**

- Zones: driven by `config/climate.toml`'s `[[pilot_platform.regions]]`
  list - all 5 confirmed zones are now configured (see Section 7): Douro
  and Terras de Trás-os-Montes (built, validated against real
  CHELSA/CAOP data), Beira Interior (configured with an *inferred* NUTS
  III combination, not yet confirmed against the official AquaHub area
  definition - see Section 7), and Castilla y León/Extremadura (their
  `NUTS_ID` codes are confirmed, but there is no climate-data pipeline
  for them yet - see Section 6).
- Content: the validated historical baseline -
  `tas` (mean near-surface air temperature), CHELSA climatologies v2.1,
  1981–2010 - plus the future SSP/GCM proposal from `docs/04`
  (`config/climate.toml`'s `[future]`/`[models]`), wired into the
  Período/SSP filters even though it is **not yet confirmed by the
  research team**. The banner states this explicitly so it is never
  mistaken for a finished product.
- **Cultura and Índice are shown but disabled.** The 4 crop names are
  confirmed (`docs/04`), but the professor is calculating the
  bioclimatic index values/thresholds per crop himself and will deliver
  them to the project - inventing placeholder values ahead of that would
  repeat exactly the mistake the project's own Phase 7 redefinition
  already ruled out (see `docs/04`), so these two selects stay disabled
  until real data exists.

This is a scope decision, not an oversight: shipping a working pilot now,
honestly labelling what is real data versus what is still pending, is
more useful than blocking on unresolved decisions.

---

### 2. Why this architecture

Two decisions were made explicitly, both prioritising speed to a working
pilot over building toward the full stack sketched in `README.md`
(React/TypeScript + MapLibre + PostGIS + FastAPI):

- **Backend:** FastAPI serving pre-generated static JSON/GeoJSON files,
  not a database. At Douro's scale (19 municipalities), there is no need
  for PostGIS yet.
- **Frontend:** Leaflet + vanilla JavaScript, no build step, no framework.
  Leaflet is vendored locally under `web/vendor/leaflet/` (from the
  official npm package) rather than loaded from a CDN, so the app has no
  external JavaScript dependency at runtime — only the OpenStreetMap
  basemap tiles require internet access.

This keeps the pilot inspectable and modifiable by someone without prior
frontend experience, consistent with the project's "learn by building"
approach. It is expected to be replaced or extended once the platform's
real requirements (multi-region scale, future-scenario layers, user
accounts, etc.) are confirmed.

---

### 3. Why data preparation must run locally

This platform was built inside a cloud development session that could
not reach the CHELSA public server (`os.zhdk.cloud.switch.ch`) or
Eurostat/GISCO due to that session's network egress policy. It could
reach `pypi.org`, `registry.npmjs.org`, GitHub and Google Cloud Storage,
which is how Leaflet was vendored, but not the climate/administrative
data sources this pipeline depends on.

As a result, **the data-preparation step cannot run in that kind of
restricted cloud session** — it must run wherever `data/raw/chelsa` and
`data/raw/boundaries/Continente_CAOP2025.gpkg` are actually available
(a normal local machine, as described in `docs/01`). This is a property
of that specific session's network policy, not of the code.

---

### 4. Data flow

```text
data/raw/boundaries/Continente_CAOP2025.gpkg
data/raw/chelsa/CHELSA_tas_MM_1981-2010_V.2.1.tif  (x12)
        │
        │  scripts/build_pilot_region.py [--region <slug>]
        │  (reuses src/climate_pipeline.process_multi_nuts3_climatology,
        │   built on the already-validated regional core — see docs/01)
        ▼
data/processed/pilot/{slug}_pilot.geojson       (one pair per built PT zone)
data/processed/pilot/{slug}_pilot_meta.json
        │
        │  scripts/build_zone_overview.py [--gisco-file <path>]
        │  (dissolves each built zone's municipalities into one outline
        │   + annual mean + per-municipality values — see
        │   src/zone_overview_export.py; optionally adds Spain zone
        │   outlines from a local GISCO file, marked "built": false)
        ▼
data/processed/pilot/zones_overview.geojson
        │
        │  api/main.py (FastAPI; GET /api/pilot/zones serves the
        │  overview; GET /api/pilot/{slug}/future/... still serves
        │  per-zone future slices on demand when a built zone is
        │  clicked with a future Período/SSP selected — static file
        │  reads, no processing)
        ▼
web/index.html + web/app.js
(Cultura/Índice/Período/SSP filters + single Leaflet map showing all
 configured zones at once + click-to-select distribution panel)
```

`data/processed/pilot/` is not versioned in Git (it falls under the
existing `data/processed/` ignore rule) and must be regenerated locally.

---

### 5. Running the pilot

From the project root, with the virtual environment active and
`data/raw/` populated as described in `docs/01`:

```powershell
# 1. Generate pilot data for every configured Portuguese zone
#    (or add --region douro to build just one)
python -m scripts.build_pilot_region

# 2. Build the all-zones overview the map actually renders
#    (add --gisco-file <path> once you have the GISCO file locally,
#    to also show the Spanish zones' outlines - see Section 7)
python -m scripts.build_zone_overview

# 3. Serve the API + frontend
uvicorn api.main:app --reload

# 4. Open the platform
# http://127.0.0.1:8000
```

The map is populated from `GET /api/pilot/zones`, i.e. from step 2's
output - so re-run `build_zone_overview` after building or rebuilding any
zone with `build_pilot_region`. If `zones_overview.geojson` hasn't been
built yet, the banner says so explicitly with the exact command to run.

---

### 6. What the platform shows

- A banner with 4 filters: **Cultura** and **Índice** (populated with the
  4 confirmed crop names, but disabled - see Section 1), **Período**
  (histórico + the 3 configured future periods) and **SSP** (disabled on
  histórico; the 2 configured scenarios otherwise).
- A single Leaflet map showing every configured zone at once, each drawn
  as one dissolved outline (not subdivided by municipality) - zones with
  built climate data are coloured by their 1981–2010 annual mean
  temperature (`tas`); zones without built data yet (e.g. Castilla y
  León/Extremadura today) are drawn in a neutral dashed style and
  tooltip as "dados pendentes".
- Clicking a zone opens a side panel with:
  - the zone name and its annual mean temperature for the current
    Período/SSP selection (histórico uses the value already baked into
    `zones_overview.geojson`; a future selection fetches that zone's
    existing `/api/pilot/{slug}/future/...` slice on demand and averages
    it);
  - a smooth distribution chart (Gaussian KDE, not a bar histogram - per
    the professor's sketch) of the annual mean temperature **per
    municipality within the zone**, with a rug plot of the real
    observed values. This is explicitly labelled "provisório" in the UI:
    it is a real, non-fabricated dataset (today's per-municipality
    temperature means), used as a placeholder for whatever the
    distribution axis should actually represent once confirmed with the
    professor - not yet the same thing as a bioclimatic index
    distribution, since no index data exists yet (see Section 1).
  - for a zone with no built data, a "dados pendentes" message instead.

This intentionally mirrors the "camada científica + camada de
interação" separation already established in `docs/01` Section 20: the
underlying ~1 km raster remains the scientific product; this platform's
dissolved zone outlines are the interaction/summary layer built on top
of it.

---

### 7. Configuration

The pilot's shared settings (variable/period/dataset label) and its list
of regions are read from `config/climate.toml`, section
`[pilot_platform]`, kept separate from the existing `[pilot]` section
(which configures the future-climate experiment scaffold in
`src/future_climate_experiment.py` and is unrelated to this platform).

```toml
[pilot_platform]
variable = "tas"
period = "1981-2010"
dataset = "CHELSA climatologies v2.1"

[[pilot_platform.regions]]
slug = "douro"
label = "Douro"
nuts3_names = ["Douro"]

[[pilot_platform.regions]]
slug = "beira-interior"
label = "Beira Interior"
nuts3_names = ["Beira Baixa", "Beiras e Serra da Estrela"]   # inferred — see below
```

Each region is defined by a list of NUTS III names, not a single name,
because an AquaHub intervention area does not necessarily correspond to
one official NUTS III unit. "Douro" happens to be both the project's
area name and a literal value in CAOP2025's `nuts3` column (confirmed
against real data during Phase 1/pilot validation).

"Beira Interior" is the project's own term for an intervention area — it
is **not confirmed** to be a literal NUTS III name. Running the CAOP
query below (September 2026) confirmed that CAOP2025 uses Portugal's
**revised (2024) NUTS III classification**, which has no unit literally
named "Beira Interior": the pre-2024 units "Beira Interior Norte",
"Beira Interior Sul" and "Cova da Beira" were consolidated into "Beiras e
Serra da Estrela" and "Beira Baixa". `nuts3_names` above uses that
combination as the closest correspondence to the historical "Beira
Interior" area — this is a **geographic inference**, not a confirmed
match to the AquaHub project's actual intervention boundary, and should
be checked against the project's own area definition before being
treated as final.

**To add or fix a region:** run this once, locally, against your real
CAOP file, to see the exact `nuts3` values available, then fill in
`nuts3_names` with whichever one(s) correspond to the intervention area:

```python
import geopandas as gpd
gdf = gpd.read_file(
    "data/raw/boundaries/Continente_CAOP2025.gpkg",
    layer="cont_municipios",
)
print(sorted(gdf["nuts3"].unique()))
```

Real output from this project's CAOP2025 file (September 2026):

```text
['Alentejo Central', 'Alentejo Litoral', 'Algarve', 'Alto Alentejo',
 'Alto Minho', 'Alto Tâmega e Barroso', 'Ave', 'Baixo Alentejo',
 'Beira Baixa', 'Beiras e Serra da Estrela', 'Cávado', 'Douro',
 'Grande Lisboa', 'Lezíria do Tejo', 'Médio Tejo', 'Oeste',
 'Península de Setúbal', 'Região de Aveiro', 'Região de Coimbra',
 'Região de Leiria', 'Terras de Trás-os-Montes', 'Tâmega e Sousa',
 'Viseu Dão Lafões', 'Área Metropolitana do Porto']
```

`get_municipalities_by_nuts3_list` (`src/boundary_processing.py`)
combines multiple NUTS III names into one region; `--region <slug>` on
`scripts/build_pilot_region.py` builds just that region once its
`nuts3_names` is filled in. Castilla y León and Extremadura will
additionally require a Spanish administrative-boundary source (not part
of this codebase yet) before the same mechanism can be used for them.

**Update (Sept 2026):** the professor's sketch confirmed the platform
should show all 5 intervention zones at once (3 Portuguese NUTS III
units - Douro, Terras de Trás-os-Montes, Beira Interior - plus 2 Spanish
NUTS II units - Castilla y León, Extremadura, as whole autonomous
communities, not subdivided by municipality), clickable to drill into a
distribution chart. That is a different shape from this section's
one-region-at-a-time dropdown, and is deferred until the Spain boundary
data below is available and the zone map itself is redesigned - tracked
in `docs/04`.

The Spanish administrative-boundary source is now identified: Eurostat's
GISCO NUTS boundaries dataset (pan-European, so it uses the same NUTS
convention across Portugal and Spain - unlike CAOP, which is Portugal-
only). This sandbox's network policy cannot reach `ec.europa.eu`/GISCO
(the same restriction already described in Section 3 for CHELSA), so the
file must be downloaded locally and placed under
`data/raw/boundaries/`, the same "download locally, then process" pattern
used throughout this project.

Boundary-processing utilities for it already exist and are tested
(`src/gisco_boundary_processing.py`, `tests/test_gisco_boundary_processing.py`),
mirroring `src/boundary_processing.py`'s conventions but keyed by the
GISCO layer's `NUTS_ID` code (e.g. `"ES41"`) rather than by name, since
`NUTS_ID` is the stable Eurostat identifier and the `NUTS_NAME` column's
exact spelling can vary by file/language. Once the GISCO file is
downloaded, run this once, locally, to find the exact `NUTS_ID` codes for
Castilla y León and Extremadura:

```powershell
python -m scripts.inspect_gisco_boundaries data/raw/boundaries/<gisco-file> --country ES --level 2
```

This prints every Spanish NUTS II region's `(NUTS_ID, NUTS_NAME)` pair so
the two needed codes can be read off directly, without guessing them.
`get_regions_by_nuts_id` (`src/gisco_boundary_processing.py`) then loads
just those two regions and reprojects them to `EPSG:4326`, ready to be
wired into the zone-map redesign once that work starts. Zonal-statistics
aggregation of CHELSA rasters over these whole-region polygons (rather
than per-municipality, as Portugal's pipeline does) is not yet
implemented - that is part of the deferred zone-map work, not this
boundary-loading step.

**Update (Sept 2026):** ran against the real GISCO file
(`NUTS_RG_01M_2024_4326.gpkg`) and confirmed the exact `NUTS_ID` codes:
`ES41` (Castilla y León) and `ES43` (Extremadura). `config/climate.toml`
now lists all 5 confirmed zones under `[[pilot_platform.regions]]` -
Douro, Beira Interior and the previously-missing Terras de
Trás-os-Montes use `nuts3_names` (built by
`scripts/build_pilot_region.py` today, once CAOP/CHELSA data is
available locally); Castilla y León and Extremadura use a new
`gisco_nuts_ids` key instead, since they come from a different source
and a different aggregation (whole-region, not per-municipality) -
`scripts/build_pilot_region.py` only reads `nuts3_names`, so it skips
these two cleanly rather than mishandling them. Building real pilot
artefacts for the two Spanish zones still needs the zonal-stats
aggregation step mentioned above, not yet implemented.

---

### 8. Testing

- `tests/test_boundary_processing.py` — covers
  `get_municipalities_by_nuts3_list`, including combining multiple NUTS
  III names, case-insensitivity, missing-name errors and de-duplication.
- `tests/test_gisco_boundary_processing.py` — covers
  `get_regions_by_nuts_id`/`get_region_bounds`/`list_available_nuts_regions`
  against a synthetic GISCO-shaped GeoDataFrame.
- `tests/test_climate_pipeline.py` — covers
  `process_multi_nuts3_climatology`.
- `tests/test_pilot_export.py` — unit tests for the per-municipality
  geometry + climatology merge logic, using synthetic GeoDataFrames (no
  CHELSA/CAOP access required).
- `tests/test_zone_overview_export.py` — unit tests for dissolving a
  built zone's municipalities into one feature (geometry union +
  average + per-municipality value array) and for placeholder zones
  with/without known geometry, using synthetic pilot GeoJSON (no real
  data required).
- `tests/test_pilot_api.py` — FastAPI endpoint tests using fixture
  GeoJSON/metadata pairs written to a temporary directory (via the
  `AQUAHUB_PILOT_DATA_DIR`/`AQUAHUB_FUTURE_PILOT_DATA_DIR` environment
  variables), covering: a built region, an unconfigured region slug
  (rejected by the allow-list before any filesystem access), a
  configured-but-not-yet-built region (the build-hint path), the
  `/api/pilot` region-listing endpoint, and `/api/pilot/zones`
  (present/missing).

All suites run without CHELSA, CAOP, GISCO, or network access, and were
verified together with the full existing test suite (162 passed, 1
skipped — the skipped test is the pre-existing opt-in remote CHELSA
integration check).

The rendering itself (the all-zones map, built-vs-pending zone styling,
clicking a built zone to see its distribution chart, switching
Período/SSP and re-fetching a future slice, clicking an unbuilt zone to
see the pending-data message) was verified end-to-end with a real
FastAPI instance serving synthetic `zones_overview.geojson`/future
fixtures and a headless browser during development; those fixtures were
discarded afterwards and are not part of the repository. This does not
replace running the pipeline against real data locally.

---

### 9. Known limitations / next steps

- No future/SSP/GCM layer is confirmed by the research team yet - the
  proposal from `docs/04` (monthly CHELSA v2.1, 5 GCMs, SSP1-2.6/SSP5-8.5)
  is wired into the Período/SSP filters so the pilot is usable today, but
  is not yet approved methodology.
- No variables besides `tas` yet (`tasmin`, `tasmax`, `pr` are supported
  by the processing pipeline as of Phase 1, but not yet exported by
  `scripts/build_pilot_region.py` or shown in the UI).
- Cultura and Índice are placeholders (real crop names, disabled
  selects) - no bioclimatic index data exists yet; the professor is
  calculating it and will deliver it (see Section 1, `docs/04`).
- What the distribution chart's values should represent is not
  confirmed with the professor - today it shows the zone's real
  per-municipality annual mean temperature (historical or a future
  ensemble mean), explicitly labelled "provisório" in the UI, as a
  working placeholder until that is confirmed.
- Douro and Terras de Trás-os-Montes have real data; Beira Interior has
  an inferred (not yet officially confirmed) `nuts3_names` and no
  CHELSA/CAOP data run against it yet (see Section 7); Castilla y
  León/Extremadura have confirmed `NUTS_ID` codes and can show their
  outline on the map (via `--gisco-file`), but have no climate-data
  pipeline yet - `scripts/build_zone_overview.py` only loads their
  geometry, it does not compute a whole-region zonal statistic from
  CHELSA the way the per-municipality Portuguese pipeline does.
- No CSV/GeoTIFF export from the UI yet (raised as an open question in
  `docs/02`, item 44).
- The OpenStreetMap basemap requires internet access at runtime; the
  rest of the platform (Leaflet, the API, the data) does not.
