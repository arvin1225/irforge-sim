"""Run the frozen IRForge H6 temporal conformal-risk confirmation."""

from __future__ import annotations

import argparse
import json

from irforge_sim.benchmark_v2 import run_h6_benchmark


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="artifacts/confirmatory-h6")
    parser.add_argument("--bootstrap", type=int, default=5000)
    args = parser.parse_args()
    result = run_h6_benchmark(args.out, bootstrap_resamples=args.bootstrap)
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

