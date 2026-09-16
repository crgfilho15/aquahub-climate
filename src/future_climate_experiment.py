"""Future climate experiment representation for AquaHub."""

from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd

from src.climate_acquisition import BoundingBox
from src.climate_paths import (
    build_ensemble_directory,
    build_future_processed_directory,
    build_future_raw_directory,
)
from src.climate_region import resolve_selection_bounding_box
from src.climate_selection import FutureClimateSelection


@dataclass(frozen=True)
class FutureClimateExperiment:
    """A complete future climate experiment and its data directories."""

    selection: FutureClimateSelection
    raw_directory: Path
    processed_directory: Path
    ensemble_directory: Path

    @classmethod
    def from_selection(
        cls,
        config: dict,
        selection: FutureClimateSelection,
    ) -> "FutureClimateExperiment":
        """Create an experiment from a validated climate selection."""

        selection.validate(config)

        raw_directory = build_future_raw_directory(
            config=config,
            gcm=selection.gcm,
            scenario=selection.scenario,
            variable=selection.variable,
        )

        processed_directory = build_future_processed_directory(
            config=config,
            gcm=selection.gcm,
            scenario=selection.scenario,
            period=selection.period,
            variable=selection.variable,
        )

        ensemble_directory = build_ensemble_directory(
            config=config,
            scenario=selection.scenario,
            period=selection.period,
            variable=selection.variable,
        )

        return cls(
            selection=selection,
            raw_directory=raw_directory,
            processed_directory=processed_directory,
            ensemble_directory=ensemble_directory,
        )

    def resolve_bounding_box(
        self,
        municipalities_gdf: gpd.GeoDataFrame,
    ) -> BoundingBox:
        """
        Resolve the geographic bounding box
        of this experiment selection.
        """

        return resolve_selection_bounding_box(
            selection=self.selection,
            municipalities_gdf=municipalities_gdf,
        )

    @property
    def experiment_id(self) -> str:
        """Return the identifier of the underlying climate selection."""

        return self.selection.experiment_id
