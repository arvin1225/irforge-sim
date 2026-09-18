# Technical report

## Question

Which compositions of infrared image-formation degradation cause silent small-target failures, and can observable sensor-quality signals improve selective prediction under held-out composition shift?

## Experimental design

The research separates an exploratory inner loop from three frozen outer-loop studies. Detector fitting and calibration for H1–H5 use seeds below 1,000 and only nominal/single-axis families. The first confirmatory matrix uses seeds `1000–1079`; the H5 replication uses untouched seeds `2000–2079`. Each matrix contains five families, 80 seeds and 11 modes, or 4,400 rows. H6 separately evaluates 34,560 rows from deterministic 12-frame drift sequences with disjoint calibration, matched-confirmation and held-out-composition seed blocks.

Primary metrics are conditional error and AURC. Secondary metrics are target probability of detection, false alarms per image, target F1, ECE, coverage and silent-failure rate. Paired bootstraps preserve family/seed alignment.

## Confirmatory results

The detector itself is weak on difficult compositions (`Pd = 0.115`, target F1 `0.186`), which makes the benchmark a useful failure atlas but prevents a competitive detection claim.

Temperature scaling reduced ECE from `0.1405` to `0.0772` and silent failure from `0.1375` to `0.0025`; AURC remained exactly `0.5047`. The monotone transform changed calibration but could not change error ordering.

The full confidence–quality score reduced AURC to `0.4680`, a `7.28%` relative improvement, but its fixed-80%-coverage paired interval crossed zero. Its calibration-fitted threshold accepted `79.25%` of composed samples while the confidence threshold accepted all samples, demonstrating operating-point transfer failure.

## H5 replication

The unexpected confirmation ablation—quality-only AURC `0.4316`—was converted into H5 and committed before replication. H5 required at least a 10% AURC reduction and a paired interval entirely below zero.

On untouched seeds, quality-only AURC was `0.4060` versus `0.4482` for confidence: `9.41%`, with paired difference interval `[-0.0998, 0.0185]`. H5 therefore failed. At exactly 80% coverage, quality-only error was `0.4438` versus `0.4938`, difference `−0.0500`, interval `[-0.0813, −0.0156]`.

## H6 temporal drift result

H6 calibrates conformal risk control on sequence-level bounded loss: a sequence is a loss if any accepted frame is wrong. On matched drift, temporal CRC reached `2.50%` sequence false-release risk with a Wilson upper bound of `6.09%`, but accepted only `4.79%` of frames and therefore failed the registered 15% utility floor. Under unseen drift composition, temporal CRC reached `15.42%` sequence risk versus `12.92%` for confidence CRC. The causal temporal-residual detector met its registered baseline gate in two of three held-out families. These results separate matched-distribution risk control from robustness to nonexchangeable drift.

## Interpretation

The evidence rejects a broad claim that quality signals globally solve selective prediction under composition shift. It suggests a narrower mechanism near one operating region: global sensor-quality cues can remove some errors that calibrated confidence ranks poorly. This effect is now a future hypothesis, not a post-hoc success label.

## Contributions

1. A deterministic controlled LWIR-like formation model with separable degradation factors and composed held-out families.
2. An audit stack that distinguishes detector accuracy, probability calibration, risk ordering and threshold transfer.
3. Three frozen studies totaling 43,360 rows, including a failed replication and a temporal-drift stress test.
4. Bitwise image and sequence replay, tolerance-bounded selected-row replay, negative controls, manifests and a dashboard that preserves rejected hypotheses.

## Next research step

A new protocol should target the local operating-region effect directly and compare source-only thresholds with unlabeled-target coverage control. For H6, the next step is drift-aware recalibration or online change detection with a preregistered alarm budget. External validity then requires measured public infrared sequences and sensor-specific preprocessing; synthetic evidence alone cannot answer that question.
