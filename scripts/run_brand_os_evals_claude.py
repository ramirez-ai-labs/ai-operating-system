#!/usr/bin/env python3
"""
Brand OS evaluation runner — Claude provider.

Runs the canonical eval set (evaluations/brand_os/content_draft_cases.json)
against ClaudeBrandContentDraftProvider through the Brand OS graph and writes
scored results to evaluations/brand_os/results_claude.json.

Commit the results. They are the evidence that the production synthesis path
produces grounded, structured output — not a separate bespoke code path.

Usage:
    # Local run (requires ANTHROPIC_API_KEY in .env)
    python -m scripts.run_brand_os_evals_claude --allow-live

    # CI (always skips: CI never makes live calls without --allow-live)
    python -m scripts.run_brand_os_evals_claude --ci
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from packages.shared.config.live_calls import (
    ALLOW_LIVE_FLAG,
    ALLOW_LIVE_HELP,
    check_live_claude_run,
)
from packages.shared.config.models import DEFAULT_CLAUDE_MODEL

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

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
    / "brand_os"
    / "results_claude.json"
)

_CLAUDE_MODEL = DEFAULT_CLAUDE_MODEL


def run_evals(ci_mode: bool = False, allow_live: bool = False) -> int:
    """Run evals and return exit code (0 = pass, 1 = fail)."""
    # .env is loaded above, so the key's presence is not an opt-in. Live calls
    # need --allow-live on this run (see packages/shared/config/live_calls.py).
    stop = check_live_claude_run(
        allow_live=allow_live, ci_mode=ci_mode, what="brand_os Claude evals"
    )
    if stop is not None:
        return stop

    from packages.shared.evaluations.brand_os import (
        BRAND_OS_CLAUDE_EVALUATORS,
        BrandContentDraftEvalCase,
        load_brand_os_eval_cases,
        run_local_brand_os_evaluations,
    )

    base_cases = load_brand_os_eval_cases()
    claude_cases: list[BrandContentDraftEvalCase] = [
        case.model_copy(
            update={
                "inputs": case.inputs.model_copy(
                    update={
                        "use_model": True,
                        "provider": "claude",
                        "claude_model": _CLAUDE_MODEL,
                    }
                ),
            }
        )
        for case in base_cases
    ]

    logger.info(
        "Running %d Brand OS eval cases against ClaudeBrandContentDraftProvider...\n",
        len(claude_cases),
    )

    results = run_local_brand_os_evaluations(claude_cases, evaluators=BRAND_OS_CLAUDE_EVALUATORS)

    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed
    pass_rate = round(passed / len(results), 3) if results else 0.0

    summary = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "provider": "claude",
        "model": _CLAUDE_MODEL,
        "eval_path": "evaluations/brand_os/content_draft_cases.json",
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
        failing = [r["key"] for r in result["results"] if not r["score"]]
        detail = "" if result["passed"] else f"  failing: {failing}"
        logger.info("  %s  %s%s", status, result["case_id"], detail)

    return 0 if failed == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Brand OS evals against Claude.")
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Skip gracefully instead of failing when a live run is not permitted (CI).",
    )
    parser.add_argument(
        ALLOW_LIVE_FLAG, dest="allow_live", action="store_true", help=ALLOW_LIVE_HELP
    )
    args = parser.parse_args()
    sys.exit(run_evals(ci_mode=args.ci, allow_live=args.allow_live))


if __name__ == "__main__":
    main()
