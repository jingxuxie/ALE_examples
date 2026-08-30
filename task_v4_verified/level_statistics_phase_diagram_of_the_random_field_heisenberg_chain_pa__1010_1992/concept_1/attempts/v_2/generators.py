import numpy as np


FAMILIES = ("iid_uniform", "ordered_blocks", "alternating_correlated", "shuffled_pairs")
LENGTHS = (10, 12)


def sample_fields(rng, length, family):
    if length not in LENGTHS or family not in FAMILIES:
        raise ValueError("Unsupported length or family")
    component = rng.choice(3, p=[0.2, 0.5, 0.3])
    intervals = ((0.4, 1.8), (1.8, 4.5), (4.5, 8.0))
    amplitude = rng.uniform(*intervals[component])
    sites = np.arange(length)
    if family == "iid_uniform":
        fields = rng.uniform(-amplitude, amplitude, length)
    elif family == "ordered_blocks":
        block_count = int(rng.integers(2, 4))
        boundaries = np.array_split(sites, block_count)
        centers = rng.uniform(-amplitude, amplitude, block_count)
        width = amplitude * rng.uniform(0.025, 0.22)
        fields = np.empty(length)
        for block, center in zip(boundaries, centers):
            slope = rng.uniform(-width, width)
            fields[block] = center + slope * np.linspace(-1, 1, len(block))
        fields += rng.uniform(-width, width, length)
    elif family == "alternating_correlated":
        stagger = amplitude * rng.uniform(0.45, 1.0)
        smooth = amplitude * rng.uniform(0.1, 0.7)
        phase = rng.uniform(0, 2 * np.pi)
        width = amplitude * rng.uniform(0.05, 0.25)
        fields = stagger * (-1.0) ** sites
        fields += smooth * np.cos(2 * np.pi * sites / length + phase)
        fields += rng.uniform(-width, width, length)
    else:
        centers = rng.uniform(-amplitude, amplitude, length // 2)
        mismatch = amplitude * rng.uniform(0.005, 0.18, length // 2)
        fields = np.column_stack((centers - mismatch / 2, centers + mismatch / 2)).ravel()
        rng.shuffle(fields)
    fields = np.roll(fields, int(rng.integers(length)))
    if rng.random() < 0.5:
        fields = fields[::-1]
    if rng.random() < 0.5:
        fields = -fields
    if np.min(np.diff(np.sort(fields))) <= 1e-8:
        return sample_fields(rng, length, family)
    return fields.tolist()


def sample_cases(per_cell, rng):
    cases = []
    for family in FAMILIES:
        for length in LENGTHS:
            for sample_index in range(per_cell):
                cases.append({"L": length, "family": family,
                              "fields": sample_fields(rng, length, family)})
    rng.shuffle(cases)
    return [dict(case, id=f"case_{index:05d}") for index, case in enumerate(cases)]
