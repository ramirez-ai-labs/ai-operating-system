#!/usr/bin/env python3
"""
Director OS evaluation runner — Claude provider.

Runs the checked-in eval set against the Claude provider and writes
scored results to evaluations/director_os/results_claude.json.

Commit these results. They are the evidence that the system produces
grounded, structured output when backed by a real LLM — not just
when running on the deterministic fallback path.

Usage:
    # Local run (requires ANTHROPIC_API_KEY in .env)
    python scripts/run_director_os_evals_claude.py

    # With LangSmith result upload
    python scripts/run_director_os_evals_claude.py --langsmith

    # CI (skips gracefully if key absent)
    python scripts/run_director_os_evals_claude.py --ci
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


EVAL_CASES = [
    {
        "id": "director_os_001",
        "prompt": "Prepare my weekly leadership update",
        "context": (
            "Project: MAP Platform onboarding\n"
            "Status: 3 of 5 BUs onboarded to Canary environment\n"
            "Blockers: Security review pending for BU-4, estimated 1 week delay\n"
            "Wins this week: BU-2 and BU-3 passed production readiness gates\n"
            "Next steps: Kick off BU-4 security review, schedule BU-5 readiness review\n"
        ),
        "expected_signals": ["blocker", "security", "onboard", "BU"],
        "must_not_contain": ["I don't know", "no information", "unable to"],
    },
    {
        "id": "director_os_002",
        "prompt": "What are the top risks this week?",
        "context": (
            "Risk log:\n"
            "- RISK-01: Data pipeline latency spike — P1, owner: infra team\n"
            "- RISK-02: Vendor API deprecation in Q4 — P2, owner: platform team\n"
            "- RISK-03: Two engineers on PTO next sprint — P3, owner: eng manager\n"
        ),
        "expected_signals": ["risk", "pipeline", "vendor", "P1"],
        "must_not_contain": ["hallucin", "fabricat"],
    },
    {
        "id": "director_os_003",
        "prompt": "Summarise key decisions from this week's 1:1 notes",
        "context": (
            "1:1 with Sarah (SRE lead) — June 9:\n"
            "  Decision: Adopt Terraform 1.8 for all new infra modules\n"
            "  Action item: Sarah to update runbooks by June 20\n\n"
            "1:1 with Marcus (DevEx lead) — June 9:\n"
            "  Decision: Roll out Cursor to remaining 12 engineers by end of sprint\n"
            "  Action item: Marcus to schedule onboarding sessions\n"
        ),
        "expected_signals": ["Terraform", "Cursor", "decision", "action"],
        "must_not_contain": ["I cannot", "no context"],
    },
]


def score_response(response_text: str, case: dict) -> dict:
    """
    Score a Claude response against expected signals and exclusions.

    Scoring:
        signal_score:  fraction of expected_signals found in response
        safety_score:  1.0 if no must_not_contain terms present, else 0.0
        grounded:      True if signal_score >= 0.5 and safety_score == 1.0
    """
    text_lower = response_text.lower()

    signals_found = [
        s for s in case["expected_signals"]
        if s.lower() in text_lower
    ]
    signal_score = len(signals_found) / len(case["expected_signals"])

    violations = [
        v for v in case.get("must_not_contain", [])
        if v.lower() in text_lower
    ]
    safety_score = 0.0 if violations else 1.0

    return {
        "signal_score": round(signal_score, 3),
        "signals_found": signals_found,
        "signals_missing": [
            s for s in case["expected_signals"] if s not in signals_found
        ],
        "safety_score": safety_score,
        "violations": violations,
        "grounded": signal_score >= 0.5 and safety_score == 1.0,
    }


def run_evals(langsmith: bool = False, ci_mode: bool = False) -> int:
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

    try:
        from packages.shared.providers.claude_provider import ClaudeProvider
    except ImportError:
        logger.error("Could not import ClaudeProvider. Run: pip install -e '.[dev]'")
        return 1

    provider = ClaudeProvider()
    if not provider.is_available():
        logger.error("ClaudeProvider not available despite API key being set.")
        return 1

    logger.info("Running %d Director OS eval cases against Claude...\n", len(EVAL_CASES))

    results = []
    passed = 0

    for case in EVAL_CASES:
        logger.info("  Case %s: %s", case["id"], case["prompt"])

        start = time.time()
        response = provider.complete(
            prompt=case["prompt"],
            context=case["context"],
        )
        elapsed = round(time.time() - start, 2)

        scores = score_response(response.content, case)
        status = "PASS" if scores["grounded"] else "FAIL"
        if scores["grounded"]:
            passed += 1

        logger.info(
            "    %s — signal=%.0f%% safety=%.0f%% tokens=%d latency=%ss",
            status,
            scores["signal_score"] * 100,
            scores["safety_score"] * 100,
            response.total_tokens,
            elapsed,
        )

        results.append({
            "case_id": case["id"],
            "prompt": case["prompt"],
            "response": response.content,
            "model": response.model,
            "scores": scores,
            "tokens": {
                "input": response.input_tokens,
                "output": response.output_tokens,
            },
            "latency_seconds": elapsed,
            "status": status,
        })

    total = len(EVAL_CASES)
    pass_rate = round(passed / total, 3)
    logger.info("\nResults: %d/%d passed (%.0f%%)", passed, total, pass_rate * 100)

    output = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "provider": "claude",
        "model": results[0]["model"] if results else "unknown",
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": pass_rate,
        },
        "cases": results,
    }

    output_path = Path("evaluations/director_os/results_claude.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2))
    logger.info("Results written to %s", output_path)

    if langsmith:
        _upload_to_langsmith(output)

    threshold = 0.6
    if pass_rate < threshold:
        logger.error(
            "Pass rate %.0f%% is below threshold %.0f%%",
            pass_rate * 100,
            threshold * 100,
        )
        return 1

    return 0


def _upload_to_langsmith(results: dict) -> None:
    """Upload results to LangSmith. Requires LANGSMITH_API_KEY in environment."""
    try:
        from langsmith import Client
        client = Client()
        dataset_name = "director-os-claude-evals"
        logger.info("Uploading results to LangSmith dataset: %s", dataset_name)
        # TODO: implement dataset creation and example upload via client API
        # See: https://docs.smith.langchain.com/reference/python
        logger.warning(
            "LangSmith upload not yet implemented — results saved locally only."
        )
    except ImportError:
        logger.warning("langsmith not installed — skipping upload. Run: pip install langsmith")
    except Exception as exc:
        logger.warning("LangSmith upload failed: %s", exc)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Director OS evals against Claude")
    parser.add_argument("--langsmith", action="store_true", help="Upload results to LangSmith")
    parser.add_argument("--ci", action="store_true", help="CI mode: skip gracefully if key absent")
    args = parser.parse_args()

    sys.exit(run_evals(langsmith=args.langsmith, ci_mode=args.ci))
