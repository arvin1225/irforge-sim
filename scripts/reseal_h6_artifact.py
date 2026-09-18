"""Refresh H6's code fingerprint after outcome-neutral tooling refactors."""

from __future__ import annotations

import argparse
import json

from irforge_sim.validation_v2 import reseal_h6_code_hash


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="artifacts/confirmatory-h6")
    args = parser.parse_args()
    print(json.dumps(reseal_h6_code_hash(args.path), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
