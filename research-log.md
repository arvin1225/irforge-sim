# Research log

## 2026-08-13 — H6 temporal conformal-risk protocol lock

- Converted the open question about threshold transfer into a sequence-level
  bounded-loss problem: any accepted wrong frame makes the 12-frame mission
  window a loss.
- Registered three drift-calibration families, a disjoint matched-drift test and
  three unseen composition families before implementation.
- Frozen four detector baselines, three conformal risk scores, a naive fixed-80
  threshold, alpha `0.10`, temporal-score weights and five pass/fail gates.
- Limited exchangeability claims to independent matched-drift sequences; held-out
  drift remains an explicit stress test.

## 2026-08-13 — frozen H6 confirmation

- Ran 120 matched and 240 held-out sequences, 12 frames and eight methods,
  producing 34,560 rows without changing registered weights or thresholds.
- Matched temporal CRC controlled sequence false release at `2.5%` but accepted
  only `4.79%` of frames, so H6-A failed its utility condition.
- On unseen drift compositions, temporal CRC was worse than confidence CRC
  (`15.42%` versus `12.92%` sequence false release), falsifying H6-B.
- At matched coverage the temporal ranking point estimate improved by 9.59
  points, but its paired interval crossed zero; H6-C failed.
- The causal temporal residual baseline passed H6-D in two of three held-out
  families. H6-E integrity passed every registered audit.
- Vectorizing the paired bootstrap reduced independent validation from minutes
  to about five seconds without changing any saved statistic or decision.

## 2026-08-03 — bootstrap and protocol lock

- Chose failure-boundary discovery over another architecture leaderboard.
- Restricted claims to synthetic single-frame LWIR-like scenes.
- Defined disjoint single-shift training/calibration compositions and composed-shift confirmatory families.
- Registered H1–H3, primary selective-risk metric, seed ranges, baselines, ablations and disproof conditions before implementation results.

## 2026-08-03 — inner loop E1–E5 (exploratory seeds only)

- E1 exposed a broken source-domain baseline: the learned detector had 80.2% calibration error, so no selective claim was interpretable.
- E2 added deterministic hard-negative mining; it reduced false alarms but over-suppressed true targets.
- E3 corrected the simulator response scale so nominal targets occupy a measurable regime rather than being lost before any composed shift.
- E4 added a fixed obvious bad-pixel mask while retaining partial defects; the shift gate began lowering error, but small-sample coverage was unstable.
- E5 replaced the linear pixel classifier with a shallow histogram gradient booster. On calibration it reached 61.5% decision accuracy and an AURC of 0.290; this remains a deliberately lightweight baseline, not a state-of-the-art network.
- The final exploratory matrix used all held-out-composition seeds `200–239` without touching confirmatory seeds. Quality-aware ranking reduced AURC from `0.4784` to `0.4387` (8.3% relative), but the fixed-threshold coverage gap was 22 percentage points and H3 failed.
- Outer-loop decision: preserve the failed H3 and preregister a separate matched-coverage ranking hypothesis before confirmation.

## 2026-08-03 — first confirmatory matrix (seeds 1000–1079)

- Evaluated 5 held-out composed-shift families × 80 seeds × 11 modes = 4,400 rows.
- Independent artifact validation passed every hash, split, range, replay, negative-control and finite-metric check.
- H1 failed: pooled raw silent failure was `0.1375`, below the worst single-shift family (`clutter_only`, `0.3125`).
- H2 passed narrowly and specifically: temperature scaling reduced ECE from `0.1405` to `0.0772`, while AURC remained exactly `0.5047`; it improved calibration, not ordering.
- H3 failed: the calibration-fitted acceptance threshold did not transfer to the composed families.
- H4 failed: the full shift-aware score reduced pooled AURC by `7.28%`, but its paired fixed-80%-coverage error interval crossed zero.
- A registered ablation unexpectedly ranked quality-only risk better than calibrated confidence (`0.4316` versus `0.5047` AURC). This observation was treated as hypothesis-generating, not confirmatory support.

## 2026-08-03 — frozen H5 replication (seeds 2000–2079)

- Locked H5 and committed the protocol before generating any replication row.
- Repeated the same 4,400-row matrix without changing the generator, detector, calibration, thresholds, gate weights or families.
- H5 failed its primary gate: quality-only AURC was `0.4060` versus `0.4482` for confidence, a `9.41%` reduction rather than the required `10%`; the paired AURC interval was `[-0.0998, 0.0185]` and crossed zero.
- A preregistered secondary diagnostic did reproduce locally: at exactly 80% coverage, quality-only error was `0.4438` versus `0.4938`, difference `-0.0500`, 95% interval `[-0.0813, -0.0156]`.
- Conclusion: reject a global ranking claim; preserve a narrower operating-region effect as a future hypothesis. No threshold was changed after observing results.
- Corrected the H5 artifact's protocol-link metadata after the run; benchmark and summary hashes, rows, metrics and decision rule were unchanged, and the enclosing manifest hash was recomputed.
