"""Print or snapshot every domain's model-facing tool definition as JSON.

    python -m packages.shared.domains            # print to stdout
    python -m packages.shared.domains --write    # regenerate the committed snapshot

Regenerate the snapshot after deliberately changing a tool description or
input schema; the diff in review shows exactly what models will now see.
"""

import argparse
import json
import sys
from pathlib import Path

from packages.shared.domains import tool_definitions

SNAPSHOT_PATH = (
    Path(__file__).resolve().parents[3] / "tests" / "snapshots" / "domain_tool_definitions.json"
)


def render() -> str:
    return json.dumps(tool_definitions(), indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help=f"write {SNAPSHOT_PATH.name}")
    args = parser.parse_args()

    if args.write:
        SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_PATH.write_text(render(), encoding="utf-8", newline="\n")
        print(f"Wrote {SNAPSHOT_PATH}")
    else:
        sys.stdout.buffer.write(render().encode("utf-8"))


if __name__ == "__main__":
    main()
