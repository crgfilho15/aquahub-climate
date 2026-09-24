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
  ISIMIP3b; periods 2041–2070 / 2071–2100; scenarios SSP1-2.6 /
  SSP3-7.0 / SSP5-8.5; ensemble = equal-weight mean with min/max/std
  uncertainty; GCM list intentionally empty). **Update (Sept 2026):**
  originally 3 periods (2011–2040 / 2041–2070 / 2071–2100) and 3 SSPs
  (SSP1-2.6/3-7.0/5-8.5) — both trimmed since, see Section 3.

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
| 1 | **Daily vs. monthly future data.** Is the intended future dataset CHELSA-ISIMIP3b (daily, used by MONTEVITIS) or the CHELSA v2.1 future climatologies (monthly)? | Frost days, GDD, chilling hours and most bioclimatic indices need daily data. Building the acquisition layer against the wrong product means rebuilding it. | **Proposal drafted (Sept 2026): monthly.** Recorded in `config/climate.toml` `[future]` (`temporal_resolution = "monthly"`, `dataset = "CHELSA-climatologies-v2.1-CMIP6"`), explicitly marked as pending professor confirmation. Rationale and the frost/chilling trade-off this implies are in Section 3 below. See `docs/02` §4. **Update (Sept 2026): the professor's first real delivery (`data/raw/ensemble1/`) is NEX-GDDP-CMIP6 via `NEX_1km_outputs`, not CHELSA v2.1** — a different dataset than this proposal. Treated as a working hypothesis, not a confirmed change, until the professor confirms in writing. See Section 2.1 below. |
| 2 | **GCM set.** The 5 GCMs standardised by CHELSA v2.1, or the 9 used by MONTEVITIS (CHELSA-ISIMIP3b)? | Directly tied to decision 1 — these may be different underlying products, not just a longer list. Determines storage/compute scope (~2x). | **Proposal drafted (Sept 2026): the 5 CHELSA v2.1 GCMs** (GFDL-ESM4, IPSL-CM6A-LR, MPI-ESM1-2-HR, MRI-ESM2-0, UKESM1-0-LL), consistent with decision 1. Recorded in `config/climate.toml` `[models].gcms`, pending confirmation. See `docs/02` §7. **Update (Sept 2026): `ensemble1`'s global attrs list only 4 GCMs** (missing MRI-ESM2-0) **and only one future period** (2041-2070, not all 3) — see Section 2.1 for whether this is a deliberate scope or a partial delivery. |
| 3 | **Confirm SSPs and periods** (SSP1-2.6/3-7.0/5-8.5; 2011–2040/2041–2070/2071–2100) | Already provisional in `climate.toml`; low risk, but should be explicitly signed off before large downloads | SSPs narrowed to 2 (Section 3) and periods narrowed to 2 — **2011-2040 dropped entirely (Sept 2026, user decision)**, not part of the project's scope, see Section 2.1 Q3 and `config/climate.toml`. 2071-2100 still pending sign-off. See `docs/02` §5–6. |
| 4 | **Bioclimatic index list and thresholds per crop** (vinha, oliveira, amendoeira, cerejeira) | Needed before Phase 7/8 below; requires literature review + agronomist validation, not just a research team's yes/no | **Update (Sept 2026, professor meeting): the professor will calculate the crop-specific indices himself and deliver them to the user** — not something this codebase computes from scratch. Changes Phase 7's shape: from "implement each index's formula" to "ingest and display the professor's delivered values" (format/schema TBD once the user shares what he delivers). Phase 6's generic Tier-1 indices (GDD/Winkler Index, already built) stay useful as an independent cross-check, not a substitute. |
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

**Update (Sept 2026, professor meeting):** the professor met with the
user and sketched part of the platform's visual architecture (mockup
to follow). Two things from that meeting:

- **Decision 1–2 (dataset/GCMs) is still open** — the professor said he
  is still reviewing which dataset to use. No change to the "proposal,
  not confirmed" status above; still safe to keep building against it
  (config value, cheap to swap), but do not treat it as settled.
- **Decision 4 (index list/thresholds) has a new answer, not just a
  status update: the professor will calculate the crop-specific
  bioclimatic indices himself and hand the results to the user.**
  This changes Phase 7's job from "implement each index's formula
  once thresholds are confirmed" to "ingest whatever the professor
  delivers and get it onto the platform" — closer to Phase 9
  (platform integration) than to new scientific computation. Don't
  build crop-specific index formulas ahead of seeing what format the
  professor's delivery takes.

The mockup, once shared, should clarify how the professor wants the
platform laid out — treat it as the concrete spec for Phase 9's
remaining work (variable/index selectors, layers, panel layout),
overriding this doc's own guesses where they conflict.

---

### 2.1. First real delivery from the professor: `data/raw/ensemble1/` (Sept 2026)

**Update (Sept 2026):** the professor sent a first real dataset —
inspected read-only with `xarray` (no parser/ingestion code written
yet; this is exploration, tracked as a separate step before Phase 7's
"ingest" work starts). It lives at `data/raw/ensemble1/` (moved there
for consistency with `data/raw/`'s existing untracked-raw-data
convention — same `.gitignore` rule already covers it, no config
change needed) and its 129-variable reference table (name, min/max per
file) is at `data/raw/ensemble1/variables_reference.csv`.

**What it is:**

- 3 NetCDF files, structurally identical to each other (same 129
  variables, same order, same dims/coords/encoding — only the values
  and the `scenario`/`period`/`clip_source` attributes differ):
  - `historical/ensemble_historical_1981-2010.nc` — `scenario=historical`, `period=1981-2010`
  - `ssp126/ensemble_ssp126_2041-2070.nc` — `scenario=ssp126`, `period=2041-2070`
  - `ssp585/ensemble_ssp585_2041-2070.nc` — `scenario=ssp585`, `period=2041-2070`
- **129 data variables** (short codes — `GDD10`, `HUGLIN`, `BRANAS`,
  `DI`, `CI`, `SELIANINOV`, `LTI`, `BIO1`–`BIO19`, `ET0_ANNUAL`,
  `WB_ANNUAL`, `CHILL_HOURS`, `TXx`, `FD`, etc. — clearly bioclimatic/
  agroclimatic indices) with **no in-file units/long_name/standard_name**
  (`attrs = {}` on every variable). The meaning/unit of each code is
  not self-describing and needs the professor's own legend before any
  ingestion work starts.
- **A raster grid, not per-zone/municipality values**: dims
  `(time=1, lat=638, lon=784)`, ~0.00833° (~1 km) resolution, bbox
  lon -8.296 to -1.771 / lat 37.929 to 43.237 — clipped to **the union
  of all 5 AquaHub zones** (global attr `clip_shapefile:
  ...\aquahub_zones.shp`, `clip_note: "clipped to the union of all
  polygons in aquahub_zones.shp, not to individual polygons"`). That
  shapefile is the same one `scripts/export_zones_shapefile.py`
  (`docs/03` Section 7) generates from `zones_overview.geojson` — so
  the "export zones → professor clips his own results → sends back"
  loop described there is confirmed working in practice, one round
  trip in.

**Contradicts the Section 3 proposal — flagged, not assumed:**

- Global attrs give `clip_source:
  E:\NEX_1km_outputs\ensemble\<scenario>\...` — this is **NEX-GDDP-CMIP6
  data via `NEX_1km_outputs`, not CHELSA v2.1** as Section 3 proposed
  and `config/climate.toml`'s `[future]` currently records. Same
  pattern the project already applies elsewhere (`docs/03` Section 7,
  `docs/04` Section 2): **treat this as the professor's working
  hypothesis for what dataset is actually being used, not a confirmed
  fact**, until he confirms it in writing. Don't change
  `config/climate.toml`'s `dataset` value or any code on the strength
  of this file's attributes alone.
- `models` global attr lists only **4 GCMs** — GFDL-ESM4, IPSL-CM6A-LR,
  MPI-ESM1-2-HR, UKESM1-0-LL — **missing MRI-ESM2-0** from the 5-GCM
  proposal in decision 2/Section 3. (That 5-GCM list was this
  project's own proposal to the professor, not something he'd
  previously confirmed — so this isn't necessarily him overriding a
  decision, it may simply be the set he actually has ensembled.)
- Only **one future period** is present (`2041-2070`), not the 3 that
  were in `config/climate.toml`'s `[future].periods` at the time
  (2011–2040 / 2041–2070 / 2071–2100). **Update (Sept 2026):**
  2011–2040 has since been dropped from that list entirely (see the
  status note after the question table below) — the remaining gap is
  just 2071-2100.
- **Open question for the professor, not yet answered:** is `ensemble1`
  a deliberate, final scope (4 models, 1 period, as a first cut) or a
  partial/in-progress delivery with more to come? Don't build ingestion
  logic that assumes either answer until he says which.

**Data-quality finding to report back:** `SELIANINOV`'s historical-file
maximum is `34,349,936` — several orders of magnitude above its
ssp126/ssp585 maxima (`~202` / `~71`) and above every other variable in
the file. Looks like a numerical artifact (likely division by a
near-zero denominator somewhere in the professor's own calculation),
not a mistake in how this project read the file. Worth flagging to the
professor rather than silently normalising or clipping it.

**Open questions to take back to the professor** (compiled while
inspecting this delivery):

| # | Question |
|---|---|
| 1 | Is the dataset really NEX-GDDP-CMIP6 (`NEX_1km_outputs`), not CHELSA v2.1 as this project's own proposal assumed — and if so, is that a deliberate choice? |
| 2 | Is the 4-GCM ensemble (missing MRI-ESM2-0) intentional, or is a 5th model still to come? |
| 3 | Is `ensemble1`'s single future period (2041-2070) a deliberate first cut, or should 2011-2040 and 2071-2100 be expected later? |
| 4 | What do the 129 variable codes mean — is there a legend/data dictionary (units, formula, literature source) to go with them? |
| 5 | What does the `SELIANINOV` outlier in the historical file (34,349,936 vs. ~70-200 in the future files) indicate — a bug on his side, or a real edge case in the formula? |
| 6 | What format will future deliveries take — more NetCDF ensembles like this one, per-crop threshold tables, or something else — so the ingestion step (Phase 7) can be designed for the real shape instead of guessed? |
| 7 | Should this raster-grid ensemble be aggregated to the same per-zone/per-municipality shape the rest of the platform uses (`docs/03` Section 6), or does the professor intend to deliver zone-level summaries himself? |

> **Status note (Sept 2026):** re. Q3 above — the user decided
> **2011-2040 will not be used**, regardless of what the professor
> eventually says about it. This isn't "still waiting to see if he
> delivers it" — it's removed from the project's scope entirely:
> dropped from `config/climate.toml`'s `[future].periods`, the Climate
> Atlas's Period selector (`web/app.js`), and the Section 3 proposal
> below. 2071-2100 remains open per Q3, unaffected by this decision.

**Deliberately not done yet:** no parser or ingestion code for
`ensemble1` — this section only records what was found by read-only
inspection. Phase 7's actual "ingest what the professor delivers" work
starts once the above questions are answered (particularly #4 and #6),
so the ingestion shape isn't built against a guess that turns out
wrong.

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
- 5 GCMs × 2 SSPs × 2 periods × monthly is a much smaller acquisition and
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

**Update (Sept 2026): also revised from 3 periods to 2.** The proposal
originally included 2011-2040 alongside 2041-2070 and 2071-2100. The
user decided to drop 2011-2040 entirely (not deferred — out of scope),
independent of whether the professor ever delivers it for `ensemble1`.
`config/climate.toml`'s `[future].periods` reflects this.

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
scenarios (`ssp126`, `ssp585`), all 3 periods (at the time — see the
Sept 2026 update below). That is 5 × 2 × 3 × 12 =
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

- **The full download sweep** (both scenarios × both configured
  periods, instead of just the one ssp585/2041-2070 slice confirmed
  above) hasn't run yet. `scripts/build_future_climatology.py` with no
  `--scenario`/`--period` flags does this; already-downloaded months
  are reused, so re-running now only fetches the remaining months.
  **Update (Sept 2026):** the original scope above assumed 3 periods
  (360 downloads total); 2011-2040 has since been dropped from
  `config/climate.toml` entirely (Section 2.1/3), so the real remaining
  full sweep is 5 GCMs × 2 scenarios × 2 periods × 12 months = 240
  downloads, of which 60 (ssp585/2041-2070) are already done.
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

#### Phase 5 — Climate-change anomalies — ✅ done (Sept 2026)

*Depends on Phase 4, which is now done; independent of Phases 6–8.*

- `src/climate_anomalies.py` (new): `calculate_climate_anomalies` joins
  Phase 4's ensemble output against Phase 1's historical baseline
  output (`calculate_monthly_climatology_for_regions`) on municipality/
  month/variable, and computes `anomaly_absolute` (future − baseline)
  for every variable, plus `anomaly_percent` for precipitation only
  (`PERCENT_ANOMALY_VARIABLES = {"pr"}`) — a "% warmer" reading near
  0 °C isn't meaningful, but "% wetter/drier" is. The same baseline is
  reused across every scenario/period row (a many-to-one join); a
  baseline with more than one row per municipality/month/variable (a
  caller passing multiple periods by mistake) raises an error rather
  than silently picking one arbitrarily, same for any row with no
  matching baseline at all.
- `scripts/build_anomaly_climatology.py` (new): takes a Phase 4
  ensemble CSV, recomputes the historical baseline the same way
  `scripts/build_pilot_region.py` does, and writes the anomaly result
  to `data/processed/anomalies/`.
- `tests/test_climate_anomalies.py` (new, 7 tests, synthetic fixtures
  only): temperature gets absolute-only anomaly, precipitation gets
  both absolute and percent, the same baseline is correctly reused
  across scenarios, and the four error cases (missing ensemble/
  historical columns, a duplicated baseline, a baseline missing for
  some row).

**Deliverable:** run
`python -m scripts.build_anomaly_climatology <path to a Phase 4 ensemble CSV>`
once real Phase 3/4 data is available for a region/variable.

#### Phase 6 — General bioclimatic indices — 🟡 GDD/Winkler + precipitation done (Sept 2026)

*Depended on Phase 1 (multi-variable) for the historical baseline version
and Phase 2's data-resolution decision for the future version - both done.*

Two-tier structure, as previously agreed:

- **Tier 1 — general indices**, computable for any crop or none: GDD,
  frost days, extreme-heat days, growing-season precipitation, water
  balance/PET-based indicators.
- Implement and validate against the historical baseline first (data
  already available), before requiring future data.

**Done:**

- `src/bioclimatic_indices.py` (new): `calculate_growing_degree_days`
  (monthly-approximation GDD, parameterised by base temperature and
  season months) and `calculate_growing_season_precipitation`. Both
  are deliberately generic over their input - the same function works
  on Phase 1's historical monthly climatology
  (`value_column="mean_value"`, `group_columns=["municipality"]`) or
  Phase 4/5's ensemble/anomaly output (`value_column="ensemble_mean"`,
  `group_columns=["municipality", "scenario", "period"]`), so no
  separate "future version" of this code is needed once real future
  data is available.
- `calculate_winkler_index`: the classic viticulture heat-summation
  index (Amerine & Winkler, 1944) - GDD with `base_temperature=10.0`
  and `season_months=range(4, 11)` (April-October), a named fixed-
  parameter case of the same function. Directly relevant to Douro
  (vinha, one of the 4 target crops). Deliberately stops at the raw
  index value - the Winkler region classification (I-V) is a threshold
  scheme and is not implemented here, consistent with Phase 7's rule
  of never inventing a threshold ahead of agronomist confirmation.
- Sanity-checked against the user's real Phase 4 ensemble values for
  Alijó (ssp585, 2041-2070): Winkler Index ≈ 2151, a plausible value
  for a warm future scenario in a region already known as a warm wine
  region historically - not the kind of implausible number that would
  indicate a formula error.
- `tests/test_bioclimatic_indices.py` (new, 9 tests, synthetic
  fixtures only): basic GDD arithmetic, negative degree-days clipped
  to zero rather than allowed to cancel out warmer months, custom
  base/season parameters, the Winkler wrapper matching its equivalent
  direct GDD call, growing-season precipitation summing only the
  requested months, groups (e.g. two scenarios) kept separate rather
  than blended, and the three error cases (missing column, invalid
  month, empty season selection).

**Explicitly NOT done (out of Tier 1's realistic scope given monthly-
only data):**

- **Frost days and extreme-heat days** need daily minimum/maximum
  temperatures to count days crossing a threshold - not computable
  from monthly means. This is exactly the frost/chilling-sensitive
  gap flagged when the monthly-vs-daily trade-off was decided (docs/04
  Section 3), not a new limitation.
- **Water balance/PET-based indicators** need `pet`, one of
  `climate.toml`'s `[variables].optional` variables, whose unit
  conversion is not yet confirmed (`CHELSA_VARIABLE_UNITS` in
  `src/climate_processing.py` only covers `tas`/`tasmin`/`tasmax`/`pr`
  today) - implementing this without a confirmed conversion would risk
  silently applying the wrong unit, which the project's existing
  pattern explicitly refuses to do.

**Deliverable:** ✅ done for GDD/Winkler Index and growing-season
precipitation - both work against historical data today and will work
unchanged against real future/ensemble data once available.

#### Phase 7 — Crop-specific indices — ✅ ingested and wired into the platform (Sept 2026)

*Depends on Track A decision 4, which now has an answer that changes
this phase's shape (see the Track A table above).*

**The professor calculated the crop-specific indices himself and
delivered the results to the user** — this codebase does not implement
Winkler/Huglin/Cool Night/Dryness/chilling-requirement formulas for
crop-specific thresholds; it ingests his output as-is. What was planned
below (the `<details>` block) is superseded by the format his delivery
actually took; kept as historical context for the reasoning (crop
order, index names, "never invent a threshold"), not as a build list
to execute.

**Delivered and ingested (Sept 2026):** `data/raw/ensemble1/` (3
NetCDF files — historical 1981-2010, ssp126 2041-2070, ssp585
2041-2070 — 129 bioclimatic/agroclimatic indices each, ~1km grid) plus
`indices_por_cultura.csv` (per-index code, name, formula, literature
reference, and a relevance flag per crop — verified 129/129 against
`ensemble1`'s variable codes, no mismatch; see Section 2.1). Both are
treated as a working hypothesis, not a final confirmation, until the
professor confirms the dataset/GCM choice in writing (`docs/02`
sections 4 and 7).

- `src/indices_catalog.py` + `scripts/build_indices_catalog.py` parse
  the CSV (Portuguese content kept as delivered — English translation
  is a tracked follow-up, not done yet, see below) and validate every
  code against `ensemble1` → `data/processed/pilot/indices_catalog.json`
  (committed, drives the Atlas's Crop/Index filters and formula box).
- `src/index_pilot_export.py` + `scripts/build_index_pilot_data.py`
  crop all 129 bands to each of the 5 zones for each of the 3 epochs,
  writing a `uint16`-quantized (per-variable scale/offset), compressed
  GeoTIFF per zone/epoch (`data/processed/pilot/indices/`, committed —
  142.10MB total measured, comfortably under GitHub's 100MB-per-file
  limit) plus coverage-weighted mean/min/max stats via `exact_extract`.
- `api/main.py`: `GET /api/indices` (the catalog), `GET
  /api/pilot/zones/index/{code}[/{scenario}/{period}]` (all 5 zones'
  pixel grid + shared min/max in one response), `GET
  /api/pilot/{region}/index/{code}[/{scenario}/{period}]/point`
  (exact-pixel lookup by lat/lon) — same allow-list-before-filesystem
  and build-hint-404 conventions as the rest of this file.
- `web/atlas.html`/`app.js`: Crop select → Index select (filtered to
  that crop's relevant codes) → formula box; on a complete
  Crop/Index/Period/SSP selection, each zone's real pixel grid is
  painted onto an HTML canvas and overlaid on the map
  (`L.imageOverlay`) with one shared color scale across all 5 zones —
  a real heatmap, not a flat per-zone fill. Clicking a zone shows the
  distribution of its pixel values; clicking a point returns that
  exact pixel's value. Combinations `ensemble1` doesn't cover (every
  period except historical and the two SSPs @ 2041-2070) show a "not
  delivered yet" message instead of inventing a value.
- `tests/test_indices_catalog.py`, `tests/test_index_pilot_export.py`
  (synthetic fixtures) and new cases in `tests/test_pilot_api.py` — 23
  new tests, full suite 171 passed/1 skipped.

**Explicitly deferred, not forgotten:** translating
`indices_catalog.json`'s Portuguese content (and the Atlas's Index/
formula display) to English is a separate, later pass — this round
intentionally kept the professor's Portuguese content as-is to get the
real data wired in first, per an explicit decision during
implementation.

<details>
<summary>Original plan (superseded, kept for context)</summary>

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

</details>

#### Phase 8 — Agroclimatic zoning

*Depends on Phase 7 and on thresholds being confirmed (not just implemented).*

- Combine indices into suitability classes (`unsuitable` /
  `marginal` / `suitable` / `highly suitable`, pending confirmation of this
  exact scheme per `docs/02` §13).
- Produce current-suitability zoning first (baseline only), then
  future-suitability and suitability-change once Phases 2–5 are in place.

#### Phase 9 — Platform integration — 🟡 first slice done (Sept 2026): scenario/period selector, ensemble + anomaly view

*Depends on whichever of Phases 3–8 is ready; done incrementally, one
layer at a time, rather than as one big-bang release.*

- Extend `pilot_export.py`/`api/main.py`/`web/` to add: SSP + period +
  variable selectors, ensemble mean + uncertainty band display, anomaly
  view, index layers, zoning layer.
- Each addition should ship independently (e.g. "add tasmin/tasmax to the
  map" doesn't need to wait for indices to be ready).
- The **region** axis of this is already done (Phase 10, below) — the
  platform now has a working selector pattern (`GET /api/pilot` listing
  built regions, a dropdown that reloads the map/panel/legend on
  change). The same pattern is now also the template used below for the
  period/scenario selector.

**Done (first slice — scenario/period, ensemble mean, anomaly view):**

- `src/future_pilot_export.py` (new): `build_future_pilot_feature_collection`
  converts one variable/scenario/period slice of Phase 5's anomaly
  output (which already carries Phase 4's ensemble values) into a
  GeoJSON `FeatureCollection`, mirroring `pilot_export.py`'s shape for
  the historical baseline — same static-file architecture, no live
  computation in the API. Reuses `calculate_annual_climatology_for_regions`
  (the historical pipeline's own days-weighted annual aggregation) so
  the annual figure is computed the same way for both.
- `scripts/build_future_pilot_data.py` (new): takes a Phase 4 ensemble
  CSV, recomputes the historical baseline the same way
  `scripts/build_anomaly_climatology.py` does, and writes one GeoJSON/
  metadata pair per scenario/period found in the CSV to
  `data/processed/pilot/future/`.
- `api/main.py`: `GET /api/pilot/{region}/future` (lists built
  variable/scenario/period combinations), `GET
  /api/pilot/{region}/future/{variable}/{scenario}/{period}` and
  `.../meta`. Variable/scenario/period are validated against
  `config/climate.toml` before ever being used to build a file path —
  the same allow-list principle already applied to the region slug.
- `web/`: a period selector next to the region selector
  (`index.html`/`app.js`), defaulting to "Histórico (1981-2010)" with
  one option per available future scenario/period, fetched from the
  new `/future` listing endpoint. Selecting a future option re-renders
  the same map/legend/panel components used for historical data — the
  future GeoJSON's `annual_ensemble_mean`/`monthly_ensemble_mean`
  properties are normalised client-side to the historical property
  names (`annual_mean_celsius`/`monthly_mean_celsius`) so the existing,
  already-tested rendering code (colour scale, legend, chart with
  hover/keyboard interaction) needed no changes. The panel additionally
  shows the anomaly vs. the historical baseline (e.g. "Cenário ssp585 ·
  vs. histórico (1981-2010): +3.50 °C") when viewing future data.
- Verified end-to-end with a headless browser (Chromium via Playwright)
  against synthetic historical + future fixture data for two
  municipalities: default historical view loads correctly, the future
  option appears in the selector, switching to it updates the banner
  (scenario, period, GCM count), re-colours the map, and the panel
  shows the correct annual value and anomaly line; switching back
  behaves correctly. Screenshot confirms the map, legend, panel and
  chart all render as expected. The only console noise was the
  sandbox's network policy blocking OpenStreetMap base-map tiles (not
  a code issue — tiles will load normally outside this sandbox) and a
  pre-existing, unrelated `/favicon.ico` 404.
- `tests/test_future_pilot_export.py` (7 tests) and additions to
  `tests/test_pilot_api.py` (7 tests) - all synthetic fixtures, no
  network or real CHELSA/CAOP data needed.
- **Found and fixed a real, currently-active bug while starting this
  phase:** `pilot_export.py`'s `build_pilot_feature_collection` still
  expected a `mean_celsius` column, but Phase 1's generalisation
  changed what `scripts/build_pilot_region.py` actually calls to
  return `mean_value` instead. A real run of `build_pilot_region.py`
  today would have raised `KeyError: 'mean_celsius'` — masked because
  `tests/test_pilot_export.py`'s fixtures built `mean_celsius`
  DataFrames directly rather than going through the real pipeline.
  Fixed and the test fixtures corrected to match reality (see that
  PR for the full explanation).

**Explicitly NOT done yet:**

- Uncertainty band display (min/max from Phase 4's ensemble output are
  in the GeoJSON's source anomaly data but not yet surfaced in the UI).
- Index layers (Phase 6's GDD/Winkler Index) and the zoning layer
  (Phase 8) — natural next additions to this same pattern.
- A real run of `scripts/build_future_pilot_data.py` against real data
  — the verification above used synthetic fixtures written directly to
  the expected file locations, not a real CSV → GeoJSON build. Next
  step once the user's full download + ensemble/anomaly CSVs are ready.

**Deliverable:** 🟡 done for the scenario/period selector + ensemble +
anomaly view (verified end-to-end with synthetic data); pending one
real run against the user's actual future data.

**Update (Sept 2026): the map's temperature display was retired.**
With Phase 7 confirmed as "ingest the professor's delivered indices,
don't compute our own" (see the Track A table above), showing
`annual_mean_celsius` on the map risked being mistaken for a real
bioclimatic index. `scripts/build_zone_overview.py`/
`src/zone_overview_export.py` now mark every zone `"built": false`
regardless of whether its temperature pipeline has run, so all 5 zones
render as "pending" - the same treatment Castilla y León/Extremadura
already had. This is a display-layer change only: the temperature
pipeline itself (Phases 1-6) is untouched and keeps working/testing
normally, so it stays available later as an independent cross-check
once real index data is ingested (see `docs/03` Section 6).

**Update 2 (Sept 2026): real index data now renders on the map.**
`/api/pilot/zones` (zone geometry, `built: false`) is unchanged and
the temperature index stays off the map, per the above. But once a
Crop/Index/Period/SSP combination is selected and Phase 7's data
exists for it, the zone no longer shows the flat "pending" style — it
shows a real per-pixel heatmap built from the professor's delivered
index data (see Phase 7 above and `docs/03` Section 6). The "pending"
zone styling is now conditional on the current filter selection, not
permanent.

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
