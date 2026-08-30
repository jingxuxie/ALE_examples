import numpy as np


TOPOLOGIES = ("ladder", "patch", "triangular")
BOUNDS = {"boundary": (0.003, 0.05), "bulk": (0.002, 0.06),
          "hook": (0.0015, 0.028), "rare": (0.00005, 0.015)}


def make_case(detector_count, topology, seed, shots=40000):
    rng = np.random.default_rng(seed)
    width = detector_count // 2 if topology == "ladder" else (4 if topology == "patch" else 3)
    coordinates = [(index // width, index % width) for index in range(detector_count)]
    lookup = {coordinate: index for index, coordinate in enumerate(coordinates)}
    permutation = rng.permutation(detector_count)
    edges = []
    for index, (row, column) in enumerate(coordinates):
        directions = [(0, 1), (1, 0)]
        if topology == "triangular":
            directions.append((1, 1))
        for row_offset, column_offset in directions:
            neighbor = lookup.get((row + row_offset, column + column_offset))
            if neighbor is not None:
                edges.append((index, neighbor))
    plaquettes = []
    for row, column in coordinates:
        corners = [(row, column), (row, column + 1), (row + 1, column), (row + 1, column + 1)]
        if all(corner in lookup for corner in corners):
            plaquettes.append([lookup[corner] for corner in corners])
    neighbors = [set() for index in range(detector_count)]
    for first, second in edges:
        neighbors[first].add(second)
        neighbors[second].add(first)

    def mask(nodes):
        return sum(1 << int(permutation[node]) for node in set(nodes))

    channels = []
    for index in range(detector_count):
        channels.append({"family": "boundary", "masks": [mask([index]), mask([index])]})
    for first, second in edges:
        choices = sorted(neighbors[first] - {second})
        alternate = [first, int(rng.choice(choices))] if choices else [first, second]
        channels.append({"family": "bulk", "masks": [mask([first, second]), mask(alternate)]})
    hook_start = len(channels)
    for index, corners in enumerate(plaquettes):
        primary = corners if index % 2 == 0 else corners[:3]
        alternate = [corners[offset] for offset in (1, 2, 3)]
        channels.append({"family": "hook", "masks": [mask(primary), mask(alternate)]})
    rare_count = max(4, detector_count // 4)
    alias_indices = np.linspace(0, len(plaquettes) - 1, rare_count, dtype=int)
    for index in alias_indices:
        corners = plaquettes[index]
        primary = channels[hook_start + index]["masks"][0]
        alternate = mask([corners[offset] for offset in (0, 1, 3)])
        channels.append({"family": "rare", "masks": [primary, alternate]})
    channel_count = len(channels)
    sectors = rng.permutation(np.arange(channel_count) % 4)
    mode_scale = rng.uniform(2.0, 4.0, channel_count)
    for index, hook_index in enumerate(alias_indices):
        mode_scale[channel_count - rare_count + index] = mode_scale[hook_start + hook_index]
    for index, channel in enumerate(channels):
        channel.update({"id": "channel_%03d" % index, "sector": int(sectors[index]),
                        "rate_bounds": list(BOUNDS[channel["family"]])})
    actions = []
    for action_index in range(13):
        exposure = np.ones(channel_count)
        alternate = np.zeros(channel_count)
        hot_probability = 0.0
        if action_index:
            hot_probability = (0.08, 0.22, 0.42)[(action_index + TOPOLOGIES.index(topology)) % 3]
            exposure = rng.uniform(0.65, 1.25, channel_count)
            alternate = rng.uniform(0.1, 0.38, channel_count)
            if action_index == 1:
                exposure *= 7.0
            elif action_index <= 9:
                selected = sectors == (action_index - 2) // 2
                exposure *= np.where(selected, 5.0 if action_index % 2 == 0 else 18.0, 0.35)
                for index, channel in enumerate(channels):
                    if channel["family"] == "rare" and selected[index]:
                        exposure[index] *= 2.5
            elif action_index == 10:
                exposure *= [12.0 if channel["family"] in ("hook", "rare") else 0.25 for channel in channels]
                alternate *= 0.12
            elif action_index == 11:
                exposure *= [20.0 if channel["family"] == "rare" else 0.45 for channel in channels]
                alternate = rng.uniform(0.55, 0.8, channel_count)
            else:
                exposure *= 0.3
                hot_probability = 0.65
        actions.append({"id": action_index, "name": "reference" if action_index == 0 else "configuration_%02d" % action_index,
                        "mode_weights": [1.0 - hot_probability, hot_probability],
                        "exposures": np.stack([exposure, exposure * mode_scale]).tolist(),
                        "alternate_probability": alternate.tolist()})
    for channel_index in range(channel_count - rare_count, channel_count):
        for gain_index, gain in enumerate((20.0, 120.0, 720.0, 4320.0)):
            exposure = np.full(channel_count, 0.2)
            exposure[channel_index] = gain
            alternate = np.full(channel_count, 0.15)
            alternate[channel_index] = 0.3 if gain_index % 2 == 0 else 0.7
            actions.append({"id": len(actions), "name": "rare_%d_gain_%d" % (channel_index, int(gain)),
                            "mode_weights": [0.8, 0.2],
                            "exposures": np.stack([exposure, exposure * mode_scale]).tolist(),
                            "alternate_probability": alternate.tolist()})
    bounds = np.array([channel["rate_bounds"] for channel in channels])
    rates = np.exp(rng.uniform(np.log(bounds[:, 0]), np.log(bounds[:, 1])))
    spec = {"protocol": "detector-calibration-stress-v0", "observation_encoding": "sparse_histogram_v1",
            "regime": ("chain_hooks", "patch_crosstalk", "burst_aliases")[TOPOLOGIES.index(topology)],
            "topology": topology, "detector_count": detector_count,
            "detector_edges": [[int(permutation[first]), int(permutation[second])] for first, second in edges],
            "channels": channels, "actions": actions, "shot_budget": shots,
            "max_queries": 64, "max_shots_per_query": 4000, "cpu_seconds": 60, "wall_seconds": 900}
    return {"id": "%s_D%d" % (topology, detector_count), "spec": spec,
            "rates": rates, "sample_seed": int(rng.integers(0, 2**63))}


def cases(seed=8317021, sizes=(14, 16, 18, 20), topologies=TOPOLOGIES, shots=40000):
    for detector_count in sizes:
        for topology in topologies:
            case_seed = int(np.random.SeedSequence([seed, detector_count, TOPOLOGIES.index(topology)]).generate_state(1)[0])
            yield make_case(detector_count, topology, case_seed, shots)


def sample(case, action_id, shots, rng, poisson=False):
    spec = case["spec"]
    action = spec["actions"][action_id]
    modes = rng.choice(2, shots, p=action["mode_weights"])
    exposures = np.array(action["exposures"])
    syndromes = np.zeros(shots, dtype=np.int64)
    for index, channel in enumerate(spec["channels"]):
        intensity = exposures[modes, index] * case["rates"][index]
        fired = rng.poisson(intensity) % 2 == 1 if poisson else rng.random(shots) < -0.5 * np.expm1(-2.0 * intensity)
        alternate = rng.random(shots) < action["alternate_probability"][index]
        footprint = np.where(alternate, channel["masks"][1], channel["masks"][0])
        syndromes ^= np.where(fired, footprint, 0)
    return np.unique(syndromes, return_counts=True)
