# Contributing

Contributions are welcome when they preserve the benchmark's experiment and evidence boundaries.

## Before opening a change

1. Describe the sensor mechanism, failure mode, or evaluation contract that motivates the change.
2. State whether the change affects image formation, detection, calibration, selective release, or a frozen protocol.
3. Never overwrite a committed confirmatory artifact to match new code. Create a new protocol and artifact identity for result-affecting changes.

## Development checks

```bash
python -m pip install -e ".[dev]"
python -m unittest discover -s tests -v
python scripts/validate_artifact.py --artifact artifacts/confirmatory
python scripts/validate_artifact.py --artifact artifacts/replication-h5
python scripts/validate_h6_artifact.py artifacts/confirmatory-h6
python -m build
cd web && pnpm install --frozen-lockfile && pnpm run build
```

Full validators intentionally refit the public baselines. Images and labels must replay bitwise; fitted risk scores must remain within the documented numerical tolerance across supported scientific Python builds.

## Pull requests

- add a regression test for every changed scientific contract;
- keep development and confirmatory seeds disjoint;
- preserve negative results and failed hypotheses;
- document any schema or protocol migration;
- keep public documentation and interface text in English;
- avoid claims that exceed the synthetic sensor family actually evaluated.
