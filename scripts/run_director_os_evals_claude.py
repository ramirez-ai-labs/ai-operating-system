#!/usr/bin/env python3
"""
Director OS evaluation runner — Claude provider.

Runs the canonical eval set (evaluations/director_os/weekly_update_cases.json)
against ClaudeWeeklyUpdateProvider through the Director OS graph and writes
scored results to evaluations/director_os/results_claude.json.

Commit the results. They are the evidence that the production synthesis path
produces grounded, structured output — not a separate bespoke code path.

Usage:
    # Local run (requires ANTHROPIC_API_KEY in .env)
    python scripts/run_director_os_evals_claude.py

    # CI (skips gracefully if key absent)
    python scripts/run_director_os_evals_claude.py --ci
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

# Load .env from the project root — same behaviour as the API server.
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

RESULTS_PATH = (
    Path(__file__).resolve().parent.parent
    / "evaluations"
    / "director_os"
    / "results_claude.json"
)


def run_evals(ci_mode: bool = False) -> int:
    """Run evals and return exit code (0 = pass, 1 = fail)."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        if ci_mode:
            logger.info("ANTHROPIC_API_KEY not set — skipping Claude evals in CI")
            return 0
        logger.error(
            "ANTHROPIC_API_KEY not set. "
            "Add it to your .env to run live Claude evaluations."
        )
        return 1

    from packages.shared.evaluations.director_os import (
        apply_provider_override,
        load_director_os_eval_cases,
        run_local_director_os_evaluations,
    )

    cases = load_director_os_eval_cases()
    claude_cases = apply_provider_override(cases, provider="claude")

    logger.info(
        "Running %d Director OS eval cases against ClaudeWeeklyUpdateProvider...\n",
        len(claude_cases),
    )

    results = run_local_director_os_evaluations(claude_cases)

    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed
    pass_rate = round(passed / len(results), 3) if results else 0.0

    summary = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "provider": "claude",
        "model": claude_cases[0].inputs.claude_model if claude_cases else "unknown",
        "eval_path": "evaluations/director_os/weekly_update_cases.json",
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "pass_rate": pass_rate,
        },
        "cases": results,
    }

    RESULTS_PATH.write_text(json.dumps(summary, indent=2))
    logger.info("\nResults written to %s", RESULTS_PATH)
    logger.info(
        "Summary: %d/%d passed (%.0f%%)", passed, len(results), pass_rate * 100
    )

    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        failing = [
            r["key"] for r in result["results"] if not r["score"]
        ]
        detail = "" if result["passed"] else f"  failing: {failing}"
        logger.info("  %s  %s%s", status, result["case_id"], detail)

    return 0 if failed == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Director OS evals against Claude.")
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Skip gracefully when ANTHROPIC_API_KEY is absent (for CI use).",
    )
    args = parser.parse_args()
    sys.exit(run_evals(ci_mode=args.ci))


if __name__ == "__main__":
    main()
