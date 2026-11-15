from models.mission import PlanRequest, PlanResponse


class RoutePlanner:
    # This is the stable API boundary for the future DEM-based route planner.
    # Do not return a fabricated route before CRS, DEM resolution, no-data rules,
    # terrain costs, and validation datasets have been specified.

    def plan(self, request: PlanRequest) -> PlanResponse:
        if request.start == request.destination:
            raise ValueError("Start and destination must be different.")

        return PlanResponse(
            status="not_implemented",
            profile=request.profile,
            message=(
                "Route planning is not implemented yet. Load and validate a Mars DEM "
                "and integrate the terrain-cost algorithm before returning a route."
            ),
            route=[],
            distance_m=None,
        )
