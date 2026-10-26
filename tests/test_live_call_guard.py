"""The eval runners never call the live Anthropic API without --allow-live.

Regression guard for the case where `--backend claude --ci` with the key unset
in the shell still made live calls, because the runners load `.env` themselves.

The runner tests execute the real scripts in a subprocess. Each subprocess gets
an explicit fake ANTHROPIC_API_KEY (so `.env`'s setdefault cannot substitute a
real one) and an unroutable ANTHROPIC_BASE_URL, so even a regressed guard could
not reach the API from this test suite.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from packages.shared.config.live_calls import check_live_claude_run

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("allow_live", "has_key", "ci_mode", "expected"),
    [
        (False, True, True, 0),  # key in .env, CI: skip
        (False, True, False, 1),  # key in .env, interactive: refuse
        (False, False, True, 0),
        (False, False, False, 1),
        (True, False, True, 0),  # opted in but no key, CI: skip
        (True, False, False, 1),  # opted in but no key, interactive: error
        (True, True, True, None),  # opted in with key: proceed
        (True, True, False, None),
    ],
)
def test_check_live_claude_run(monkeypatch, allow_live, has_key, ci_mode, expected) -> None:
    if has_key:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-not-a-real-key")
    else:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert check_live_claude_run(allow_live=allow_live, ci_mode=ci_mode, what="t") == expected


def _run(*args: str) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "ANTHROPIC_API_KEY": "sk-ant-test-not-a-real-key",
        "ANTHROPIC_BASE_URL": "http://127.0.0.1:9",
    }
    return subprocess.run(
        [sys.executable, *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.mark.parametrize(
    ("args", "expected_code"),
    [
        (("scripts/run_evals.py", "--domain", "planner", "--backend", "claude", "--ci"), 0),
        (("scripts/run_evals.py", "--domain", "planner", "--backend", "claude"), 1),
        (("scripts/run_brand_os_evals_claude.py", "--ci"), 0),
        (("scripts/run_director_os_evals_claude.py",), 1),
        (("scripts/run_director_os_evals.py", "--provider", "claude"), 1),
    ],
    ids=["unified-ci", "unified", "brand-script-ci", "director-script", "director-provider"],
)
def test_runners_refuse_live_calls_without_allow_live(args, expected_code) -> None:
    before = _claude_results_snapshot()

    result = _run(*args)

    output = result.stdout + result.stderr
    assert result.returncode == expected_code, output
    assert "--allow-live" in output
    # Nothing was evaluated, so no domain's results file was created or rewritten.
    assert _claude_results_snapshot() == before


def _claude_results_snapshot() -> dict[str, bytes | None]:
    """Content of every evaluations/<domain>/results_claude.json, None if absent."""
    snapshot: dict[str, bytes | None] = {}
    for domain_dir in sorted((REPO_ROOT / "evaluations").iterdir()):
        if not domain_dir.is_dir():
            continue
        path = domain_dir / "results_claude.json"
        snapshot[domain_dir.name] = path.read_bytes() if path.exists() else None
    return snapshot
