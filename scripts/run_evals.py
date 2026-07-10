#!/usr/bin/env python3
"""
Unified eval runner with auto-discovery.

Discovers domain evaluators from packages/shared/evaluations/ by convention:
  load_{domain}_eval_cases        — loads eval cases from JSON
  run_local_{domain}_evaluations  — scores cases locally
  run_langsmith_{domain}_evaluations — uploads run to LangSmith

Adding a new domain requires only its evaluations module and eval-cases JSON;
no new script is needed.

Usage:
    python scripts/run_evals.py                              # all domains, local
    python scripts/run_evals.py --domain director_os        # one domain, local
    python scripts/run_evals.py --domain director_os --backend claude
    python scripts/run_evals.py --domain all --backend chroma --ci
    python scripts/run_evals.py --domain brand_os --langsmith
"""
from __future__ import annotations

import argparse
import importlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_EVALS_PKG = _REPO_ROOT / "packages" / "shared" / "evaluations"
_ENV_FILE = _REPO_ROOT / ".env"

if _ENV_FILE.exists():
    for _line in _ENV_FILE.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())


def _discover_domains() -> list[str]:
    """Return domain names from packages/shared/evaluations/*.py, sorted."""
    return sorted(p.stem for p in _EVALS_PKG.glob("*.py") if p.stem != "__init__")


def _load_module(domain: str):
    return importlib.import_module(f"packages.shared.evaluations.{domain}")


def _default_cases_path(mod, domain: str) -> Path | None:
    attr = f"DEFAULT_{domain.upper()}_EVALS_PATH"
    return getattr(mod, attr, None)


def _load_cases(mod, domain: str, cases_path: str | None):
    load_fn = getattr(mod, f"load_{domain}_eval_cases")
    path = Path(cases_path) if cases_path else _default_cases_path(mod, domain)
    return load_fn(path) if path else load_fn()


def _write_results(domain: str, backend: str, results: list, extra: dict | None = None) -> Path:
    out_path = _REPO_ROOT / "evaluations" / domain / f"results_{backend}.json"
    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed
    pass_rate = round(passed / len(results), 3) if results else 0.0
    payload: dict = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "domain": domain,
        "backend": backend,
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "pass_rate": pass_rate,
        },
        **(extra or {}),
        "cases": results,
    }
    out_path.write_text(json.dumps(payload, indent=2))
    return out_path


def _log_case_results(results: list) -> None:
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        failing = [x["key"] for x in r.get("results", []) if not x.get("score")]
        detail = f"  failing: {failing}" if failing else ""
        logger.info("  %s  %s%s", status, r["case_id"], detail)


def _run_local(domain: str, cases_path: str | None, ci_mode: bool) -> int:
    mod = _load_module(domain)
    cases = _load_cases(mod, domain, cases_path)
    run_fn = getattr(mod, f"run_local_{domain}_evaluations")
    results = run_fn(cases)
    print(json.dumps(results, indent=2))
    failed = [r["case_id"] for r in results if not r["passed"]]
    if failed:
        logger.error("%s failures: %s", domain, ", ".join(failed))
        return 1
    logger.info("%s: %d/%d passed", domain, len(results), len(results))
    return 0


def _run_claude(domain: str, cases_path: str | None, ci_mode: bool) -> int:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        if ci_mode:
            logger.info(
                "ANTHROPIC_API_KEY not set — skipping %s Claude evals in CI", domain
            )
            return 0
        logger.error("ANTHROPIC_API_KEY not set. Add it to .env to run Claude evals.")
        return 1

    mod = _load_module(domain)
    cases = _load_cases(mod, domain, cases_path)

    # Director OS supports multi-provider — filter to Claude cases only.
    apply_fn = getattr(mod, "apply_provider_override", None)
    if apply_fn:
        cases = apply_fn(cases, "claude")
        if not cases:
            logger.info("No eligible Claude cases for %s — skipping", domain)
            return 0

    logger.info("Running %d %s eval cases against Claude...", len(cases), domain)
    run_fn = getattr(mod, f"run_local_{domain}_evaluations")

    # Some domains swap in a Claude-calibrated evaluator set (e.g. Brand OS
    # drops prefix-purity checks that only make sense for the deterministic
    # path). Use it when the domain defines one; otherwise use the default.
    claude_evaluators = getattr(mod, f"{domain.upper()}_CLAUDE_EVALUATORS", None)
    run_kwargs = {"evaluators": claude_evaluators} if claude_evaluators is not None else {}
    results = run_fn(cases, **run_kwargs)

    passed = sum(1 for r in results if r["passed"])
    failed_count = len(results) - passed
    pass_rate = round(passed / len(results), 3) if results else 0.0
    out_path = _write_results(domain, "claude", results)
    logger.info("Results written to %s", out_path)
    logger.info("Summary: %d/%d passed (%.0f%%)", passed, len(results), pass_rate * 100)
    _log_case_results(results)
    return 0 if failed_count == 0 else 1


def _run_chroma(domain: str, cases_path: str | None, ci_mode: bool) -> int:
    from packages.shared.retrieval.chroma import is_index_ready

    if not is_index_ready():
        msg = (
            "ChromaDB index not found. "
            "Run: ollama pull nomic-embed-text && python scripts/ingest_local_data.py"
        )
        if ci_mode:
            logger.info("%s — skipping %s chroma evals in CI", msg, domain)
            return 0
        logger.error(msg)
        return 1

    os.environ["RETRIEVAL_BACKEND"] = "chroma"

    mod = _load_module(domain)
    cases = _load_cases(mod, domain, cases_path)
    logger.info(
        "Running %d %s eval cases with RETRIEVAL_BACKEND=chroma...", len(cases), domain
    )
    run_fn = getattr(mod, f"run_local_{domain}_evaluations")
    results = run_fn(cases)

    passed = sum(1 for r in results if r["passed"])
    failed_count = len(results) - passed
    pass_rate = round(passed / len(results), 3) if results else 0.0
    out_path = _write_results(domain, "chroma", results, {"retrieval_backend": "chroma"})
    logger.info("Results written to %s", out_path)
    logger.info("Summary: %d/%d passed (%.0f%%)", passed, len(results), pass_rate * 100)
    _log_case_results(results)
    return 0 if failed_count == 0 else 1


def _run_langsmith(domain: str, cases_path: str | None, ci_mode: bool) -> int:
    mod = _load_module(domain)
    langsmith_fn = getattr(mod, f"run_langsmith_{domain}_evaluations", None)
    if langsmith_fn is None:
        logger.error("No LangSmith function found for domain '%s'", domain)
        return 1
    langsmith_fn()
    return 0


_BACKEND_RUNNERS = {
    "local": _run_local,
    "claude": _run_claude,
    "chroma": _run_chroma,
}


def main() -> None:
    domains = _discover_domains()

    parser = argparse.ArgumentParser(
        description=(
            "Unified AI-OS eval runner. Auto-discovers domains from "
            "packages/shared/evaluations/."
        ),
    )
    parser.add_argument(
        "--domain",
        choices=domains + ["all"],
        default="all",
        help=f"Domain to evaluate, or 'all'. Discovered: {', '.join(domains)}.",
    )
    parser.add_argument(
        "--backend",
        choices=["local", "claude", "chroma"],
        default="local",
        help="Retrieval/model backend (default: local).",
    )
    parser.add_argument(
        "--langsmith",
        action="store_true",
        help="Upload to LangSmith instead of running locally (requires LANGSMITH_API_KEY).",
    )
    parser.add_argument(
        "--cases-path",
        default=None,
        help="Override the eval cases JSON path (single-domain runs only).",
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Skip gracefully when API keys or ChromaDB index are absent.",
    )
    args = parser.parse_args()

    if args.cases_path and args.domain == "all":
        parser.error("--cases-path requires --domain <specific-domain>")

    targets = domains if args.domain == "all" else [args.domain]
    exit_code = 0

    for domain in targets:
        tag = "langsmith" if args.langsmith else args.backend
        logger.info("=== %s [%s] ===", domain, tag)
        if args.langsmith:
            code = _run_langsmith(domain, args.cases_path, args.ci)
        else:
            runner = _BACKEND_RUNNERS[args.backend]
            code = runner(domain, args.cases_path, args.ci)
        if code != 0:
            exit_code = code

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
