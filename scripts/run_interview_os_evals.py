from __future__ import annotations

import argparse
import json
from pathlib import Path

from packages.shared.evaluations.interview_os import (
    DEFAULT_INTERVIEW_OS_EVALS_PATH,
    load_interview_os_eval_cases,
    run_langsmith_interview_os_evaluations,
    run_local_interview_os_evaluations,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the checked-in Interview OS brief evaluation set."
    )
    parser.add_argument(
        "--cases-path",
        default=str(DEFAULT_INTERVIEW_OS_EVALS_PATH),
        help="Path to the local JSON evaluation cases file.",
    )
    parser.add_argument(
        "--langsmith",
        action="store_true",
        default=False,
        help="Run cloud-backed evaluations via LangSmith (requires LANGSMITH_API_KEY).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.langsmith:
        run_langsmith_interview_os_evaluations()
        return

    cases = load_interview_os_eval_cases(Path(args.cases_path))
    results = run_local_interview_os_evaluations(cases)
    print(json.dumps(results, indent=2))
    failed_cases = [item["case_id"] for item in results if not item["passed"]]
    if failed_cases:
        raise SystemExit(
            f"Interview OS evaluations failed for: {', '.join(failed_cases)}"
        )


if __name__ == "__main__":
    main()
