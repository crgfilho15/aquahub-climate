# AquaHub Climate Platform

## Interactive Pilot Platform — Douro (v1)

### 1. Purpose and scope

This is the first interactive deliverable of the AquaHub climate atlas: a
map-based platform for the Douro NUTS III region, built on top of the
already-validated baseline climatology pipeline (see
`docs/01_climate_baseline_methodology.md`).

**Scope of this v1 is deliberately limited:**

- Region: Douro NUTS III (19 municipalities) only. The architecture is
  built to extend to Beira Interior, Castilla y León and Extremadura once
  the Douro pilot is validated, but no other region is wired up yet.
- Content: the validated historical baseline only —
  `tas` (mean near-surface air temperature), CHELSA climatologies v2.1,
  1981–2010.
- **Future climate scenarios (SSP/GCM) are intentionally not included.**
  The future dataset, GCM set and required temporal resolution
  (monthly vs daily, needed for frost/GDD indices) are still open
  questions for the research team — see
  `docs/02_methodological_questions_for_team.md`. The platform's banner
  displays this limitation explicitly so it is never mistaken for a
  finished product.

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
        │  scripts/build_pilot_douro.py
        │  (reuses src/climate_pipeline.process_nuts3_temperature,
        │   already validated — see docs/01)
        ▼
data/processed/pilot/douro_pilot.geojson
data/processed/pilot/douro_pilot_meta.json
        │
        │  api/main.py (FastAPI, static file read, no processing)
        ▼
web/index.html + web/app.js (Leaflet choropleth + per-municipality panel)
```

`data/processed/pilot/` is not versioned in Git (it falls under the
existing `data/processed/` ignore rule) and must be regenerated locally.

---

### 5. Running the pilot

From the project root, with the virtual environment active and
`data/raw/` populated as described in `docs/01`:

```powershell
# 1. Generate the pilot dataset (reads data/raw, writes data/processed/pilot)
python -m scripts.build_pilot_douro

# 2. Serve the API + frontend
uvicorn api.main:app --reload

# 3. Open the platform
# http://127.0.0.1:8000
```

If step 2 is run before step 1, the API returns a `404` with an explicit
hint to run the build script first, and the banner in the UI shows the
same message instead of failing silently.

---

### 6. What the platform shows

- A Leaflet map of the 19 Douro municipalities, coloured by
  1981–2010 annual mean temperature (`tas`).
- Clicking a municipality opens a panel with:
  - the municipality name and annual mean temperature;
  - a monthly climatology chart (12 points, drawn as inline SVG, no
    charting library dependency);
  - the dataset source and variable.
- A banner stating the dataset, variable, period, methodology status
  (`provisional`, from `config/climate.toml`), and the future-scenario
  limitation described in Section 1.

This intentionally mirrors the "camada científica + camada de
interação" separation already established in `docs/01` Section 20: the
underlying ~1 km raster remains the scientific product; this platform's
municipality polygons are the interaction/summary layer built on top of
it.

---

### 7. Configuration

The pilot's region/variable/period are read from `config/climate.toml`,
section `[pilot_platform]`, kept separate from the existing `[pilot]`
section (which configures the future-climate experiment scaffold in
`src/future_climate_experiment.py` and is unrelated to this platform).

```toml
[pilot_platform]
region_type = "NUTS3"
region_name = "Douro"
variable = "tas"
period = "1981-2010"
dataset = "CHELSA climatologies v2.1"
```

Changing `region_name` alone is not sufficient to point the pilot at a
different region yet: `scripts/build_pilot_douro.py` currently assumes
Douro-shaped municipality data from the Portuguese CAOP layer. Extending
to Beira Interior (still Portugal/CAOP) should work with only a
`region_name` change; extending to Castilla y León or Extremadura will
additionally require a Spanish administrative-boundary source, which is
not wired up yet.

---

### 8. Testing

- `tests/test_pilot_export.py` — unit tests for the geometry +
  climatology merge logic, using synthetic GeoDataFrames (no CHELSA/CAOP
  access required).
- `tests/test_pilot_api.py` — FastAPI endpoint tests using a fixture
  GeoJSON/metadata pair written to a temporary directory (via the
  `AQUAHUB_PILOT_DATA_DIR` environment variable), covering both the
  success path and the "data not generated yet" `404` path.

Both suites run without CHELSA, CAOP, or network access, and were
verified together with the full existing test suite (78 passed, 1
skipped — the skipped test is the pre-existing opt-in remote CHELSA
integration check) before this platform was added.

The rendering itself (map, choropleth colouring, click interaction,
chart) was verified with a temporary synthetic fixture and a headless
browser during development; that fixture was discarded afterwards and is
not part of the repository. It does not replace running the pipeline
against real Douro data locally.

---

### 9. Known limitations / next steps

- No future/SSP/GCM layer yet — blocked on the open questions in
  `docs/02_methodological_questions_for_team.md`.
- No variables besides `tas` yet (`tasmin`, `tasmax`, `pr` are configured
  in `climate.toml` but not yet exported by
  `scripts/build_pilot_douro.py`).
- No bioclimatic indices or agroclimatic zoning layer yet.
- Single region (Douro) only; Beira Interior, Castilla y León and
  Extremadura are not yet wired up (see Section 7).
- No CSV/GeoTIFF export from the UI yet (raised as an open question in
  `docs/02`, item 44).
- The OpenStreetMap basemap requires internet access at runtime; the
  rest of the platform (Leaflet, the API, the data) does not.
