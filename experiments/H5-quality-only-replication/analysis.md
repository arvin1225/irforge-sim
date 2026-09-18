# H5 replication analysis

## Outcome

H5 **failed**. On untouched seeds `2000–2079`, quality-only AURC was `0.4060` and confidence-only AURC was `0.4482`, a relative reduction of `9.41%`. The frozen gate required at least `10%`, and the paired bootstrap interval for the difference was `[-0.0998, 0.0185]`, which includes zero.

The fixed-80%-coverage secondary diagnostic was positive: quality-only conditional error was `0.4438` versus `0.4938`, difference `-0.0500`, 95% interval `[-0.0813, -0.0156]`.

## Interpretation boundary

The replication does not support a global claim that image-quality features reliably outrank calibrated confidence across the entire risk–coverage curve. It supports a narrower hypothesis: around one registered operating region, sensor-quality signals can remove errors that confidence misses. That narrower mechanism requires a new experiment and cannot be confirmed by this reused matrix.

## Integrity

- 5 families × 80 seeds × 11 modes = 4,400 rows;
- training/calibration seeds are below 1,000 and disjoint from replication seeds;
- CSV and summary hashes pass;
- selected images and output rows replay exactly;
- the zero-contrast negative control passes;
- no post-result threshold or gate-weight change was made.
