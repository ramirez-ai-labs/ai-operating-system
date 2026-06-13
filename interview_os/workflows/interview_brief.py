from packages.shared.graphs.interview_os import run_interview_brief_graph
from packages.shared.schemas.interview_os import InterviewBriefRequest, InterviewBriefResponse


def build_interview_brief(request: InterviewBriefRequest) -> InterviewBriefResponse:
    """Run the Interview OS brief graph behind the stable public API."""
    return run_interview_brief_graph(request)
