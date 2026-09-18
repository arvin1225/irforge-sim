# GitHub systems consulted for IRForge V2

Accessed 2026-08-13. No external implementation is copied into IRForge-Sim.

## MAPIE

- Repository: <https://github.com/scikit-learn-contrib/MAPIE>
- Relevance: distribution-free uncertainty and risk-control interfaces for
  scikit-learn-style workflows.
- Design response: expose calibration, risk scores, selected thresholds and
  finite-sample correction as first-class artifact fields. The local
  sequence-loss controller remains dependency-light and auditable.

## BasicIRSTD

- Repository: <https://github.com/XinyiYing/BasicIRSTD>
- Relevance: common single-frame infrared small-target baselines and dataset
  evaluation conventions.
- Design response: preserve classical local-contrast and matched-filter
  controls, target-level localization and false alarms/image. IRForge is a
  failure-boundary simulator, not a leaderboard reproduction.

## MSHNet and PAL

- MSHNet: <https://github.com/Lliu666/MSHNet>
- PAL: <https://github.com/YuChuang1205/PAL>
- Relevance: modern learned IRSTD systems illustrate the gap between this
  lightweight fixed detector and competitive segmentation models.
- Design response: state that detector quality is not the proposed
  contribution. H6 studies temporal sensor drift and post-detector release
  control; stronger frozen detectors can later plug into the same protocol.

