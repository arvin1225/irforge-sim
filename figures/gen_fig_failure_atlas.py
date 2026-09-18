"""Generate the registered IRForge risk/coverage result figure from immutable CSVs."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from irforge_sim.metrics import aurc, risk_coverage_curve


ROOT = Path(__file__).resolve().parents[1]
STUDIES = {
    "Confirmation": ROOT / "artifacts" / "confirmatory" / "benchmark.csv",
    "Replication": ROOT / "artifacts" / "replication-h5" / "benchmark.csv",
}
MODES = {
    "confidence_selective": ("Confidence", "#0072B2", "o"),
    "shift_selective": ("Confidence + quality", "#E69F00", "s"),
    "quality_selective": ("Quality only", "#009E73", "^"),
}
FAMILIES = ("blur_noise", "attenuation_contrast", "badpixel_fpn", "clutter_blur", "triple_shift")


def load_rows(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            rows.append(
                {
                    **raw,
                    "seed": int(raw["seed"]),
                    "error": raw["error"].lower() == "true",
                    "risk_score": float(raw["risk_score"]),
                }
            )
    return rows


def select(rows: list[dict[str, object]], mode: str, family: str | None = None) -> list[dict[str, object]]:
    return [row for row in rows if row["mode"] == mode and (family is None or row["family"] == family)]


def arrays(rows: list[dict[str, object]]) -> tuple[np.ndarray, np.ndarray]:
    return np.array([row["error"] for row in rows], dtype=float), np.array([row["risk_score"] for row in rows], dtype=float)


def fixed_risk(rows: list[dict[str, object]], coverage: float = 0.8) -> float:
    errors, risks = arrays(rows)
    keep = max(1, int(round(coverage * len(rows))))
    order = np.argsort(risks, kind="stable")[:keep]
    return float(np.mean(errors[order]))


def style() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "DejaVu Serif"],
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.titleweight": "bold",
            "axes.labelsize": 9,
            "legend.fontsize": 7.5,
            "legend.frameon": False,
            "figure.dpi": 300,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.16,
            "grid.linestyle": "-",
        }
    )


def main() -> None:
    style()
    data = {study: load_rows(path) for study, path in STUDIES.items()}
    fig, axes = plt.subplots(1, 3, figsize=(6.75, 2.65), gridspec_kw={"width_ratios": [1.17, 1.0, 1.08]})

    ax = axes[0]
    confirmation = data["Confirmation"]
    for mode, (label, color, marker) in MODES.items():
        errors, risks = arrays(select(confirmation, mode))
        coverage, conditional = risk_coverage_curve(errors, risks)
        indices = np.linspace(0, len(coverage) - 1, 45).astype(int)
        ax.plot(coverage, conditional, color=color, label=label, linewidth=1.8)
        ax.scatter(coverage[indices[::9]], conditional[indices[::9]], color=color, marker=marker, s=12, zorder=3)
    ax.axvline(0.8, color="#6B7280", linestyle="--", linewidth=0.9)
    ax.text(0.805, 0.31, "registered\n80%", color="#6B7280", fontsize=6.7, va="bottom")
    ax.set_xlim(0.05, 1.0)
    ax.set_ylim(0.2, 0.72)
    ax.set_xlabel("Coverage")
    ax.set_ylabel("Conditional error")
    ax.set_title("a  Risk–coverage / confirmation", loc="left")
    ax.legend(loc="upper left")

    ax = axes[1]
    x = np.arange(3)
    width = 0.34
    for index, (study, rows) in enumerate(data.items()):
        values = []
        for mode in MODES:
            errors, risks = arrays(select(rows, mode))
            values.append(aurc(errors, risks))
        bars = ax.bar(x + (index - 0.5) * width, values, width * 0.88, color=("#8AA4B0" if index == 0 else "#264653"), label=study)
        for bar, value in zip(bars, values, strict=True):
            ax.text(bar.get_x() + bar.get_width() / 2, value - 0.012, f"{'C' if index == 0 else 'R'}\n{value:.3f}", ha="center", va="top", fontsize=6.0, color="white", fontweight="bold")
    ax.set_xticks(x, ["Confidence", "Conf. +\nquality", "Quality\nonly"])
    ax.set_ylim(0.0, 0.59)
    ax.set_ylabel("AURC ↓")
    ax.set_title("b  Pooled AURC", loc="left")
    ax.text(0.98, 0.035, "H4 FAIL · H5 FAIL", transform=ax.transAxes, ha="right", va="bottom", color="#D55E00", fontsize=6.7, fontweight="bold")

    ax = axes[2]
    matrix = np.zeros((2, len(FAMILIES)))
    for study_index, rows in enumerate(data.values()):
        for family_index, family in enumerate(FAMILIES):
            matrix[study_index, family_index] = fixed_risk(select(rows, "quality_selective", family)) - fixed_risk(
                select(rows, "confidence_selective", family)
            )
    image = ax.imshow(matrix, cmap="PiYG_r", vmin=-0.25, vmax=0.25, aspect="auto")
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = matrix[i, j]
            ax.text(j, i, f"{value:+.2f}", ha="center", va="center", fontsize=7, color=("white" if abs(value) > 0.15 else "#17212B"))
    ax.set_xticks(np.arange(len(FAMILIES)), ["blur +\nnoise", "atten. +\ncontrast", "bad pixel +\nFPN", "clutter +\nblur", "triple\nshift"], fontsize=6.6)
    ax.set_yticks([0, 1], ["Confirm.", "Replic."])
    ax.set_title("c  Family Δerror @ 80%", loc="left")
    colorbar = fig.colorbar(image, ax=ax, fraction=0.045, pad=0.03)
    colorbar.set_label("quality − confidence error", fontsize=7)
    colorbar.ax.tick_params(labelsize=6.5)
    ax.grid(False)

    fig.suptitle("IRForge-Sim: calibration improves while global failure ranking remains unresolved", fontsize=9.6, fontweight="bold", y=0.965)
    fig.subplots_adjust(left=0.072, right=0.985, bottom=0.24, top=0.79, wspace=0.34)
    fig.savefig(ROOT / "figures" / "fig_failure_atlas.pdf")
    fig.savefig(ROOT / "figures" / "fig_failure_atlas.png", dpi=300)
    plt.close(fig)


if __name__ == "__main__":
    main()
