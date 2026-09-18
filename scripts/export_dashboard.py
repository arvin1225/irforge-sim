"""Export browser-ready curves and exact deterministic sensor frames."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.image as mpimg
import numpy as np

from irforge_sim.image_formation import generate_sample
from irforge_sim.metrics import aurc, risk_coverage_curve


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
FAMILIES = ("blur_noise", "attenuation_contrast", "badpixel_fpn", "clutter_blur", "triple_shift")
MODES = ("confidence_selective", "shift_selective", "quality_selective")


def read_rows(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            rows.append(
                {
                    **raw,
                    "seed": int(raw["seed"]),
                    "error": raw["error"].lower() == "true",
                    "has_target": raw["has_target"].lower() == "true",
                    "localized": raw["localized"].lower() == "true",
                    "accepted": raw["accepted"].lower() == "true",
                    "risk_score": float(raw["risk_score"]),
                    "confidence": float(raw["confidence"]),
                    "target_x": int(raw["target_x"]),
                    "target_y": int(raw["target_y"]),
                    "peak_x": int(raw["peak_x"]),
                    "peak_y": int(raw["peak_y"]),
                }
            )
    return rows


def risk_data(rows: list[dict[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for mode in MODES:
        subset = [row for row in rows if row["mode"] == mode]
        errors = np.array([row["error"] for row in subset], dtype=float)
        risks = np.array([row["risk_score"] for row in subset], dtype=float)
        coverage, conditional = risk_coverage_curve(errors, risks)
        idx = np.linspace(0, len(coverage) - 1, 81).astype(int)
        result[mode] = {
            "aurc": aurc(errors, risks),
            "curve": [[round(float(coverage[i]), 5), round(float(conditional[i]), 5)] for i in idx],
        }
    return result


def fixed_risk(rows: list[dict[str, object]], coverage: float = 0.8) -> float:
    errors = np.array([row["error"] for row in rows], dtype=float)
    risks = np.array([row["risk_score"] for row in rows], dtype=float)
    keep = max(1, int(round(coverage * len(rows))))
    return float(np.mean(errors[np.argsort(risks, kind="stable")[:keep]]))


def family_data(rows: list[dict[str, object]]) -> dict[str, object]:
    result = {}
    for family in FAMILIES:
        modes = {}
        for mode in MODES:
            subset = [row for row in rows if row["family"] == family and row["mode"] == mode]
            errors = np.array([row["error"] for row in subset], dtype=float)
            risks = np.array([row["risk_score"] for row in subset], dtype=float)
            modes[mode] = {"aurc": aurc(errors, risks), "risk80": fixed_risk(subset)}
        result[family] = modes
    return result


def export_samples(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    sample_dir = WEB / "public" / "samples"
    sample_dir.mkdir(parents=True, exist_ok=True)
    exported: list[dict[str, object]] = []
    learned = [row for row in rows if row["mode"] == "quality_selective"]
    for family in FAMILIES:
        family_rows = [row for row in learned if row["family"] == family and row["has_target"]]
        candidates = []
        for desired_error in (True, False):
            match = next((row for row in family_rows if row["error"] == desired_error), None)
            if match is not None:
                candidates.append(match)
        for row in candidates:
            sample = generate_sample(int(row["seed"]), family)
            low, high = np.percentile(sample.image, [1, 99])
            normalized = np.clip((sample.image - low) / max(1e-8, high - low), 0.0, 1.0)
            filename = f"{family}-{row['seed']}.png"
            mpimg.imsave(sample_dir / filename, normalized, cmap="gray", vmin=0.0, vmax=1.0)
            exported.append(
                {
                    "family": family,
                    "seed": row["seed"],
                    "image": f"/samples/{filename}",
                    "error": row["error"],
                    "localized": row["localized"],
                    "accepted": row["accepted"],
                    "confidence": row["confidence"],
                    "qualityRisk": row["risk_score"],
                    "target": [row["target_x"], row["target_y"]],
                    "peak": [row["peak_x"], row["peak_y"]],
                    "transmission": float(row["transmission"]),
                    "blurSigma": float(row["blur_sigma"]),
                    "readNoise": float(row["read_noise"]),
                    "badPixelFraction": float(row["bad_pixel_fraction"]),
                    "clutterStrength": float(row["clutter_strength"]),
                }
            )
    return exported


def main() -> None:
    confirmation = read_rows(ROOT / "artifacts" / "confirmatory" / "benchmark.csv")
    replication = read_rows(ROOT / "artifacts" / "replication-h5" / "benchmark.csv")
    replication_summary = json.loads((ROOT / "artifacts" / "replication-h5" / "replication-summary.json").read_text(encoding="utf-8"))
    payload = {
        "generatedFrom": ["artifacts/confirmatory/benchmark.csv", "artifacts/replication-h5/benchmark.csv"],
        "studies": {
            "confirmation": {"risk": risk_data(confirmation), "families": family_data(confirmation), "seeds": "1000–1079"},
            "replication": {"risk": risk_data(replication), "families": family_data(replication), "seeds": "2000–2079"},
        },
        "replicationDecision": replication_summary,
        "samples": export_samples(confirmation),
        "hypotheses": [
            {"id": "H1", "status": "FAIL", "label": "composed silent failure"},
            {"id": "H2", "status": "PASS", "label": "calibration ≠ ranking"},
            {"id": "H3", "status": "FAIL", "label": "threshold transfer"},
            {"id": "H4", "status": "FAIL", "label": "full-score risk gate"},
            {"id": "H5", "status": "FAIL", "label": "quality-only replication"},
        ],
    }
    output = WEB / "public" / "data"
    output.mkdir(parents=True, exist_ok=True)
    (output / "benchmark.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"samples": len(payload["samples"]), "output": str(output / "benchmark.json")}, indent=2))


if __name__ == "__main__":
    main()
