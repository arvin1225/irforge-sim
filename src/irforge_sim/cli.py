"""Command-line entry points for simulation, benchmarking and validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .benchmark import run_benchmark
from .image_formation import generate_sample
from .validation import validate_artifact


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="irforge", description="Infrared composed-shift simulation benchmark")
    subparsers = parser.add_subparsers(dest="command", required=True)
    simulate = subparsers.add_parser("simulate", help="generate one deterministic scene")
    simulate.add_argument("--family", default="nominal")
    simulate.add_argument("--seed", type=int, default=0)
    simulate.add_argument("--out", type=Path, default=Path("sample.npz"))

    benchmark = subparsers.add_parser("benchmark", help="run the frozen or quick benchmark")
    benchmark.add_argument("--out", type=Path, default=Path("artifacts/confirmatory"))
    benchmark.add_argument("--quick", action="store_true")
    benchmark.add_argument("--no-ablations", action="store_true")

    validate = subparsers.add_parser("validate", help="validate hashes, splits and deterministic replay")
    validate.add_argument("--artifact", type=Path, default=Path("artifacts/confirmatory"))
    validate.add_argument("--quick", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "simulate":
        sample = generate_sample(args.seed, args.family)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            args.out,
            image=sample.image,
            target_mask=sample.target_mask,
            target_xy=np.array(sample.target_xy if sample.target_xy else (-1, -1)),
            metadata=json.dumps({**sample.config.as_dict(), "seed": sample.seed, "has_target": sample.has_target, "latent_contrast": sample.latent_contrast}),
        )
        print(json.dumps({"output": str(args.out), "family": args.family, "seed": args.seed, "has_target": sample.has_target}, indent=2))
        return 0
    if args.command == "benchmark":
        result = run_benchmark(
            args.out,
            seeds_per_family=8 if args.quick else 80,
            train_per_family=8 if args.quick else 24,
            calibration_per_family=6 if args.quick else 16,
            bootstrap_resamples=250 if args.quick else 5000,
            include_ablations=not args.no_ablations,
        )
        print(json.dumps({"output": str(args.out), "rows": result["manifest"]["row_count"], "registered_success": result["summary"]["registered_success"]}, indent=2))
        return 0
    report = validate_artifact(args.artifact, quick=args.quick)
    print(json.dumps(report, indent=2))
    return 0 if report["integrity"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

