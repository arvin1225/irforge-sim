"""Analyze the committed H6 decisions without refitting or changing thresholds."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from irforge_analysis.paired_sequences import compare_sequences


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=ROOT / "artifacts/confirmatory-h6/benchmark_h6.csv")
    parser.add_argument("--out", type=Path, default=ROOT / "artifacts/sequence-pair-analysis")
    args = parser.parse_args()
    with args.csv.open(newline="", encoding="utf-8") as handle:
        summary = compare_sequences(list(csv.DictReader(handle)))
    summary["source_csv_sha256"] = hashlib.sha256(args.csv.read_bytes()).hexdigest()
    summary["analysis_sha256"] = hashlib.sha256((ROOT / "src/irforge_analysis/paired_sequences.py").read_bytes()).hexdigest()
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    lines = ["# Temporal selector comparison", "", "Exploratory paired analysis of fixed H6 outputs. Each resample preserves the complete 12-frame sequence, both selectors, and the family stratum. Intervals are pointwise; they do not imply robustness to a new drift distribution.", "", "| Regime | Sequences | Metric | Temporal − confidence | 95% interval |", "|---|---:|---|---:|---:|"]
    for regime, data in summary["regimes"].items():
        for name, metric in data["paired_difference"].items():
            lines.append(f"| {regime} | {data['sequences']} | {name} | {100*metric['estimate']:.2f} pp | [{100*metric['ci_low']:.2f}, {100*metric['ci_high']:.2f}] |")
    lines += ["", "Lower sequence false release is better. Higher coverage and correct releases per input frame are better. Report all three: rejecting every frame has zero observed false release and zero utility.", "", f"Source SHA-256: `{summary['source_csv_sha256']}`", ""]
    (args.out / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary["regimes"], indent=2))


if __name__ == "__main__":
    main()
