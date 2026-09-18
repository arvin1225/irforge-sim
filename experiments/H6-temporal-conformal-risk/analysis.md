# H6 confirmatory analysis

## Registered outcome

H6 is a negative joint confirmation with one supported detector-baseline effect.
The final matrix contains 34,560 rows: 360 independent evaluation sequences,
12 frames and eight methods.

### H6-A — matched control failed on utility

On 120 matched-drift sequences, `crc_temporal` made three sequence-level false
releases (`2.5%`, one-sided 95% Wilson upper `6.09%`), well below the registered
risk limits. It accepted only `4.79%` of frames, below the required 15% coverage,
so H6-A failed. The formal controller was safe by abstention, not usefully safe.

All three calibration controllers operated at the edge of the finite-sample
rule: 11 loss sequences out of 120, corrected risk `(11 + 1)/(120 + 1) =
0.09917` under alpha `0.10`. Calibration frame coverage was `4.10%` for
confidence CRC, `1.88%` for quality CRC and `6.32%` for temporal CRC.

### H6-B — held-out transfer failed

On 240 unseen drift-composition sequences, temporal CRC produced 37 sequence
false releases (`15.42%`) versus confidence CRC's 31 (`12.92%`) at closely
matched frame coverage (`5.07%` versus `4.24%`). Relative risk reduction was
therefore negative (`-19.35%`). This is direct evidence against exporting the
matched exchangeability claim to new sensor-drift compositions.

Quality CRC accepted no held-out frames. That zero-error outcome is vacuous and
is reported as a transfer failure, not as perfect safety. The naive calibration
80%-quantile threshold transferred in the opposite direction and accepted every
held-out frame, yielding `77.92%` sequence false-release probability.

### H6-C — ranking signal was inconclusive

At the temporal controller's exact `5.07%` held-out frame coverage, temporal
risk lowered the frame-error point estimate by `9.59` percentage points versus
confidence risk. The paired sequence-bootstrap interval was
`[-23.97, +4.11]` points and crossed zero, so H6-C failed.

### H6-D — causal temporal baseline passed

The causal running-background residual improved target-present localization
over the stronger classical frame baseline in `compound_aging` and
`oscillatory_gain` (two of three held-out families) while satisfying the
registered twofold false-alarm budget. It tied local contrast under bad-pixel
bloom. This is a baseline result, not a claim of competitive IRSTD accuracy.

### H6-E — integrity passed

The validator passed artifact and summary hashes, current code fingerprint,
34,560-cell completeness, calibration/evaluation disjointness, finite metrics,
all three conformal calibration contracts, recomputed hypotheses, and exact
image/mask/drift hashes for one matched and one held-out sequence. The full test
suite contains 21 passing tests.

## Research conclusion

Sequence-level CRC correctly exposes the coverage price of controlling an
"any accepted error" mission loss. Observable temporal drift improved matched
risk ranking but did not make the controller distribution-free across new drift
compositions. The technically justified next direction is online recalibration
or covariate-shift-aware risk control with explicit drift alarms, evaluated on
measured sequences; lowering alpha or retuning the existing blend would not
resolve the exchangeability failure.

