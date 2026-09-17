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

### 3. Recommended proposal: monthly CHELSA v2.1, 5 GCMs

This is what to present to the professor for decisions 1–2 above.

**Proposal:** use the official CHELSA v2.1 future climatologies (monthly,
same ~1km downscaling methodology as the historical baseline already
validated) with its 5 standardised GCMs — GFDL-ESM4, IPSL-CM6A-LR,
MPI-ESM1-2-HR, MRI-ESM2-0, UKESM1-0-LL.

**Why:**

- It is the official, already-downscaled-to-1km CHELSA product, from the
  same group and methodology as the historical baseline — scientific
  continuity, no need to build a separate downscaling step.
- 5 GCMs × 3 SSPs × 3 periods × monthly is a much smaller acquisition and
  compute footprint than 9 GCMs × daily (the MONTEVITIS/CHELSA-ISIMIP3b
  approach) — faster to implement, test and defend.
- The acquisition scaffold already built (`climate_acquisition.py`)
  targets the CHELSA climatology-style endpoint, which matches this
  product's format.

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

#### Phase 2 — Future data acquisition — 🟡 URL/path and dims/scale-factor fixed (Sept 2026), pending one final real-server confirmation

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

**Explicitly NOT done — do not treat this as fully validated:**

- **Confirmation against a real download, with the fixes above, is
  still pending.** The synthetic-raster test proves the *logic* is
  right; it does not prove CHELSA's real files carry the same embedded
  scale/offset tags (very likely, given the local pre-downloaded
  rasters already work this way, but not yet directly observed through
  this remote code path).
- Raw future data persistence under `data/raw/future/...` (the
  directory convention already exists in `climate_paths.py`, but no
  download has actually been run to populate it).

**Next validation step (needs real network access, i.e. not this
session):** `scripts/validate_future_acquisition.py` now runs both
loaders — one small, fast download each (Vila Real bbox, one month) —
printing the requested URLs, success/failure, and (on success) the
resulting data variable names, value ranges and attrs, with guidance on
whether those values match expectations. Run it locally:

```powershell
python -m scripts.validate_future_acquisition
```

Two real runs from the user's machine already drove this fix: the
first got a real `FileNotFoundError` (wrong host/path — fixed by
browsing the CHELSA server manually), the second got the `KeyError`
above (wrong dims — fixed as described). One more real run should now
come back clean on both loaders; if it doesn't, send the exact output.

**Deliverable once validated:** one confirmed future climatology cell
(e.g. Douro, `tas`, one GCM, SSP3-7.0, 2041–2070), spot-checked against
plausible values for the region.

#### Phase 3 — Multi-GCM processing

*Depends on Phase 2.*

- Loop Phase 2's acquisition over the full confirmed GCM list.
- Preserve each GCM's result individually (already the intent of
  `processing.preserve_individual_gcm_results = true` in `climate.toml`).

#### Phase 4 — Ensemble and uncertainty

*Depends on Phase 3.*

- Implement `ensemble.method = "equal_weight_mean"` and the
  `min`/`max`/`std` uncertainty metrics already declared in `climate.toml`.
- Unit-test against a synthetic multi-GCM fixture (same pattern as the
  existing synthetic-raster tests), so this doesn't require real GCM data
  to validate the arithmetic.

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
  Phase 2: future acquisition ◄───────────────────(needs A.1/A.2)
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
Phase 1 (multi-variable pipeline), the synthetic-fixture parts of Phase 4
(ensemble arithmetic), and Phase 10's Beira Interior extension (same
country, same data source).

**What is blocked until Track A resolves:** Phase 2 onward for anything
that touches real future/GCM data, and Phase 7's exact index thresholds.
