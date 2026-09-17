# AquaHub Climate Platform

## Interactive Pilot Platform (v1 — historical baseline, multi-region)

### 1. Purpose and scope

This is the first interactive deliverable of the AquaHub climate atlas: a
map-based platform, built on top of the already-validated baseline
climatology pipeline (see `docs/01_climate_baseline_methodology.md`). It
started as a Douro-only pilot and was generalised (September 2026,
roadmap Phase 10) to support any number of regions, each selectable from
a dropdown in the UI.

**Scope of this v1 is deliberately limited:**

- Regions: driven by `config/climate.toml`'s `[[pilot_platform.regions]]`
  list. Douro (19 municipalities) is fully configured and validated
  against real CHELSA/CAOP data. Beira Interior is configured with an
  *inferred* NUTS III combination (not yet confirmed against the
  official AquaHub area definition — see Section 7) and has not been
  built yet (no CHELSA/CAOP data available in this session). Castilla y
  León and Extremadura are not wired up: they need a Spanish
  administrative-boundary source, which does not exist in this codebase
  yet.
- Content: the validated historical baseline only —
  `tas` (mean near-surface air temperature), CHELSA climatologies v2.1,
  1981–2010.
- **Future climate scenarios (SSP/GCM) are intentionally not included.**
  A concrete proposal now exists (monthly CHELSA v2.1 future
  climatologies, the 5 standard GCMs — see `config/climate.toml`
  `[future]`/`[models]` and `docs/04`), but it is **not yet confirmed by
  the research team**, so it is not implemented in this platform. The
  platform's banner displays this limitation explicitly so it is never
  mistaken for a finished product.

This is a scope decision, not an oversight: shipping a working historical
pilot now is more useful than blocking on unresolved future-scenario
decisions.

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
data/processed/pilot/{slug}_pilot.geojson       (one pair per region)
data/processed/pilot/{slug}_pilot_meta.json
        │
        │  api/main.py (FastAPI; /api/pilot lists built regions,
        │  /api/pilot/{slug} and /api/pilot/{slug}/meta serve them —
        │  static file reads, no processing)
        ▼
web/index.html + web/app.js
(region <select> + Leaflet choropleth + per-municipality panel)
```

`data/processed/pilot/` is not versioned in Git (it falls under the
existing `data/processed/` ignore rule) and must be regenerated locally.

---

### 5. Running the pilot

From the project root, with the virtual environment active and
`data/raw/` populated as described in `docs/01`:

```powershell
# 1. Generate pilot data for every configured region
#    (or add --region douro to build just one)
python -m scripts.build_pilot_region

# 2. Serve the API + frontend
uvicorn api.main:app --reload

# 3. Open the platform
# http://127.0.0.1:8000
```

The UI's region dropdown is populated from `GET /api/pilot`, which only
lists regions that are both configured in `climate.toml` and have been
built — so a configured-but-not-yet-built region (e.g. Beira Interior
today) simply doesn't appear as an option, rather than showing a broken
one. If no region has been built yet, the banner says so explicitly with
the exact command to run.

---

### 6. What the platform shows

- A region selector (top-right of the banner), populated from whichever
  pilot datasets have actually been built.
- A Leaflet map of the selected region's municipalities, coloured by
  1981–2010 annual mean temperature (`tas`).
- Clicking a municipality opens a panel with:
  - the municipality name and annual mean temperature;
  - a monthly climatology chart (12 points, drawn as inline SVG, no
    charting library dependency) with a hover/keyboard-accessible
    crosshair tooltip;
  - the dataset source and variable.
- A banner stating the region, dataset, variable, period, methodology
  status (`provisional`, from `config/climate.toml`), and the
  future-scenario limitation described in Section 1.

This intentionally mirrors the "camada científica + camada de
interação" separation already established in `docs/01` Section 20: the
underlying ~1 km raster remains the scientific product; this platform's
municipality polygons are the interaction/summary layer built on top of
it.

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

---

### 8. Testing

- `tests/test_boundary_processing.py` — covers
  `get_municipalities_by_nuts3_list`, including combining multiple NUTS
  III names, case-insensitivity, missing-name errors and de-duplication.
- `tests/test_climate_pipeline.py` — covers
  `process_multi_nuts3_climatology`.
- `tests/test_pilot_export.py` — unit tests for the geometry +
  climatology merge logic, using synthetic GeoDataFrames (no CHELSA/CAOP
  access required).
- `tests/test_pilot_api.py` — FastAPI endpoint tests using fixture
  GeoJSON/metadata pairs written to a temporary directory (via the
  `AQUAHUB_PILOT_DATA_DIR` environment variable), covering: a built
  region, an unconfigured region slug (rejected by the allow-list before
  any filesystem access), a configured-but-not-yet-built region (the
  build-hint path), and the `/api/pilot` region-listing endpoint.

All suites run without CHELSA, CAOP, or network access, and were
verified together with the full existing test suite (96 passed, 1
skipped — the skipped test is the pre-existing opt-in remote CHELSA
integration check).

The rendering itself (map, choropleth colouring, click interaction,
chart, and — for the multi-region generalisation — actually switching
the dropdown between two regions with different synthetic data and
confirming the map/legend/banner all update) was verified with temporary
synthetic fixtures and a headless browser during development; those
fixtures were discarded afterwards and are not part of the repository.
This does not replace running the pipeline against real data locally.

---

### 9. Known limitations / next steps

- No future/SSP/GCM layer yet — blocked on the open questions in
  `docs/02_methodological_questions_for_team.md`. A concrete proposal
  (monthly CHELSA v2.1, 5 GCMs) is recorded in `config/climate.toml` and
  `docs/04`, pending professor confirmation.
- No variables besides `tas` yet (`tasmin`, `tasmax`, `pr` are supported
  by the processing pipeline as of Phase 1, but not yet exported by
  `scripts/build_pilot_region.py` or shown in the UI).
- No bioclimatic indices or agroclimatic zoning layer yet.
- Douro is the only region with real data; Beira Interior has an
  inferred (not yet officially confirmed) `nuts3_names` and no CHELSA/
  CAOP data run against it yet (see Section 7); Castilla y León and
  Extremadura need a Spanish boundary source that doesn't exist in this
  codebase yet.
- No CSV/GeoTIFF export from the UI yet (raised as an open question in
  `docs/02`, item 44).
- The OpenStreetMap basemap requires internet access at runtime; the
  rest of the platform (Leaflet, the API, the data) does not.
