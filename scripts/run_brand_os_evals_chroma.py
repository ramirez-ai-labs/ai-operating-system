#!/usr/bin/env python3
"""
Brand OS evaluation runner — ChromaDB retrieval backend.

Runs the canonical eval set (evaluations/brand_os/content_draft_cases.json)
with RETRIEVAL_BACKEND=chroma through the Brand OS graph and writes scored
results to evaluations/brand_os/results_chroma.json.

Commit the results. They are the evidence that semantic retrieval produces
grounded content drafts that satisfy the same quality bar as the keyword
baseline — closing the untested claim that RETRIEVAL_BACKEND=chroma improves
or equals keyword retrieval for Brand OS content drafts.

Prerequisites:
    ollama pull nomic-embed-text
    python scripts/ingest_local_data.py

Usage:
    # Local run (requires ChromaDB index built via ingest_local_data.py)
    python -m scripts.run_brand_os_evals_chroma

    # CI (skips gracefully if ChromaDB index is absent)
    python -m scripts.run_brand_os_evals_chroma --ci
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
    / "results_chroma.json"
)


def run_evals(ci_mode: bool = False) -> int:
    """Run evals against the chroma backend and return exit code (0 = pass, 1 = fail)."""
    from packages.shared.retrieval.chroma import is_index_ready

    if not is_index_ready():
        msg = (
            "ChromaDB index not found. "
            "Run: ollama pull nomic-embed-text && python scripts/ingest_local_data.py"
        )
        if ci_mode:
            logger.info("%s — skipping chroma evals in CI", msg)
            return 0
        logger.error(msg)
        return 1

    # Activate the chroma backend for this evaluation run.
    os.environ["RETRIEVAL_BACKEND"] = "chroma"

    from packages.shared.evaluations.brand_os import (
        load_brand_os_eval_cases,
        run_local_brand_os_evaluations,
    )

    cases = load_brand_os_eval_cases()
    logger.info(
        "Running %d Brand OS eval cases with RETRIEVAL_BACKEND=chroma...\n",
        len(cases),
    )

    results = run_local_brand_os_evaluations(cases)

    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed
    pass_rate = round(passed / len(results), 3) if results else 0.0

    summary = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "retrieval_backend": "chroma",
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
    logger.info("Summary: %d/%d passed (%.0f%%)", passed, len(results), pass_rate * 100)

    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        failing = [r["key"] for r in result["results"] if not r["score"]]
        detail = "" if result["passed"] else f"  failing: {failing}"
        logger.info("  %s  %s%s", status, result["case_id"], detail)

    return 0 if failed == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Brand OS evals against ChromaDB.")
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Skip gracefully when ChromaDB index is absent (for CI use).",
    )
    args = parser.parse_args()
    sys.exit(run_evals(ci_mode=args.ci))


if __name__ == "__main__":
    main()
