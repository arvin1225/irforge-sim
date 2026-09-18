# Architecture

## 1. Image formation

For wavelength `λ` and temperature `T`, spectral radiance follows Planck's law

`L_λ(T) = 2hc² / [λ⁵(exp(hc/(λkT)) − 1)]`.

IRForge integrates this surrogate over the `8–12 μm` band. Atmospheric transmission is

`τ = exp(−κd)`,

where `κ` is a sampled extinction coefficient and `d` is path length. The target/background mixture reaches the sensor as

`L_sensor = τL_scene + (1−τ)L_path`.

The spatial target is subpixel-scale before convolution. A Gaussian PSF models optical blur. Shot noise is sampled in electron space; additive read noise, multiplicative/additive fixed-pattern noise, partial hot/dead pixels, clipping and 12-bit quantization follow. These are controlled surrogates, not parameters fitted to a fielded device.

## 2. Shift design

Source fitting uses nominal and five single-axis families. Confirmation uses five compositions that never appear during fitting:

| Family | Shift axes |
|---|---|
| `blur_noise` | PSF width, read noise, shot-electron count |
| `attenuation_contrast` | extinction/path length, target ΔT |
| `badpixel_fpn` | partial defects, gain/offset FPN |
| `clutter_blur` | structured distractors, PSF width |
| `triple_shift` | attenuation/contrast, blur, noise, clutter |

The family is sampled before image generation and is never inferred from labels during evaluation.

## 3. Detection stack

- **Local contrast:** maximum over three difference-of-Gaussian scales with robust-MAD normalization.
- **Matched filter:** local-energy-normalized small-PSF response.
- **Learned baseline:** histogram gradient booster on seven fixed pixel features: intensity, two DoG scales, variance-normalized DoG, gradient magnitude, Laplacian and local variance.

The learned baseline uses deterministic hard-negative mining so defect pixels, glints and edges are represented during source fitting. Thresholds are selected from a fixed candidate grid on the calibration split.

## 4. Calibration and selective prediction

Temperature scaling transforms raw decision confidence. Image-quality features measure residual-noise MAD, row/column pattern, extreme-pixel fraction, high-frequency energy, clutter peaks and dynamic range.

Three primary risk orderings are audited:

- `R_conf = 1 − calibrated_confidence`;
- `R_quality = g(q)`;
- `R_full = 0.65 R_conf + 0.35 g(confidence, q, confidence×q)`.

An acceptance threshold is fitted only on calibration data. A separate exact-coverage evaluator sorts by risk and accepts the safest `k = round(cn)` samples, allowing rankings to be compared at identical coverage without retuning a threshold.

## 5. Evidence and replay

Each row records family, seed, target state/location, detector peak, localization, false alarms, error, confidence, risk, acceptance, silent failure and sampled sensor factors. A study manifest binds:

- protocol path;
- training/calibration/evaluation seed ranges;
- thresholds and temperature;
- source, CSV and summary SHA-256 hashes;
- row count and enabled modes.

Independent validation regenerates selected frames and rows exactly. The zero-contrast control verifies that the target radiance injection disappears when `ΔT = 0`.
