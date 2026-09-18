"""Validate the frozen H6 artifact."""

from __future__ import annotations

import argparse
import json

from irforge_sim.validation_v2 import validate_h6_artifact


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="artifacts/confirmatory-h6")
    args = parser.parse_args()
    report = validate_h6_artifact(args.path)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["integrity"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

