# H6 protocol — sequence-level conformal risk under sensor drift

Status: **locked before implementation and outcome inspection**  
Lock date: 2026-08-13

## Research question

Can a sequence-level conformal risk controller wrap a fixed infrared detector
and limit the probability of at least one accepted wrong decision in a
temporally correlated mission window, while retaining useful coverage under
sensor drift? Does an observable temporal-drift score transfer better than
confidence alone to unseen drift compositions?

The study uses synthetic 12-frame LWIR-like sequences and does not claim a
fielded-sensor guarantee or state-of-the-art target detector.

## Frozen data split

- The H1/H5 learned pixel detector, threshold and source calibration pipeline
  remain unchanged.
- Conformal calibration unit: an entire 12-frame sequence. Frames within a
  sequence may be dependent; sequences are generated independently.
- Calibration drift families: `gain_ramp`, `fpn_ramp`, `blur_creep`, 40
  sequences each, seeds 3000–3039.
- Matched-drift confirmation: the same three families, 40 new sequences each,
  seeds 3500–3539.
- Held-out composition confirmation: `bad_pixel_bloom`, `oscillatory_gain`,
  `compound_aging`, 80 sequences each, seeds 4000–4079.
- No sequence or label from either confirmation block may set a threshold.

## Drift and motion contract

A sequence starts from one replayable scene. Subpixel target/scene motion,
read-noise innovation and sensor state evolve deterministically from the
sequence seed. Registered drifts modify gain/offset, row/column fixed-pattern
noise, blur, defective-pixel population, or a frozen composition of these.
All transformed target coordinates and masks are carried into evaluation.

## Frozen methods

Detector baselines:

1. `local_contrast_frame`: existing single-frame local-contrast baseline.
2. `matched_filter_frame`: existing single-frame matched-filter baseline.
3. `learned_frame`: fixed H1 learned detector.
4. `temporal_residual`: causal running-background residual baseline.

Selective controllers wrapping the fixed learned detector:

5. `fixed80_confidence`: calibration 80%-quantile confidence-risk threshold.
6. `crc_confidence`: sequence conformal risk control using calibrated
   confidence risk.
7. `crc_quality`: sequence conformal risk control using H5 image-quality risk.
8. `crc_temporal`: sequence conformal risk control using a fixed combination of
   quality risk, confidence risk and observable drift/temporal-instability
   features.

`crc_temporal` weights are frozen at `0.50 quality + 0.25 confidence + 0.25
temporal`. No confirmation-family identifier or hidden drift parameter is an
input.

## Conformal risk rule

For threshold `lambda`, accept frames with risk score `<= lambda`. Each
calibration sequence has bounded loss

`L(lambda) = 1{any accepted frame is a wrong target-level decision}`.

For `n` independent calibration sequences, select the largest candidate
threshold satisfying

`(n * mean(L(lambda)) + 1) / (n + 1) <= alpha`, with `alpha = 0.10`.

This finite-sample conformal risk-control correction is applied to bounded
sequence loss. Its exchangeability interpretation is evaluated only on the
matched-drift block. Held-out compositions are a stress test, not covered by the
same guarantee.

## Registered hypotheses

- **H6-A matched control:** `crc_temporal` has matched-drift sequence
  false-release probability at most 0.10, one-sided 95% Wilson upper bound at
  most 0.15, and frame coverage at least 0.15.
- **H6-B held-out robustness:** on held-out compositions, `crc_temporal`
  reduces sequence false-release probability by at least 20% relative to
  `crc_confidence`, with absolute frame-coverage difference at most 0.10.
- **H6-C temporal value:** at exactly matched pooled frame coverage,
  `crc_temporal` has lower frame error than `fixed80_confidence`, with the 95%
  paired sequence-bootstrap interval entirely below zero.
- **H6-D standard temporal baseline:** the causal temporal-residual detector
  improves target-present localization probability over the stronger of the two
  classical single-frame baselines in at least two of three held-out families,
  without more than doubling false alarms per image.
- **H6-E integrity:** all thresholds derive only from the calibration block;
  hashes, sequence/frame completeness, deterministic replay and split
  disjointness pass.

Every hypothesis may fail. Thresholds and weights are not changed after either
confirmation block is opened.

## Metrics and reporting

Primary metrics are sequence false-release probability, its one-sided Wilson
upper bound, and frame coverage. Secondary metrics include frame conditional
error, target-present Pd, false alarms/image, AURC, coverage by time, and drift
alarm magnitude. Results are paired by `(regime, family, sequence_seed)`.

## Claim boundary

The controller can validate only the registered synthetic generator and
exchangeability unit. It cannot establish safety for measured imagery,
non-exchangeable deployment drift, or a real camera without new calibration and
external validation.

