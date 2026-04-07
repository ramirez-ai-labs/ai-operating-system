from __future__ import annotations

import argparse
import json
from pathlib import Path

from packages.shared.evaluations.director_os import (
    DEFAULT_DIRECTOR_OS_EVALS_PATH,
    load_director_os_eval_cases,
    run_langsmith_director_os_evaluations,
    run_local_director_os_evaluations,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the checked-in Director OS weekly-update evaluation set."
    )
    parser.add_argument(
        "--langsmith",
        action="store_true",
        help="Upload the evaluation run to LangSmith using the current environment variables.",
    )
    parser.add_argument(
        "--cases-path",
        default=str(DEFAULT_DIRECTOR_OS_EVALS_PATH),
        help="Path to the local JSON evaluation cases file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    # This script supports both fully local checks and optional LangSmith-backed
    # runs, but the local path stays the default so normal SDLC remains cheap.
    cases = load_director_os_eval_cases(Path(args.cases_path))
    if args.langsmith:
        experiment = run_langsmith_director_os_evaluations(cases=cases)
        print(experiment)
        return

    results = run_local_director_os_evaluations(cases)
    print(json.dumps(results, indent=2))
    failed_cases = [item["case_id"] for item in results if not item["passed"]]
    if failed_cases:
        raise SystemExit(
            f"Director OS evaluations failed for: {', '.join(failed_cases)}"
        )


if __name__ == "__main__":
    main()
