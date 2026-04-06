from packages.shared.graphs.director_os import run_weekly_update_graph
from packages.shared.schemas.director_os import WeeklyUpdateRequest, WeeklyUpdateResponse


def build_weekly_update(request: WeeklyUpdateRequest) -> WeeklyUpdateResponse:
    """Run the Director OS weekly update graph behind the stable public API."""
    return run_weekly_update_graph(request)
