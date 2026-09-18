# Frozen replication protocol — H5 quality-only error ranking

Status: **LOCKED BEFORE REPLICATION**  
Date: 2026-08-03

## Motivation

The first confirmatory matrix on seeds `1000–1079` rejected H1, H3 and H4. A preregistered ablation produced one unanticipated result: the `quality_selective` score had AURC `0.4316`, compared with `0.5047` for calibrated confidence and `0.4680` for the full confidence–quality blend. This suggests that confidence may dilute a useful global sensor-quality signal under composition shift.

This is a new replication hypothesis. The first confirmatory rows motivate it but cannot confirm it.

## Frozen replication

- untouched seeds: `2000–2079` for each of the same five composed-shift families;
- identical generator, learned detector, calibration split, thresholds, quality features and gate weights;
- no refitting, hyperparameter change or family-specific threshold;
- primary comparison: `quality_selective` versus `confidence_selective` error ranking;
- 5,000 paired seed bootstrap resamples.

## H5 gate

H5 passes only if:

1. pooled quality-only AURC is at least 10% lower than confidence-only AURC;
2. the paired bootstrap 95% interval for `AURC_quality − AURC_confidence` is entirely below zero;
3. integrity replay and split-disjointness checks pass.

Fixed 80% coverage error is reported as a secondary diagnostic and is not a pass condition because the prior matrix showed the effect is distributed across the curve rather than concentrated at one operating point.

## Claim boundary

A pass would support reproducibility of a synthetic error-ranking effect. It would not validate an operating threshold, real-sensor failure prediction, or a state-of-the-art infrared detector.

