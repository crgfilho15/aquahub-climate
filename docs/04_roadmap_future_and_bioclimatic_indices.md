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

| # | Decision | Why it blocks engineering | Where it's already framed |
|---|---|---|---|
| 1 | **Daily vs. monthly future data.** Is the intended future dataset CHELSA-ISIMIP3b (daily, used by MONTEVITIS) or the CHELSA v2.1 future climatologies (monthly)? | Frost days, GDD, chilling hours and most bioclimatic indices need daily data. Building the acquisition layer against the wrong product means rebuilding it. | `docs/02` §4; flagged explicitly in the architecture discussion before this platform was built |
| 2 | **GCM set.** The 5 GCMs standardised by CHELSA v2.1, or the 9 used by MONTEVITIS (CHELSA-ISIMIP3b)? | Directly tied to decision 1 — these may be different underlying products, not just a longer list. Determines storage/compute scope (~2x). | `docs/02` §7 |
| 3 | **Confirm SSPs and periods** (SSP1-2.6/3-7.0/5-8.5; 2011–2040/2041–2070/2071–2100) | Already provisional in `climate.toml`; low risk, but should be explicitly signed off before large downloads | `docs/02` §5–6 |
| 4 | **Bioclimatic index list and thresholds per crop** (vinha, oliveira, amendoeira, cerejeira) | Needed before Phase F/G below; requires literature review + agronomist validation, not just a research team's yes/no | `docs/02` §11–12 |
| 5 | **Scope confirmation:** does the researcher's responsibility include the socioeconomic diagnosis, and which territory (Douro only vs. all four regions) for this stage | Lower engineering impact, but affects prioritisation | `docs/02` §1 |

**Recommended action:** take decisions 1–3 to the professor first, as a single question ("which exact CHELSA product, which GCMs") — they gate everything in Phase 2 onward below. Decision 4 can start in parallel as a literature-review task (see Phase F).

---

### 3. Track B — engineering roadmap

#### Phase 1 — Generalise the pipeline beyond `tas`

*Can start immediately; blocks nothing else; blocked by nothing.*

- Refactor `climate_processing.py` to accept `variable` as a parameter
  instead of hardcoding `tas` in the raster filename and in the two
  `variable =` assignments.
- Extend `climate_pipeline.py`'s municipality/region/NUTS3 functions to
  pass `variable` through.
- Validate against the already-downloaded historical CHELSA rasters for
  `tasmin`, `tasmax`, `pr` (same 1981–2010 baseline, same Douro region —
  reuses the already-proven zonal-statistics logic, just parametrised).
- Update `docs/01` and tests accordingly.

**Deliverable:** Douro historical climatology for `tas`, `tasmin`, `tasmax`,
`pr`, with the same validation rigour as the existing `tas` baseline.

#### Phase 2 — Future data acquisition

*Blocked by Track A decision 1–2 (which product, which GCMs).*

- Write the future-data equivalent of `climate_acquisition.py`'s
  `load_chelsa_monthly_subset` (or a daily variant, depending on decision 1),
  parametrised by GCM + SSP + period.
- Prove it end-to-end with **one** GCM × one SSP × one period × Douro bbox
  before scaling — this mirrors how the historical pipeline was validated
  (single municipality first, then NUTS3).
- Persist raw future data under `data/raw/future/...` following the
  directory convention already built in `climate_paths.py`.

**Deliverable:** one validated future climatology cell (e.g. Douro, `tas`,
one confirmed GCM, SSP3-7.0, 2041–2070), spot-checked against the paper's
own reported figures where possible.

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

#### Phase 10 — Scale beyond Douro

*Independent track, can run in parallel once Phase 1 is stable.*

- Beira Interior: same CAOP source, should mostly be a `region_name` config
  change plus re-running the pipeline.
- Castilla y León / Extremadura: needs a Spanish administrative-boundary
  source (not yet identified) before the same pipeline can run there.

---

### 4. Suggested execution order

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
