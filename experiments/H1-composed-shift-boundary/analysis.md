# Exploratory analysis before confirmation

All results below use exploratory seeds only. They are mechanism checks, not confirmatory evidence.

| Iteration | Change | Calibration error | Pooled composed AURC (confidence / shift) | Interpretation |
|---|---|---:|---:|---|
| E1 | linear pixel model, initial response scale | 0.802 | 0.786 / 0.876 | invalid baseline; gate cannot rescue mostly wrong detector |
| E2 | hard-negative mining | 0.781 | 0.603 / 0.611 | fewer false alarms, excessive target suppression |
| E3 | measurable nominal radiance-response scale | 0.656 | 0.850 / 0.661 | gate signal appears, detector still artifact-sensitive |
| E4 | partial-defect model + obvious pixel mask | 0.594 | 0.849 / 0.661 | coverage and ranking improve; small sample unstable |
| E5 | shallow nonlinear learned detector | 0.385 | 0.665 / 0.596 | source-domain baseline becomes usable |
| Final | 200 composed samples, blended confidence/quality risk | 0.385 | **0.478 / 0.439** | ranking improves 8.3%; threshold coverage fails to transfer |

The final exploratory comparison at the validation-fitted threshold was:

- confidence-only: coverage `1.000`, conditional error `0.505`;
- shift-aware: coverage `0.780`, conditional error `0.474`;
- coverage gap `0.220`, violating the registered H3 gate;
- shift-aware AURC improved by 8.3% relative, motivating a separate fixed-coverage ranking hypothesis.

No confirmatory seed or label was inspected during these iterations.

## Frozen confirmation outcome

The first confirmatory run used seeds `1000–1079` for every composed family and produced 4,400 rows. Integrity validation passed.

| Registered item | Outcome | Decision |
|---|---|---|
| H1: compositions increase high-confidence failure | pooled raw silent failure `0.1375`, below worst single shift `0.3125` | fail |
| H2: calibration helps ECE, not selective ordering | ECE `0.1405 → 0.0772`; AURC unchanged at `0.5047` | pass |
| H3: fitted threshold transfers | confidence coverage `1.000`; full shift-aware coverage `0.7925` | fail |
| H4: quality-aware score improves global and 80% risk | AURC `0.5047 → 0.4680` (7.28%); paired 80% interval crosses zero | fail |

The unanticipated quality-only AURC of `0.4316` was not promoted into H4. It motivated the separately committed H5 replication protocol.
