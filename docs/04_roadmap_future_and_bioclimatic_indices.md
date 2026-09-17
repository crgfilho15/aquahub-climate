# AquaHub Climate Platform

## Roadmap — Future Scenarios & Crop-Specific Bioclimatic Indices

### 0. Where we are today

Validated and shipped (v1, `docs/03_pilot_interactive_platform.md`):

- Historical baseline pipeline (`tas`, CHELSA climatologies v2.1, 1981–2010),
  validated for Douro's 19 municipalities.
- Interactive pilot platform (map + monthly chart with hover tooltip) showing
  that baseline for Douro only.
- A future-scenario scaffold that resolves configuration and geographic
  extent, but does **not** yet fetch or process any future/GCM data:
  `climate_config.py`, `climate_selection.py`, `climate_region.py`,
  `climate_paths.py`, `future_climate_experiment.py`. `climate_acquisition.py`
  currently only fetches the **historical** CHELSA climatology endpoint.
- `config/climate.toml` already encodes a provisional methodology (historical
  = CHELSA-W5E5 1981–2010; future = CHELSA-climatologies-v2.1-CMIP6 /
  ISIMIP3b; periods 2011–2040 / 2041–2070 / 2071–2100; scenarios SSP1-2.6 /
  SSP3-7.0 / SSP5-8.5; ensemble = equal-weight mean with min/max/std
  uncertainty; GCM list intentionally empty).

Not yet true, and important to say plainly:

- The climate-processing core (`climate_processing.py`) is hardcoded to
  `tas` in three places (the raster filename pattern and two `variable =
  "tas"` assignments) — extending to `tasmin`, `tasmax`, `pr` requires a
  refactor, not just new downloads.
- No bioclimatic index has been implemented yet.
- No future/GCM data has been downloaded or processed.

---

### 1. Two tracks, and why they're separate

**Track A — decisions that only the professor/research team can make.**
No amount of engineering resolves these; coding ahead of them risks building
the wrong thing twice.

**Track B — engineering that can proceed now**, because it does not depend
on which GCM or which exact future dataset ends up confirmed.

Track B is scoped so it stays useful regardless of how Track A resolves —
e.g. generalising the pipeline to `tasmin`/`tasmax`/`pr` is needed whichever
future dataset is chosen.

---

### 2. Track A — decisions needed from the professor

In priority order (blocks the most downstream work first):

| # | Decision | Why it blocks engineering | Status |
|---|---|---|---|
| 1 | **Daily vs. monthly future data.** Is the intended future dataset CHELSA-ISIMIP3b (daily, used by MONTEVITIS) or the CHELSA v2.1 future climatologies (monthly)? | Frost days, GDD, chilling hours and most bioclimatic indices need daily data. Building the acquisition layer against the wrong product means rebuilding it. | **Proposal drafted (Sept 2026): monthly.** Recorded in `config/climate.toml` `[future]` (`temporal_resolution = "monthly"`, `dataset = "CHELSA-climatologies-v2.1-CMIP6"`), explicitly marked as pending professor confirmation. Rationale and the frost/chilling trade-off this implies are in Section 3 below. See `docs/02` §4. |
| 2 | **GCM set.** The 5 GCMs standardised by CHELSA v2.1, or the 9 used by MONTEVITIS (CHELSA-ISIMIP3b)? | Directly tied to decision 1 — these may be different underlying products, not just a longer list. Determines storage/compute scope (~2x). | **Proposal drafted (Sept 2026): the 5 CHELSA v2.1 GCMs** (GFDL-ESM4, IPSL-CM6A-LR, MPI-ESM1-2-HR, MRI-ESM2-0, UKESM1-0-LL), consistent with decision 1. Recorded in `config/climate.toml` `[models].gcms`, pending confirmation. See `docs/02` §7. |
| 3 | **Confirm SSPs and periods** (SSP1-2.6/3-7.0/5-8.5; 2011–2040/2041–2070/2071–2100) | Already provisional in `climate.toml`; low risk, but should be explicitly signed off before large downloads | Unchanged from the original proposal — still pending sign-off. See `docs/02` §5–6. |
| 4 | **Bioclimatic index list and thresholds per crop** (vinha, oliveira, amendoeira, cerejeira) | Needed before Phase F/G below; requires literature review + agronomist validation, not just a research team's yes/no | Not started. See `docs/02` §11–12. |
| 5 | **Scope confirmation:** does the researcher's responsibility include the socioeconomic diagnosis, and which territory (Douro only vs. all four regions) for this stage | Lower engineering impact, but affects prioritisation | Partially resolved in conversation: Douro is the pilot, architecture built to extend afterwards (see Phase 10). Socioeconomic-diagnosis scope: still open. |

**Recommended action:** decisions 1–3 now have a concrete drafted proposal (Section 3) ready to take to the professor as a single package — present it as a proposal, not a fait accompli. Decision 4 can start in parallel as a literature-review task (see Phase 7).

**Update (Sept 2026):** the user adopted this proposal as the working
assumption to build Phase 2 against, so engineering could proceed
without waiting idle for the professor meeting. This does **not** mean
decisions 1–2 are confirmed — the professor can still redirect them —
it means the alternative (sit idle until a meeting happens) was judged
worse than building against a documented, reasoned proposal that is
cheap to adjust if the professor pushes back (see Section 3's closing
argument about the dataset being a config value, not something baked
into the pipeline shape).

---

### 3. Recommended proposal: monthly CHELSA v2.1, 5 GCMs, 2 SSPs

This is what to present to the professor for decisions 1–2 above.

**Proposal:** use the official CHELSA v2.1 future climatologies (monthly,
same ~1km downscaling methodology as the historical baseline already
validated) with its 5 standardised GCMs — GFDL-ESM4, IPSL-CM6A-LR,
MPI-ESM1-2-HR, MRI-ESM2-0, UKESM1-0-LL — under 2 SSP scenarios: **SSP1-2.6**
(low-emissions/conservative) and **SSP5-8.5** (high-emissions/extreme),
bracketing the plausible range instead of also computing the SSP3-7.0
middle scenario.

**Why:**

- It is the official, already-downscaled-to-1km CHELSA product, from the
  same group and methodology as the historical baseline — scientific
  continuity, no need to build a separate downscaling step.
- 5 GCMs × 2 SSPs × 3 periods × monthly is a much smaller acquisition and
  compute footprint than 9 GCMs × daily (the MONTEVITIS/CHELSA-ISIMIP3b
  approach) or even the full 3-SSP version — faster to implement, test
  and defend, and the platform can present results as a clear
  "conservative vs. extreme" bracket rather than three overlapping lines
  that are harder to read at the municipality scale.
- The acquisition scaffold already built (`climate_acquisition.py`)
  targets the CHELSA climatology-style endpoint, which matches this
  product's format.

**Update (Sept 2026): revised from 3 SSPs to 2.** The proposal originally
included SSP3-7.0 as a middle scenario (and Phase 2's real-server
validation happened to use it, since scenario choice doesn't affect the
URL/format questions Phase 2 was validating). The user opted for the
2-scenario bracket instead, ahead of Phase 3 (multi-GCM processing), both
to cut the acquisition volume by a third and because conservative-vs-
extreme is what a decision-facing atlas actually needs to show — SSP3-7.0
can be added later as a strict extension (same config-driven dataset
handling as any other scenario) if the professor or a reviewer asks for
it. `config/climate.toml`'s `[future].scenarios` and `[pilot].scenario`
reflect this.

**The trade-off, to state explicitly rather than leave implicit:**
monthly data cannot directly support frost-day counts, extreme-heat-day
counts, or precise chilling-hour models — those need daily minimum/
maximum temperatures. GDD, the Winkler Index, the Huglin Index and the
Branas Hydrothermal Index all have accepted monthly-data formulations in
the literature, so this proposal does not block the core viticulture
indices; it specifically blocks the frost/chilling-sensitive indices
relevant to oliveira, amendoeira and cerejeira (Phase 7).

**Why this doesn't paint the project into a corner:** `climate_selection.py`
and `climate_acquisition.py` already treat the dataset as a configuration
value, not something hardcoded into the pipeline shape. Adding a second,
daily source later (e.g. CHELSA-ISIMIP3b, scoped only to the specific
variables/indices that need it) is an additive extension, not a rewrite
of what Phases 2–5 will build on this proposal.

---

### 4. Track B — engineering roadmap

#### Phase 1 — Generalise the pipeline beyond `tas` — ✅ done (Sept 2026)

*Could start immediately; blocked nothing else; blocked by nothing.*

- `climate_processing.py` now has a generic, variable-parameterised core
  (`calculate_monthly_value_for_regions`, `calculate_monthly_climatology_for_regions`,
  `calculate_annual_climatology_for_regions`, `process_climatology_for_regions`),
  registered per-variable in `CHELSA_VARIABLE_UNITS` (`tas`, `tasmin`,
  `tasmax`, `pr` today; an unsupported variable raises a clear error
  rather than silently applying the wrong unit conversion).
- `climate_pipeline.py` got generic counterparts
  (`process_municipality_climatology`,
  `process_multiple_municipalities_climatology`,
  `process_nuts3_climatology`) alongside the original `_temperature`
  functions, which are now thin wrappers over the same generic core —
  unchanged signatures, unchanged behaviour, no breakage to the
  notebook, the pilot export pipeline, or existing tests.
- `data_io.py` already accepted `variable` as a parameter and needed no
  changes.
- Covered by new tests proving the unit-conversion logic is actually
  correct per variable (temperature converts Kelvin → Celsius;
  precipitation does not), not just that the code runs.

**Remaining before this is validated against real data:** the historical
CHELSA rasters for `tasmin`, `tasmax`, `pr` still need to be downloaded
locally (same 1981–2010 baseline, same Douro region) and run through
`process_nuts3_climatology(..., variable="tasmin")` etc. — the synthetic
tests prove the logic is correct, not that the real CHELSA files match
the expected naming/unit assumptions.

#### Phase 2 — Future data acquisition — ✅ done, confirmed against the real CHELSA server (Sept 2026)

*Unblocked: the user adopted the Section 3 proposal (monthly CHELSA v2.1,
5 GCMs) as the working assumption to build against, pending final
professor sign-off.*

**Done:**

- `src/climate_acquisition.py`: `build_chelsa_future_climatology_url` and
  `load_chelsa_future_monthly_subset`, the future-data equivalents of the
  historical `build_chelsa_climatology_url`/`load_chelsa_monthly_subset`,
  parametrised by variable + GCM + SSP + period. `CHELSA_FUTURE_GCM_SLUGS`
  maps the 5 configured GCMs to their filename slugs and rejects
  anything else.
- `src/future_climate_pipeline.py`: `load_future_month_for_experiment`,
  the future counterpart to the existing
  `load_reference_month_for_experiment`, wired through
  `FutureClimateExperiment`/`FutureClimateSelection` (already built).
- Tests cover the URL construction and validation logic, and the
  loader's wiring (bbox → URL → metadata), using a mocked network call
  — the same pattern used for the historical loader's tests.
- **The remote host, path and filename pattern are now confirmed
  against real CHELSA directory listings** (browsed manually via
  envicloud.wsl.ch, since this development session cannot reach
  `os.zhdk.cloud.switch.ch` or `os.unil.cloud.switch.ch` itself — see
  `docs/03` section 3). This corrected two things that were wrong in the
  original guess:
  - **Wrong host.** The originally coded host
    (`os.zhdk.cloud.switch.ch/chelsav2/GLOBAL/...`) 404'd on a real
    request. The real host/bucket is
    `os.unil.cloud.switch.ch/chelsa02/chelsa/global/climatologies/`.
    This affects **both** the historical and future URL builders — the
    historical loader's remote endpoint had never actually been tested
    against a live server either (the Douro pilot's confirmed-good
    values came from `src/climate_processing.py` reading local
    pre-downloaded rasters directly, a different code path).
  - **Wrong format/path shape.** The real server is GeoTIFF
    (`.tif`), organised as `climatologies/{variable}/{period}/...`
    (historical) and
    `climatologies/{variable}/{period}/{GCM}/{scenario}/{filename}`
    (future) — not the NetCDF `ncdf/` mirror previously assumed for
    the historical loader. Both loaders now read GeoTIFF through the
    same `engine="rasterio"` xarray backend.
  - **GCM realization variant confirmed for all 5 GCMs.** Future
    filenames embed a CMIP6 realization/forcing code, e.g.
    `CHELSA_gfdl-esm4_r1i1p1f1_w5e5_ssp126_tas_01_2071-2100_V.2.1.tif`.
    All 5 configured GCMs use `r1i1p1f1` in this CHELSA product —
    notably including `UKESM1-0-LL`, which uses a *different* variant
    (`r1i1p1f2`) under the standard ISIMIP3b protocol elsewhere, but
    was confirmed as `r1i1p1f1` here directly from a real filename
    (`CHELSA_ukesm1-0-ll_r1i1p1f1_w5e5_ssp126_tas_01_2071-2100_
    V.2.1.tif`). Encoded in `CHELSA_FUTURE_GCM_VARIANTS`.

**Also fixed, from a second real run (Sept 2026):** after the host/path
fix above, the user's next run got past the URL but hit
`KeyError: "'lon' is not a valid dimension or coordinate for Dataset
with dimensions FrozenMappingWarningOnValuesAccess({'band': 1, 'x':
43200, 'y': 20880})"`. That real error revealed the actual dims
`xarray`'s `engine="rasterio"` backend uses for a CHELSA GeoTIFF —
`band`/`x`/`y`, not `lat`/`lon` as the loaders assumed. Investigated
locally (no network needed — a synthetic GeoTIFF built with `rasterio`
using CHELSA's documented convention: raw int16 values, embedded
`scale=0.1`/`offset=0`) and confirmed:

- The backend auto-decodes the GeoTIFF's embedded scale/offset into
  physical units (a raw `2794` came back as `279.4`, matching
  `exactextract`/GDAL's behaviour for the local pre-downloaded
  rasters). **Neither loader re-applies `CHELSA_SCALE_FACTOR` anymore**
  — the historical loader's previous unconditional `× 0.1` was
  double-applying it and has been removed.
- `y` is ordered descending (north to south), which matters for
  `.sel()` slicing direction.
- The single-band `band` dimension needs squeezing away.

`src/climate_acquisition.py` now has a shared
`_open_and_subset_chelsa_geotiff` helper (used by both loaders) that
renames `x`/`y` → `lon`/`lat`, squeezes `band`, and picks the correct
slice direction from the actual coordinate order. This is a documented,
general property of the rasterio/GDAL backend (not something specific
to the one synthetic file tested), so it is trusted to hold for the
real CHELSA server too.

**Confirmed against the real server (Sept 2026):** the user re-ran
`scripts/validate_future_acquisition.py` locally after the dims/scale-
factor fix (third real run — the first two are what drove the two
fixes above) and both loaders succeeded cleanly against Vila Real's
bbox, July:

- **Historical** (`tas`, 1981–2010): 289.3–295.7 K (≈16.2–22.6 °C) —
  plausible for July in the Vila Real area.
- **Future** (`tas`, MRI-ESM2-0, ssp370, 2041–2070): 292.5–299.0 K
  (≈19.4–25.9 °C) — mean ≈3.3 °C warmer than the historical mean, a
  physically sensible mid-century warming signal for a high-emissions
  SSP.
- Both results' attrs match CHELSA's own published metadata exactly
  (`cf_standard_name: air_temperature`, the official CHELSA v2.1
  citations, `forcing_source_id: MRI-ESM2-0`,
  `forcing_experiment_id: ssp370`), independently confirming the
  URL/path, dims and scale-factor fixes are all correct — not just
  internally consistent.

This closes out the three-round real-world feedback loop: (1) guessed
URL → `FileNotFoundError` → fixed host/path from a real directory
listing; (2) fixed URL, wrong dims assumed → `KeyError` → fixed dims/
scale-factor from a local synthetic-raster investigation; (3) both
fixes → clean success with plausible, metadata-consistent values.

**Still open (does not block Phase 3, address opportunistically):**

- Raw future data persistence under `data/raw/future/...` (the
  directory convention already exists in `climate_paths.py`, but no
  download has actually been run to populate it — Phase 3 will do this
  as part of looping over the full GCM list).
- Minor: `xarray`/`dask` prints a `UserWarning` about the loaders'
  default `chunks={"x": 500, "y": 500}` not aligning with the GeoTIFF's
  internal tiling ("could degrade performance"). Harmless for the
  small bbox subsets acquired so far; worth revisiting if Phase 3's
  full-region, multi-GCM loop turns out slow.

**Deliverable:** ✅ one confirmed future climatology cell (Douro-area
bbox, `tas`, MRI-ESM2-0, SSP3-7.0, 2041–2070), spot-checked against
plausible values for the region — done above.

#### Phase 3 — Multi-GCM processing — ✅ confirmed against real data for one scenario/period (Sept 2026), full sweep pending

*Depended on Phase 2, which is now done.*

**Scope decided for this first pass** (narrower than "everything
configured", to keep the first real acquisition run's volume
manageable — see the scenario-bracket decision above): one variable
(`tas`), the Douro region, all 5 configured GCMs, both configured
scenarios (`ssp126`, `ssp585`), all 3 periods. That is 5 × 2 × 3 × 12 =
360 real downloads — narrower scopes (fewer scenarios/periods, via the
new script's flags) can validate the pipeline faster before committing
to the full run.

**Done:**

- `src/future_climate_processing.py` (new module):
  - `calculate_future_monthly_climatology_for_gcm`: downloads (via the
    already-confirmed Phase 2 loader) and persists each of the 12
    months for one GCM/scenario/period/variable/region combination,
    then reuses `calculate_monthly_value_for_regions` — the same
    generic zonal-statistics core the historical pipeline uses — on
    each persisted raster, instead of writing a second implementation.
    Already-persisted months are skipped on a re-run (`force_download`
    to override), matching `processing.preserve_rasters = true`.
  - `calculate_future_monthly_climatology_for_all_gcms`: loops the
    above over every GCM in `config/climate.toml`'s `[models].gcms`,
    keeping each GCM's result as its own rows (tagged by `gcm`) rather
    than averaging them — averaging is Phase 4, not this phase.
  - `persist_future_month_raster`: writes a downloaded month to a
    local GeoTIFF via `rioxarray`. This caught a real bug during
    testing: the Phase 2 loader's output uses `lat`/`lon` dims (its
    own established convention), but `rioxarray`'s `.rio.to_raster()`
    does not auto-detect those as spatial dims (only `x`/`y`) and
    raises `MissingSpatialDimensionError` without an explicit
    `rio.set_spatial_dims(x_dim="lon", y_dim="lat")` first — now
    handled, and verified end-to-end against the real Phase 2 loader's
    actual output shape (not just a synthetic test fixture), confirming
    the round-tripped raster still decodes correctly through
    `exactextract`/GDAL exactly like the pre-downloaded historical
    rasters do.
- `scripts/build_future_climatology.py` (new): the script the user
  runs locally to perform the real acquisition. Loads CAOP boundaries
  the same way `scripts/build_pilot_region.py` does, loops configured
  (or `--scenario`/`--period`-narrowed) scenario × period combinations,
  and writes one combined CSV to
  `data/processed/future/{region}_{variable}_future_climatology.csv`.
  Prints the total combination/download count up front, since this is
  real network traffic on the user's machine, not something to start
  blind.
- Tests (`tests/test_future_climate_processing.py`, all mocked/
  synthetic, no network): persistence round-trip, one full 12-month ×
  N-municipality result for one GCM with correct `gcm`/`scenario`/
  `period` tagging and correct unit conversion (reusing Phase 1's
  Kelvin→Celsius logic), the multi-GCM loop tagging results correctly
  per GCM, the "no GCMs configured" guard, and — critically — that a
  second call with the same selection does **not** re-download
  (asserts the mocked loader is never called), proving the persistence
  skip-if-exists logic actually works, not just that it's present in
  the code.

**Confirmed against real data (Sept 2026):** the user ran
`scripts/build_future_climatology.py --scenario ssp585 --period 2041-2070`
(the narrow first slice — 5 GCMs × 12 months = 60 real downloads) and
it completed cleanly: `Wrote 1140 rows (5 GCMs x 1 scenarios x 1
periods x 12 months x 19 municipalities)`, exactly matching the
expected row count (5 × 12 × 19). Sample values (GFDL-ESM4, January)
range 6.4–8.2 °C across Douro's municipalities, with the right spatial
pattern — higher/more interior municipalities (Penedono, Sernancelhe)
colder than lower-elevation ones near the river (Mesão Frio, Peso da
Régua), consistent with the region's real orography. This confirms the
full acquisition → persistence → zonal-statistics chain end to end for
real, not just against synthetic fixtures.

**Explicitly NOT done:**

- **The full 360-download sweep** (both scenarios × all 3 periods,
  instead of just the one ssp585/2041-2070 slice confirmed above)
  hasn't run yet. `scripts/build_future_climatology.py` with no
  `--scenario`/`--period` flags does this; already-downloaded months
  are reused, so re-running now only fetches the remaining ~300.
- Variables beyond `tas` (`tasmin`, `tasmax`, `pr`) — the code is
  already generic per-variable (same `CHELSA_VARIABLE_UNITS` core as
  Phase 1), so this is a scope expansion via the script's `--variable`
  flag once `tas` is confirmed for real, not new code.
- Regions beyond Douro — `calculate_future_monthly_climatology_for_gcm`
  only supports a single NUTS III name today (via
  `resolve_selection_bounding_box`), so Beira Interior's multi-NUTS3
  combination (Phase 10) is not yet wired into this future-data path.

**Deliverable:** ✅ done above — one confirmed real result set (Douro,
`tas`, all 5 GCMs, ssp585, 2041-2070), plausible values with the right
geographic pattern.

#### Phase 4 — Ensemble and uncertainty — ✅ done (Sept 2026)

*Depends on Phase 3, which is now done.*

- `src/climate_ensemble.py` (new): `calculate_ensemble_climatology`
  aggregates Phase 3's per-GCM rows into one row per municipality/
  month/variable/scenario/period, implementing
  `config/climate.toml`'s `[ensemble].method = "equal_weight_mean"`
  and the `min`/`max`/`std` uncertainty metrics. Scenario and period
  are deliberately kept as separate groups, never averaged together —
  the two-scenario bracket (docs/04 Section 3) exists specifically to
  show conservative vs. extreme as distinct outcomes.
- Unsupported `ensemble.method` or `uncertainty_metrics` values raise
  a clear error instead of silently producing a wrong/partial result —
  same defensive pattern as `CHELSA_VARIABLE_UNITS` in Phase 1.
- `scripts/build_ensemble_climatology.py` (new): takes a Phase 3 CSV
  (`scripts/build_future_climatology.py`'s output) and writes the
  ensemble result to `data/processed/ensemble/`. Smoke-tested against
  a small CSV built from the user's real Phase 3 sample values
  (Alijó, January, ssp585/2041-2070 across all 5 GCMs) — ensemble mean
  7.53 °C, range 6.75–8.25 °C, std 0.59 °C, all plausible.
- `tests/test_climate_ensemble.py` (new, 8 tests, synthetic fixture
  only — no real GCM data needed): basic mean/min/max/std arithmetic,
  a zero-spread case, scenarios and municipalities correctly kept
  separate rather than blended, only the requested uncertainty metrics
  appear as columns, and the three configuration-error cases (bad
  method, bad metric, missing column).

**Deliverable:** ✅ done — run
`python -m scripts.build_ensemble_climatology <path to a Phase 3 CSV>`
once real Phase 3 data is available (the partial ssp585/2041-2070 CSV
already works; re-run once the full sweep finishes for the complete
picture).

#### Phase 5 — Climate-change anomalies

*Depends on Phase 4; independent of Phases 6–8.*

- Compute future-minus-baseline deltas per variable/SSP/period (absolute
  for temperature, absolute + % for precipitation, per the earlier
  architecture discussion).
- Store as first-class outputs (not recomputed on every request) — these
  are the numbers the platform should actually display, not raw futures
  alone.

#### Phase 6 — General bioclimatic indices

*Depends on Phase 1 (multi-variable) for the historical baseline version;
depends on Phase 2's data-resolution decision for the future version.*

Two-tier structure, as previously agreed:

- **Tier 1 — general indices**, computable for any crop or none: GDD,
  frost days, extreme-heat days, growing-season precipitation, water
  balance/PET-based indicators.
- Implement and validate against the historical baseline first (data
  already available), before requiring future data.

#### Phase 7 — Crop-specific indices

*Depends on Phase 6 and on Track A decision 4 (index list + thresholds).*

Recommended crop order — vinha first, because it has the most direct
precedent (MONTEVITIS, CITAB/Hélder Fraga's own published methodology):

1. **Vinha:** GDD/Winkler Index, Huglin Index, Cool Night Index, Dryness
   Index, Branas Hydrothermal Index.
2. **Oliveira, amendoeira, cerejeira:** chilling requirement, thermal
   accumulation, frost risk during sensitive phenological phases, extreme
   heat, water availability.

Each index: implement, cite its literature source, and flag its threshold
values as `pending validation` until the agronomy team confirms them —
never invent a threshold.

#### Phase 8 — Agroclimatic zoning

*Depends on Phase 7 and on thresholds being confirmed (not just implemented).*

- Combine indices into suitability classes (`unsuitable` /
  `marginal` / `suitable` / `highly suitable`, pending confirmation of this
  exact scheme per `docs/02` §13).
- Produce current-suitability zoning first (baseline only), then
  future-suitability and suitability-change once Phases 2–5 are in place.

#### Phase 9 — Platform integration

*Depends on whichever of Phases 3–8 is ready; can be done incrementally,
one layer at a time, rather than as one big-bang release.*

- Extend `pilot_export.py`/`api/main.py`/`web/` to add: SSP + period +
  variable selectors, ensemble mean + uncertainty band display, anomaly
  view, index layers, zoning layer.
- Each addition should ship independently (e.g. "add tasmin/tasmax to the
  map" doesn't need to wait for indices to be ready).
- The **region** axis of this is already done (Phase 10, below) — the
  platform now has a working selector pattern (`GET /api/pilot` listing
  built regions, a dropdown that reloads the map/panel/legend on
  change). The same pattern is the template for the variable/period/SSP
  selectors this phase still needs to add.

#### Phase 10 — Scale beyond Douro — 🟡 infrastructure done (Sept 2026), Beira Interior data pending

*Independent track, ran in parallel once Phase 1 was stable.*

**Done:**

- `get_municipalities_by_nuts3_list` (`src/boundary_processing.py`) and
  `process_multi_nuts3_climatology` (`src/climate_pipeline.py`): a
  region can now be one or more combined NUTS III units, not just one —
  needed because AquaHub intervention areas (e.g. "Beira Interior") are
  project-defined, not guaranteed to match a single official NUTS III
  name.
- `config/climate.toml`'s `[pilot_platform]` restructured into a
  `[[pilot_platform.regions]]` list (slug + label + `nuts3_names`),
  replacing the single hardcoded Douro region.
- `scripts/build_pilot_douro.py` replaced by
  `scripts/build_pilot_region.py`, which builds every configured region
  (or one, via `--region <slug>`) instead of only Douro.
- `api/main.py` generalised: region slugs are validated against
  `climate.toml`'s configured list (an allow-list, closing what would
  otherwise be a path-construction risk from an arbitrary path
  parameter) rather than a single hardcoded slug; a new
  `GET /api/pilot` lists regions that are both configured and actually
  built.
- `web/` got a region `<select>`, wired to `GET /api/pilot`; switching
  regions reloads the map layer, legend and banner without a page
  reload. Verified with two synthetic regions carrying different data
  (different temperature ranges, different municipality sets) to prove
  the switch actually changes what's displayed, not just the label.
- Covered by new tests in `test_boundary_processing.py`,
  `test_climate_pipeline.py` and `test_pilot_api.py` (unconfigured
  region → 404 via the allow-list; configured-but-unbuilt region → the
  build-hint 404; region listing only includes built regions).

**Update (Sept 2026):** the real CAOP2025 `nuts3` values were checked
against this project's actual file. It confirmed CAOP2025 uses
Portugal's revised (2024) NUTS III classification — there is no unit
literally named "Beira Interior". `climate.toml` now sets
`nuts3_names = ["Beira Baixa", "Beiras e Serra da Estrela"]` for
Beira Interior, the combination that corresponds to the old "Beira
Interior Norte" + "Beira Interior Sul" + "Cova da Beira" units under
the classification revision. **This is a geographic inference, not a
confirmed match to the AquaHub project's official intervention
boundary** — worth a quick sanity check against the project's own area
definition before treating it as final. `python -m
scripts.build_pilot_region --region beira-interior` will build it with
no further code changes, once CHELSA/CAOP data is available locally.

- Castilla y León / Extremadura: needs a Spanish administrative-boundary
  source (not yet identified) before the same pipeline can run there.

---

### 5. Suggested execution order

```text
Track A (professor) ──────────────────────────────────────────┐
  1. daily vs monthly / GCM set  ─────┐                        │
  2. confirm SSP/periods          │   │                        │
  3. index list + thresholds ─────┼───┼──────────┐             │
                                   │   │          │             │
Track B (engineering)              ▼   ▼          ▼             │
  Phase 1: multi-variable pipeline (now, no blocker)            │
       │                                                        │
       ▼                                                        │
  Phase 2: future acquisition (done, built+confirmed against the
           Section 3 proposal — still needs A.1/A.2 sign-off to lock in)
       │
       ▼
  Phase 3: multi-GCM → Phase 4: ensemble → Phase 5: anomalies
       │                                         │
       ▼                                         │
  Phase 6: general indices (baseline now,   ◄─────┘
           future once Phase 5 ready)
       │
       ▼
  Phase 7: crop indices ◄──────────────────(needs A.3: thresholds)
       │
       ▼
  Phase 8: zoning
       │
       ▼
  Phase 9: platform integration (incremental, alongside 3-8)

  Phase 10: scale to Beira Interior / Spain (parallel, after Phase 1)
```

**What can start today, with zero new decisions from the professor:**
Phase 1 (multi-variable pipeline), Phase 2 (now done — see its section
above), Phase 3 onward built against the Section 3 proposal, the
synthetic-fixture parts of Phase 4 (ensemble arithmetic), and Phase
10's Beira Interior extension (same country, same data source).

**What is blocked until Track A resolves:** nothing technically — Phase
2 proved the Section 3 proposal (monthly CHELSA v2.1, 5 GCMs) works
end-to-end against the real server, so engineering can keep proceeding
against it. What's still open is the professor's formal sign-off on
that dataset/GCM choice (A.1/A.2) — if it changes, only
`build_chelsa_future_climatology_url`/`load_chelsa_future_monthly_subset`
and `config/climate.toml`'s `[future]`/`[models]` need to change, not
Phases 3 onward's logic — and Phase 7's exact index thresholds
(A.3), which still blocks crop-specific index work specifically.
