"""Climate processing selections for the AquaHub future pipeline."""

from dataclasses import dataclass


class ClimateSelectionError(ValueError):
    """Raised when a future climate selection is invalid."""


@dataclass(frozen=True)
class FutureClimateSelection:
    """A validated future climate experiment selection."""

    gcm: str
    scenario: str
    period: str
    variable: str
    region_type: str
    region_name: str

    @classmethod
    def from_pilot(
        cls,
        config: dict,
        gcm: str,
    ) -> "FutureClimateSelection":
        """Create a selection from the configured pilot experiment."""

        pilot = config["pilot"]

        selection = cls(
            gcm=gcm,
            scenario=pilot["scenario"],
            period=pilot["period"],
            variable=pilot["variable"],
            region_type=pilot["region_type"],
            region_name=pilot["region_name"],
        )

        selection.validate(config)

        return selection

    def validate(self, config: dict) -> None:
        """Validate the selection against the climate configuration."""

        future = config["future"]
        variables = config["variables"]
        configured_gcms = config["models"].get("gcms", [])

        all_variables = (
            variables.get("core", [])
            + variables.get("optional", [])
        )

        if not self.gcm.strip():
            raise ClimateSelectionError(
                "GCM cannot be empty."
            )

        if configured_gcms and self.gcm not in configured_gcms:
            raise ClimateSelectionError(
                f"GCM '{self.gcm}' is not configured."
            )

        if self.scenario not in future["scenarios"]:
            raise ClimateSelectionError(
                f"Scenario '{self.scenario}' is not configured."
            )

        if self.period not in future["periods"]:
            raise ClimateSelectionError(
                f"Period '{self.period}' is not configured."
            )

        if self.variable not in all_variables:
            raise ClimateSelectionError(
                f"Variable '{self.variable}' is not configured."
            )

        if not self.region_type.strip():
            raise ClimateSelectionError(
                "Region type cannot be empty."
            )

        if not self.region_name.strip():
            raise ClimateSelectionError(
                "Region name cannot be empty."
            )

    @property
    def experiment_id(self) -> str:
        """Return a compact identifier for the climate experiment."""

        return (
            f"{self.region_name}_"
            f"{self.variable}_"
            f"{self.gcm}_"
            f"{self.scenario}_"
            f"{self.period}"
        )
