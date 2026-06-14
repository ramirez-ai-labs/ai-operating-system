from packages.shared.graphs.one_on_one_os import run_one_on_one_graph
from packages.shared.schemas.one_on_one_os import OneOnOneRequest, OneOnOneResponse


def build_meeting_brief(request: OneOnOneRequest) -> OneOnOneResponse:
    """Public entry point for the One-on-One OS meeting brief workflow."""
    return run_one_on_one_graph(request)
