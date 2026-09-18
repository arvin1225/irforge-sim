# Temporal selector comparison

Exploratory paired analysis of fixed H6 outputs. Each resample preserves the complete 12-frame sequence, both selectors, and the family stratum. Intervals are pointwise; they do not imply robustness to a new drift distribution.

| Regime | Sequences | Metric | Temporal − confidence | 95% interval |
|---|---:|---|---:|---:|
| heldout | 240 | sequence_false_release | 2.50 pp | [-2.92, 7.92] |
| heldout | 240 | frame_coverage | 0.83 pp | [-0.35, 2.01] |
| heldout | 240 | correct_release_per_frame | 0.83 pp | [-0.03, 1.70] |
| matched | 120 | sequence_false_release | -5.83 pp | [-11.67, 0.00] |
| matched | 120 | frame_coverage | 0.14 pp | [-1.81, 2.22] |
| matched | 120 | correct_release_per_frame | 1.11 pp | [-0.69, 3.06] |

Lower sequence false release is better. Higher coverage and correct releases per input frame are better. Report all three: rejecting every frame has zero observed false release and zero utility.

Source SHA-256: `6639875c9190c4d653a743f0b2f72f94e4836051f577cacb2f223dafd85a8e98`
