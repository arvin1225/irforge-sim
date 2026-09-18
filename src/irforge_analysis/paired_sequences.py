"""Paired, family-stratified sequence bootstrap for selective decisions."""

from collections import defaultdict
import numpy as np


def _boolean(value):
    if value in (True, "True", "true", "1", 1):
        return True
    if value in (False, "False", "false", "0", 0):
        return False
    raise ValueError(f"invalid boolean: {value!r}")


def compare_sequences(rows, *, candidate="crc_temporal", baseline="crc_confidence", frames_per_sequence=12, resamples=10000, seed=20260917):
    """Resample complete paired sequences within each family, never frames.

    Report frame coverage, correct accepted frames / all frames, and sequence
    false release. Conditional error is undefined when no frames are accepted.
    These are exploratory intervals, without a multiple-comparison correction.
    """
    if candidate == baseline or frames_per_sequence < 1 or resamples < 100:
        raise ValueError("distinct methods, positive frame count and >=100 resamples are required")
    groups = defaultdict(dict)
    for row in rows:
        if row["method"] not in (candidate, baseline):
            continue
        key = (str(row["regime"]), str(row["family"]), int(row["sequence_seed"]))
        method, frame = row["method"], int(row["frame_index"])
        frames = groups[key].setdefault(method, {})
        if frame in frames:
            raise ValueError(f"duplicate frame: {key}, {method}, {frame}")
        frames[frame] = (_boolean(row["accepted"]), _boolean(row["error"]), _boolean(row["has_target"]))
    if not groups:
        raise ValueError("no paired sequences")
    vectors = defaultdict(lambda: defaultdict(list))
    for key, pair in sorted(groups.items()):
        if set(pair) != {candidate, baseline}:
            raise ValueError(f"unpaired sequence: {key}")
        for method in (candidate, baseline):
            if set(pair[method]) != set(range(frames_per_sequence)):
                raise ValueError(f"incomplete frame sequence: {key}, {method}")
        for index in range(frames_per_sequence):
            if pair[candidate][index][1:] != pair[baseline][index][1:]:
                raise ValueError("selector comparison requires the same detector errors and target labels")
        methods = []
        for method in (candidate, baseline):
            values = np.asarray([pair[method][i] for i in range(frames_per_sequence)], dtype=bool)
            accepted, error = values[:, 0], values[:, 1]
            methods.append([float(np.any(accepted & error)), float(np.mean(accepted)), float(np.mean(accepted & ~error)), float(np.sum(accepted & error)), float(np.sum(accepted))])
        vectors[key[0]][key[1]].append(methods)
    rng = np.random.default_rng(seed)
    metrics = ("sequence_false_release", "frame_coverage", "correct_release_per_frame")
    result = {"candidate": candidate, "baseline": baseline, "resampling_unit": "paired sequence, stratified by family", "frames_per_sequence": frames_per_sequence, "resamples": resamples, "bootstrap_seed": seed, "analysis": "exploratory; pointwise percentile 95% intervals", "regimes": {}}
    for regime, families in sorted(vectors.items()):
        arrays = {name: np.asarray(values, dtype=float) for name, values in sorted(families.items())}
        all_values = np.concatenate(list(arrays.values()))
        n = len(all_values)
        draws = np.zeros((resamples, 3), dtype=np.int64)
        for values in arrays.values():
            indices = rng.integers(0, len(values), size=(resamples, len(values)))
            # All three outcomes are integer counts divided by sequence length.
            # Sum counts first: cancelling strata must give exact zero, not a
            # tiny negative interval endpoint that appears to exclude zero.
            difference = np.rint((values[:, 0, :3] - values[:, 1, :3]) * frames_per_sequence).astype(np.int64)
            draws += difference[indices].sum(axis=1)
        draws = draws / (n * frames_per_sequence)
        report = {"sequences": n, "families": {}, "methods": {}, "paired_difference": {}}
        for j, method in enumerate((candidate, baseline)):
            accepted = int(all_values[:, j, 4].sum())
            wrong = int(all_values[:, j, 3].sum())
            report["methods"][method] = {**{m: float(all_values[:, j, i].mean()) for i, m in enumerate(metrics)}, "accepted_frames": accepted, "wrong_releases": wrong, "conditional_error": wrong / accepted if accepted else None}
        for i, metric in enumerate(metrics):
            low, high = np.quantile(draws[:, i], [0.025, 0.975])
            report["paired_difference"][metric] = {"estimate": float((all_values[:, 0, i] - all_values[:, 1, i]).mean()), "ci_low": float(low), "ci_high": float(high)}
        for family, values in arrays.items():
            report["families"][family] = {"sequences": len(values), **{m: float((values[:, 0, i] - values[:, 1, i]).mean()) for i, m in enumerate(metrics)}}
        result["regimes"][regime] = report
    return result
