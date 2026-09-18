# Findings

## Current understanding

The confirmatory and independent replication matrices are complete. The defensible result is a negative one with a bounded secondary effect:

- calibration and risk ranking are different problems: temperature scaling cut ECE from `0.1405` to `0.0772` but left AURC at `0.5047`;
- the full confidence–quality blend improved confirmatory AURC by `7.28%`, below the registered effect gate, and its fixed-coverage interval crossed zero;
- an unexpected quality-only advantage did not reproduce under the frozen global AURC rule: the replication improvement was `9.41%` and the interval crossed zero;
- quality-only ranking did lower error by `5.0` percentage points at exactly 80% replication coverage, with a wholly negative interval. This is a secondary, operating-region observation—not proof of a global selective predictor;
- the lightweight detector remains intentionally weak on hard compositions. The artifact is a failure-boundary instrument, not a competitive detector submission.

## Lessons and constraints

- Synthetic radiance is useful for controlled causal stress tests but cannot substitute for sensor calibration or public real-image validation.
- Detector score, calibration confidence and selective acceptance are three separate decisions and must be logged separately.
- Held-out composition families and confirmatory seeds must not be used for threshold selection.
- A detector can have useful error ranking and still have a non-transferable absolute rejection threshold. Both must be reported.
- Obvious hot/dead-pixel masking is a common preprocessing step; partial defects remain in the benchmark so masking does not erase the stress factor.
- A visually attractive dashboard must never relabel `registered_success: false` as a verified mission. The interface exposes hypothesis status, seed provenance and rejected claims alongside metrics.

## Open questions

- Why is the quality-only benefit concentrated near 80% coverage instead of spanning the full risk–coverage curve?
- Can a labeled-source, unlabeled-target conformal controller transfer coverage without consuming target labels?
- Do the same ordering failures occur on public measured infrared benchmarks after sensor-specific normalization?

## H6 temporal result

The sequence experiment resolves the threshold-transfer question more sharply.
Conformal risk control can keep an "any accepted frame is wrong" mission loss
low on matched drift, but here it did so by accepting fewer than 5% of frames.
That is a real safety–utility boundary, not a successful deployment controller.

The exchangeability boundary was also operationally visible. On new drift
compositions, temporal CRC made more sequence false releases than confidence
CRC despite similar coverage, and quality-only CRC collapsed to zero coverage.
Thus observable sensor-quality features do not create a free distribution-shift
guarantee. The promising positive result is narrower: a causal temporal residual
substantially helped a moving target under compound aging and oscillatory gain.

The next credible step is online/weighted conformal recalibration with explicit
drift detection and measured temporal data. Retuning the current fixed blend on
held-out families would only hide the failure boundary.
