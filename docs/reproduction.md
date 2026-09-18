# Reproduction guide

## Environment

- Python 3.10 or newer
- NumPy, SciPy and scikit-learn from `pyproject.toml`
- Matplotlib only for figures/dashboard image export
- Node 20+ and pnpm for the optional web build

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[plot]"
python -m unittest discover -s tests -v
```

## Fast deterministic checks

```powershell
irforge simulate --family attenuation_contrast --seed 1002 --out sample.npz
python scripts/validate_artifact.py --artifact artifacts/confirmatory --quick
python scripts/validate_artifact.py --artifact artifacts/replication-h5 --quick
python scripts/validate_h6_artifact.py artifacts/confirmatory-h6
```

Remove `--quick` to refit the source system and replay selected output rows. Images and labels are bitwise deterministic; refitted selective-risk scores must match within `1e-6` because supported scikit-learn/BLAS builds can differ in their final decimal places.

The H6 validator always checks the complete 34,560-row matrix, calibration contracts, hashes and two deterministic sequence replays.

## Publication outputs

```powershell
$env:MPLBACKEND="Agg"
python figures/gen_fig_failure_atlas.py
python figures/gen_fig_sensor_shift_gallery.py
python scripts/export_dashboard.py
```

Both figures are exported as vector PDF and 300-DPI PNG. Dashboard JSON includes downsampled risk–coverage curves derived from the committed CSVs; sample PNGs are regenerated from their exact family/seed pairs.

## Web build

```powershell
cd web
pnpm install
pnpm run build
pnpm run preview
```

Vite uses a relative base so the artifact can be hosted under a GitHub Pages repository path.

## Full studies

The commands below rewrite an output directory. Preserve the committed study before intentionally rerunning it.

```powershell
python scripts/run_benchmark.py --out artifacts/confirmatory
python scripts/run_quality_replication.py
```

Expected row count is 4,400 per full matrix. A new scientific question should use a new protocol directory, seed range and artifact directory rather than silently replacing these studies.
