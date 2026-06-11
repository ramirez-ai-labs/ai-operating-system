from __future__ import annotations

import argparse
import json
from pathlib import Path

from packages.shared.evaluations.director_os import (
    DEFAULT_DIRECTOR_OS_EVALS_PATH,
    apply_provider_override,
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
    parser.add_argument(
        "--provider",
        choices=["ollama", "claude"],
        default=None,
        help=(
            "Override the model provider for all evaluation cases. "
            "'claude' requires ANTHROPIC_API_KEY. "
            "Skips cases that use a provider_scenario (fake-provider tests)."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cases = load_director_os_eval_cases(Path(args.cases_path))

    if args.provider:
        cases = apply_provider_override(cases, args.provider)
        if not cases:
            raise SystemExit("No eligible cases after applying provider override.")

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
