# CLAUDE.md

## What this is

AquaHub Climate is a climate-risk atlas for AquaHub's intervention zones
(Douro, Terras de Trás-os-Montes, Beira Interior in Portugal; Castilla y
León, Extremadura in Spain), built with a university professor as the
domain-science partner. Source of truth is `docs/`, read in order:

1. `docs/01_climate_baseline_methodology.md` — validated historical
   baseline pipeline (CHELSA climatologies, `tas`, 1981–2010).
2. `docs/02_methodological_questions_for_team.md` — open questions log
   referenced throughout `docs/03`/`docs/04`.
3. `docs/03_pilot_interactive_platform.md` — the interactive map/API/frontend.
4. `docs/04_roadmap_future_and_bioclimatic_indices.md` — future scenarios,
   bioclimatic indices, and what's confirmed vs. still a working hypothesis.

Don't duplicate their content here — when in doubt, read the relevant
doc rather than assuming this file is up to date.

## Non-negotiable rule

**Never invent a scientific value or threshold ahead of confirmation.**
If real data/confirmation isn't available yet, show "pending"/"no data
yet" in the UI rather than a plausible-looking placeholder — a
placeholder risks being mistaken for a validated result. This is why
the pilot map currently shows all 5 zones as "pending" even though some
have real temperature data underneath (see `docs/03` Section 6,
`docs/04` Phase 7). Treat anything from the professor (dataset choice,
GCM list, index formulas/thresholds) as a working hypothesis until he
confirms it in writing, even if it's already wired into code or config.

## Data layout

- `data/raw/` — licensed/source datasets (CHELSA rasters, CAOP/GISCO
  boundaries, the professor's deliveries). **Not in Git**, must exist
  locally to run the pipeline.
- `data/processed/pilot/` — the small GeoJSON/JSON the interactive
  platform's API serves directly from disk. **The one exception that
  IS committed to Git** (stateless hosts like Vercel can't run the
  pipeline at deploy time — see `docs/03` Section 10).
- Everything else under `data/processed/` — derived output, **not in
  Git**, regenerable from `data/raw/` via the pipeline scripts.

## Current platform state

All 5 zones on the map render as "pending" (dashed outline, no data on
click) **on purpose** — the temperature index was deliberately hidden so
it isn't mistaken for the professor's real bioclimatic indices, which
don't exist yet. The temperature pipeline itself still runs and is
still tested; only the map display was changed. **Don't re-enable
showing `annual_mean_celsius` on the map without re-reading `docs/04`
Phase 7 first** — this was an explicit, reasoned decision, not a bug.

## Testing

`pytest`. Most suites use synthetic/mocked fixtures and need no network
or real CHELSA/CAOP/GISCO access; a few opt-in tests exercise real
remote/local data and are skipped by default.

## Branch convention

Active development happens on `feature/future-climate-pipeline`.
