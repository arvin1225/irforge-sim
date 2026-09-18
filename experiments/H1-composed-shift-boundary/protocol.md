# Frozen protocol — H1/H2/H3 composed sensor-shift benchmark

Status: **CONFIRMATORY PROTOCOL — lock before results**  
Date: 2026-08-03

## Question

Which combinations of blur, read/shot noise, fixed-pattern noise, bad pixels, atmospheric attenuation, target contrast and structured clutter cause infrared small-target detectors to fail silently? Can a quality-aware selective gate reduce those errors on degradation compositions absent from training and calibration?

## Splits

- exploratory training/calibration seeds: `0–239`;
- frozen confirmatory seeds: `1000–1079` for every held-out family;
- training contains nominal and isolated/single-axis degradations only;
- confirmatory families contain paired or triple compositions; their named ranges are not used to fit detector weights, score temperature, detection threshold, or acceptance threshold.

Each family contains a balanced deterministic mixture of target-present and target-absent images. Images are `64 x 64` and all stochasticity is derived from the row seed.

## Image-formation factors

1. band-integrated Planck-radiance contrast in an 8–12 µm surrogate band;
2. exponential atmospheric transmission;
3. Gaussian optical PSF/MTF blur;
4. Poisson shot noise and additive read noise;
5. row/column fixed-pattern gain and offset;
6. bad/dead/hot pixels;
7. quantization and clipping;
8. multiscale structured background clutter and distractor glints.

These factors are controlled simulation variables, not a calibrated focal-plane-array model.

## Frozen methods

1. `local_contrast`: multiscale difference-of-Gaussians score;
2. `matched_filter`: robust-normalized Gaussian PSF response;
3. `learned_raw`: logistic pixel classifier on fixed multiscale features;
4. `learned_calibrated`: same predictions with temperature-scaled image confidence;
5. `shift_selective`: same detector plus an error-risk model using calibrated confidence and image-quality shift features; it may abstain but may not change the detection map.

## Thresholds

- detection thresholds maximize target-level F1 on validation data only;
- temperature minimizes validation binary NLL;
- acceptance thresholds target 80% validation coverage;
- confirmatory thresholds are never refit per family.

## Metrics

- target-level probability of detection (`Pd`);
- false alarms per image (`Fa/image`);
- target-level F1;
- expected calibration error (`ECE`, 10 equal-width bins);
- area under empirical risk–coverage curve (`AURC`);
- selective coverage and conditional error;
- silent-failure rate: incorrect accepted decision with reported confidence `>= 0.80`;
- seed-level paired bootstrap intervals with 5,000 resamples.

## Hypotheses and gates

- **H1:** at least two held-out composed families have higher silent-failure rate than the strongest isolated-shift validation family.
- **H2:** temperature scaling improves pooled ECE but does not improve AURC by more than 5% relative.
- **H3:** `shift_selective` lowers pooled conditional error by at least 20% relative to confidence-only selection at coverage within ±10 percentage points, with a paired bootstrap interval excluding zero.
- **H4 (outer-loop amendment, locked before confirmation):** quality-aware risk lowers pooled AURC by at least 5% relative to calibrated confidence and has lower conditional error when both rankings are evaluated at exactly 80% pooled coverage. A paired seed bootstrap interval for the fixed-coverage error difference must exclude zero.

H4 was added after exploratory runs showed that error ranking can improve even when a validation-set absolute threshold does not preserve coverage. It does not replace or retroactively pass H3. The strict original claim fails if H3 fails, if its coverage mismatch exceeds the gate, or if any method uses confirmatory labels for selection. The narrower failure-ranking contribution requires both H2 and H4.

## Registered ablations

- confidence-only acceptance;
- quality-only acceptance;
- confidence + quality without interaction terms;
- full confidence + quality + interaction risk model;
- no calibration;
- no bad-pixel quality feature;
- no frequency/clutter quality feature.

## Negative controls

- target coordinates shuffled before localization scoring;
- target radiance contrast set to zero;
- quality feature rows permuted before gate fitting;
- identical seed replay must reproduce image and metrics byte-for-byte.

## Claim boundary

This protocol can support claims about the registered synthetic generator and method ranking inside it. It cannot establish real detector range, MRTD, atmospheric validity, sensor safety, or cross-device generalization.
