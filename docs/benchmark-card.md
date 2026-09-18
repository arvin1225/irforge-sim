# Benchmark card

## Intended use

Controlled study of detector failure, confidence calibration and selective error ranking under synthetic composed infrared sensor shift.

## Out-of-scope use

- operational surveillance or targeting;
- claims about a named physical sensor;
- safety certification;
- state-of-the-art detector comparison;
- demographic or human-subject inference.

## Data generation

All frames are procedural and deterministic from `(family, seed)`. No personal, proprietary or measured imagery is included. A target is a small band-radiance perturbation placed on procedural cloud, horizon, sea or urban-like backgrounds.

## Splits

| Split | Seed range | Families |
|---|---|---|
| training/calibration | 0–239 | nominal + single-axis shifts |
| confirmation | 1000–1079 per family | five composed shifts |
| H5 replication | 2000–2079 per family | same frozen five composed shifts |

## Known limitations

- H1–H5 use independent frames; H6 adds controlled 12-frame drift sequences but not multi-object tracking;
- Gaussian PSF and simplified atmospheric transfer;
- no nonuniformity-correction pipeline fitted to a device;
- procedural backgrounds do not reproduce a measured scene distribution;
- small source-domain training set and deliberately shallow learned baseline;
- a failed global selective-ranking claim.

## Integrity

Every committed matrix has a manifest, data/summary hashes, code hash and validation report. The replication decision has its own manifest binding the parent benchmark manifest, frozen decision rule and decision JSON.
