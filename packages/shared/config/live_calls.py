"""Guard for eval runs that would call the live Anthropic API.

Rule: **no `--allow-live` flag, no live call.**

The eval runners load `.env` themselves (`os.environ.setdefault`), so whether
`ANTHROPIC_API_KEY` is "set" depends on a file, not on the shell. Gating live
calls on the key's presence therefore made a CI-mode run with the key unset in
the shell still call the API. Live calls now require an explicit per-run flag.
The key is checked only after that.

`--ci` only changes how a refusal is reported: a clean skip (exit 0) in CI, an
error (exit 1) for an interactive run, so a missing flag is never mistaken for
a passing eval.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

ALLOW_LIVE_FLAG = "--allow-live"
ALLOW_LIVE_HELP = (
    "Permit live Anthropic API calls for this run (costs money). Without this flag "
    "the Claude eval path never runs, even if ANTHROPIC_API_KEY is set in .env."
)


def check_live_claude_run(*, allow_live: bool, ci_mode: bool, what: str) -> int | None:
    """Decide whether a live Claude eval run may proceed.

    Returns None to proceed, or the exit code the caller should stop with.
    """
    if not allow_live:
        message = f"{what}: live Anthropic API calls need {ALLOW_LIVE_FLAG}."
        if ci_mode:
            logger.info("%s Skipping in CI.", message)
            return 0
        logger.error("%s Re-run with %s to opt in.", message, ALLOW_LIVE_FLAG)
        return 1

    if not os.getenv("ANTHROPIC_API_KEY"):
        message = f"{what}: {ALLOW_LIVE_FLAG} was passed but ANTHROPIC_API_KEY is not set."
        if ci_mode:
            logger.info("%s Skipping in CI.", message)
            return 0
        logger.error("%s Add it to .env to run live Claude evaluations.", message)
        return 1

    logger.warning("%s: making live Anthropic API calls (%s).", what, ALLOW_LIVE_FLAG)
    return None
