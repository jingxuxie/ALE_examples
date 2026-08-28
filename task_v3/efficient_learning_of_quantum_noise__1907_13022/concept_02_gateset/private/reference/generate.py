import argparse
import hashlib
import itertools
import json
import time
from pathlib import Path

import numpy as np
from scipy.linalg import qr

from metrics import WEIGHTS, losses
from solver import Model, membership, row_basis, solve
from weak_baseline import solve as weak_solve


ROOT = Path(__file__).resolve().parents[2]
FAMILIES = ('local_edges', 'parallel_crosstalk', 'restricted_components')


def connected_components(qubits, edges):
    neighbors = [set() for _ in range(qubits)]
    for first, second in edges:
        neighbors[first].add(second)
        neighbors[second].add(first)
    unseen = set(range(qubits))
    sizes = []
    while unseen:
        reached, pending = set(), [next(iter(unseen))]
        while pending:
            site = pending.pop()
            if site not in reached:
                reached.add(site)
                pending.extend(neighbors[site] - reached)
        unseen.difference_update(reached)
        sizes.append(len(reached))
    return sorted(sizes, reverse=True)


def topology(data):
    model = Model(data)
    gate_edges = [(int(first), int(second)) for gate in np.flatnonzero(model.noise >= 0)
                  for opcode, first, second in model.operations[gate] if opcode >= 3]
    noise_edges = [tuple(np.flatnonzero(mask)) for channel, mask in
                   zip(data['factor_channel'], data['factor_mask'])
                   if channel >= 0 and np.count_nonzero(mask) == 2]
    maximum_weight = 0
    for begin, end, observable in zip(data['holdout_ptr'][:-1], data['holdout_ptr'][1:],
                                      data['holdout_observable']):
        _, _, terms = model.trace(data['holdout_gates'][begin:end], observable, terms=True)
        maximum_weight = max(maximum_weight, max(np.count_nonzero(pauli) for _, pauli, _ in terms))
    scope_width = 0
    for gate in np.flatnonzero(model.noise >= 0):
        dependencies = model.dependencies(gate)
        for factor in model.factors[-2] + model.factors[int(model.noise[gate])]:
            scope_width = max(scope_width, len(set().union(*(dependencies[site] for site in factor))))
    return {'ideal_graph_component_sizes': connected_components(model.qubits, gate_edges),
            'noise_graph_component_sizes': connected_components(model.qubits, noise_edges),
            'rooted_experiments': len(model.rooted_experiments()),
            'maximum_dependency_scope': scope_width,
            'maximum_heldout_propagated_weight': int(maximum_weight)}


def gate_set(qubits, family, variant, random):
    primitive_lists, noise_labels, factor_channels, factor_masks = [], [], [], []
    permutation = random.permutation(qubits)

    def factor(channel, sites):
        mask = np.zeros(qubits, dtype=np.int8)
        mask[permutation[list(sites)]] = 1
        factor_channels.append(channel)
        factor_masks.append(mask)

    def gate(operations, channel):
        mapped = [(opcode, int(permutation[first]),
                   -1 if second < 0 else int(permutation[second]))
                  for opcode, first, second in operations]
        primitive_lists.append(mapped)
        noise_labels.append(channel)

    if family == 'local_edges':
        edges = [(site, site + 1) for site in range(qubits - 1)]
        if variant >= 3:
            edges.append((qubits - 1, 0))
        spam_scopes = [(site,) for site in range(qubits)]
        for channel, edge in enumerate(edges):
            opcode = 3 if (channel + variant) % 2 else 4
            gate([(opcode, *edge)], channel)
            for scope in [(edge[0],), (edge[1],), edge]:
                factor(channel, scope)
        dark = set()
    else:
        if family == 'parallel_crosstalk' or qubits >= 16:
            edges = [(site, site + 1) for site in range(qubits - 1)]
            if variant % 2 or variant >= 3:
                edges.append((qubits - 1, 0))
            layers = [edges[::2], edges[1::2]]
            dark = set() if family == 'parallel_crosstalk' else set(permutation.tolist())
        else:
            edges = [(site, site + 1) for site in range(0, qubits, 2)]
            layers = [edges, [(second, first) for first, second in edges]]
            dark = set(permutation[-(4 if variant >= 3 else 2):].tolist())
        spam_scopes = [(site,) for site in range(qubits)]
        if family == 'parallel_crosstalk' or variant >= 3:
            spam_scopes += edges
        for channel, layer in enumerate(layers):
            operations = [(3 if (channel + position + variant) % 2 else 4, first, second)
                          for position, (first, second) in enumerate(layer)]
            gate(operations, channel)
            for scope in [(site,) for site in range(qubits)] + edges:
                factor(channel, scope)
    for channel in (-2, -1):
        for scope in spam_scopes:
            factor(channel, scope)
    for site in range(qubits):
        gate([(1, site, -1)], -1)
        gate([(2, site, -1)], -1)
    order = random.permutation(len(primitive_lists))
    pointers, operations, shuffled_noise = [0], [], []
    for position in order:
        operations.extend(primitive_lists[position])
        pointers.append(len(operations))
        shuffled_noise.append(noise_labels[position])
    factor_order = random.permutation(len(factor_channels))
    data = {
        'schema_version': np.array(1, dtype=np.int32),
        'n_qubits': np.array(qubits, dtype=np.int32),
        'gate_ptr': np.array(pointers, dtype=np.int32),
        'gate_ops': np.array(operations, dtype=np.int16),
        'gate_noise': np.array(shuffled_noise, dtype=np.int16),
        'factor_channel': np.array(factor_channels, dtype=np.int16)[factor_order],
        'factor_mask': np.array(factor_masks, dtype=np.int8)[factor_order],
    }
    return data, dark


def pack_experiments(data, prefix, experiments):
    pointers, gates, observables = [0], [], []
    for sequence, observable in experiments:
        gates.extend(sequence)
        pointers.append(len(gates))
        observables.append(observable)
    data[prefix + '_ptr'] = np.array(pointers, dtype=np.int32)
    data[prefix + '_gates'] = np.array(gates, dtype=np.int16)
    data[prefix + '_observable'] = np.array(observables, dtype=np.int8)


def pack_queries(data, queries):
    pointers, channels, paulis, coefficients = [0], [], [], []
    for terms in queries:
        for channel, pauli, coefficient in terms:
            channels.append(channel)
            paulis.append(pauli)
            coefficients.append(coefficient)
        pointers.append(len(channels))
    data['query_ptr'] = np.array(pointers, dtype=np.int32)
    data['query_channel'] = np.array(channels, dtype=np.int16)
    data['query_pauli'] = np.array(paulis, dtype=np.int8)
    data['query_coeff'] = np.array(coefficients, dtype=np.float64)


def physical_rates(model, random, variant):
    rates = np.empty(model.parameter_count)
    for position, channel in enumerate(model.channels):
        weight = int(np.sum(model.supports[position]))
        if channel < 0:
            rates[position] = random.uniform(0.018, 0.070) / weight ** 2
        else:
            bias = 4.0 if np.all(model.labels[position][model.labels[position] != 0] == 3) else 1.0
            rates[position] = random.uniform(0.00035, 0.0035) * bias / weight ** 1.7
    rates *= 0.75 + 0.25 * (variant % 3)
    return rates


def build_case(seed, qubits, family, variant, small=False):
    random = np.random.default_rng(seed)
    data, dark = gate_set(qubits, family, variant, random)
    model = Model(data)
    rates = physical_rates(model, random, variant)
    noisy = np.flatnonzero(model.noise >= 0).tolist()
    clean = [position for position in np.flatnonzero(model.noise < 0)
             if all(opcode != 1 or first not in dark
                    for opcode, first, second in model.operations[position])]

    def observable(restricted=True):
        weight = int(random.integers(1, min(qubits, 5 if variant >= 3 else 3) + 1))
        sites = random.choice(qubits, weight, replace=False)
        pauli = np.zeros(qubits, dtype=np.int8)
        pauli[sites] = random.integers(1, 4, weight)
        if restricted:
            for site in dark:
                if pauli[site]:
                    pauli[site] = 3
        return pauli

    def sequence(length, restricted=True):
        clean_choices = clean if restricted else np.flatnonzero(model.noise < 0).tolist()
        return [int(random.choice(noisy if random.random() < 0.7 else clean_choices))
                for _ in range(length)]

    rooted = model.rooted_experiments()
    structural_rows = np.array([model.trace(gates, pauli)[0] for gates, pauli in rooted])
    structural = row_basis(structural_rows)
    allowed = [position for position, (_, pauli) in enumerate(rooted)
               if all(pauli[site] in (0, 3) for site in dark)]
    allowed_rows = structural_rows[allowed]
    observed = row_basis(allowed_rows)
    _, _, pivots = qr(allowed_rows.T, pivoting=True, mode='economic', check_finite=False)
    selected = list(pivots[:len(observed)])
    remaining = np.setdiff1d(np.arange(len(allowed)), selected)
    if len(remaining):
        selected += random.choice(remaining, min(len(remaining), len(observed) // 2),
                                  replace=False).tolist()
    training = [rooted[allowed[position]] for position in selected]
    amplified_count = 8 if small else max(35, model.parameter_count // 2)
    for _ in range(amplified_count):
        pauli = observable()
        motif = [int(random.choice(noisy))]
        if random.random() < 0.55:
            motif += [int(random.choice(clean)), int(random.choice(noisy))]
        current = pauli.copy()
        period = 0
        for repetition in range(1, 9):
            for gate in reversed(motif):
                current, _ = model.backward(gate, current)
            if np.array_equal(current, pauli):
                period = repetition
                break
        if not period:
            motif, period = [int(random.choice(noisy))], 2
        for depth in (1, 4, 16 if variant < 3 else 24):
            training.append((motif * (period * depth), pauli.copy()))
    for _ in range(8 if small else model.parameter_count // 2):
        training.append((sequence(int(random.integers(2, 12))), observable()))
    random.shuffle(training)
    pack_experiments(data, 'train', training)
    calibration, signs = model.experiments('train')
    observed = row_basis(calibration)
    true_means = signs * np.exp(-calibration @ rates)
    choices = np.array([384, 1024, 4096, 16384, 65536])
    if variant >= 3:
        choices = np.array([128, 384, 1536, 8192, 32768])
    shots = random.choice(choices, len(training), p=[0.12, 0.18, 0.25, 0.30, 0.15])
    data['train_shots'] = shots.astype(np.int64)
    data['train_plus'] = random.binomial(shots, (1 + true_means) / 2).astype(np.int64)

    heldout = []
    for _ in range(16 if small else 128):
        length = int(random.integers(3, 35 if variant < 3 else 65))
        heldout.append((sequence(length), observable()))
    pack_experiments(data, 'holdout', heldout)
    heldout_rows, heldout_signs = model.experiments('holdout')
    if not np.all(membership(heldout_rows, observed)):
        raise AssertionError('Unestimable held-out experiment')

    queries = []
    query_count = 20 if small else 112
    for position in range(query_count):
        restricted_query = family == 'restricted_components' and qubits >= 16 and position % 8 in (1, 2)
        pauli = observable(restricted=restricted_query)
        if position % 4 == 0:
            channel = int(random.choice([-2, -1] + list(range(len(noisy)))))
            terms = [(channel, pauli, 1.0)]
        elif position % 4 == 1:
            gate = int(random.choice(noisy))
            _, _, components = model.trace([gate, gate], pauli, terms=True)
            terms = [term for term in components if term[0] >= 0]
        elif position % 4 == 2:
            _, _, terms = model.trace(sequence(int(random.integers(0, 5)), restricted=False),
                                      pauli, terms=True)
        else:
            gate = int(random.choice(noisy))
            other = observable(restricted=False)
            channel = int(model.noise[gate])
            terms = [(channel, pauli, 1.0), (channel, other, -1.0)]
        queries.append(terms)
    random.shuffle(queries)
    pack_queries(data, queries)
    query_rows = model.queries()
    scale = np.array([sum(abs(coefficient) * max(1, np.count_nonzero(pauli))
                          for channel, pauli, coefficient in terms) for terms in queries])
    oracle = {
        'structural_identifiable': membership(query_rows, structural).astype(np.int8),
        'calibration_identifiable': membership(query_rows, observed).astype(np.int8),
        'query_log': query_rows @ rates,
        'query_scale': scale,
        'holdout_mean': heldout_signs * np.exp(-heldout_rows @ rates),
    }
    return data, oracle, {'parameters': model.parameter_count,
                          'structural_rank': len(structural), 'calibration_rank': len(observed),
                          'train_experiments': len(training), 'holdout_experiments': len(heldout),
                          'queries': len(queries), 'qubits': qubits,
                          'noisy_gates': len(noisy), 'dark_qubits': sorted(dark),
                          'negative_holdout': int(np.sum(heldout_signs < 0)),
                          'structural_identified_queries': int(oracle['structural_identifiable'].sum()),
                          'calibration_identified_queries': int(oracle['calibration_identifiable'].sum())}


def save_npz(path, arrays):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('wb') as stream:
        np.savez_compressed(stream, **arrays)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate_pool(root, pool, seed):
    destination = root / 'private' / ('reference/core' if pool == 'core' else 'challenge_pool')
    destination.mkdir(parents=True, exist_ok=True)
    manifest = {'schema_version': 1, 'scale_profile': 'coupled_20_24', 'seed': seed, 'pool': pool, 'cases': [],
                'metrics': list(WEIGHTS), 'source_revision': '9946e16305a3927ffff9706f3ffedd4c98b9b30f'}
    variants = range(3) if pool == 'core' else range(3, 5)
    for family_index, family in enumerate(FAMILIES):
        for variant in variants:
            case_seed = int(seed + 100003 * (family_index + 1) + variant * 7919)
            if pool == 'core':
                qubits = 20 if variant == 2 else (4 if family == 'local_edges' else 6) + 2 * variant
            else:
                qubits = 20 + 4 * (variant - 3)
            case_id = f'{family}_{variant + 1:02d}'
            started = time.monotonic()
            data, oracle, details = build_case(case_seed, qubits, family, variant)
            geometry = topology(data)
            if qubits >= 16 and (geometry['ideal_graph_component_sizes'] != [qubits] or
                                 geometry['noise_graph_component_sizes'] != [qubits]):
                raise AssertionError('Large-system case must be genuinely coupled')
            reference, fit_info = solve(data, diagnostics=True)
            baseline = weak_solve(data)
            baseline_loss, reference_loss = losses(baseline, oracle), losses(reference, oracle)
            for component in WEIGHTS:
                if baseline_loss[component] - reference_loss[component] <= 1e-12:
                    raise AssertionError(f'Reference does not beat baseline: {case_id} {component}')
            if not fit_info['success']:
                raise AssertionError(f'Likelihood optimization failed: {case_id} {fit_info}')
            if reference_loss['heldout_prediction'] > 0.0016:
                raise AssertionError(f'Poor absolute prediction accuracy: {case_id}')
            oracle['baseline_loss'] = np.array([baseline_loss[key] for key in WEIGHTS])
            oracle['reference_loss'] = np.array([reference_loss[key] for key in WEIGHTS])
            case_path = destination / case_id
            save_npz(case_path / 'input.npz', data)
            save_npz(case_path / 'oracle.npz', oracle)
            entry = dict(case_id=case_id, family=family, seed=case_seed,
                         input_sha256=sha256(case_path / 'input.npz'),
                         oracle_sha256=sha256(case_path / 'oracle.npz'),
                         baseline_loss=baseline_loss, reference_loss=reference_loss,
                         fit=fit_info, build_seconds=time.monotonic() - started, **details, **geometry)
            manifest['cases'].append(entry)
            print(json.dumps(entry), flush=True)
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=241003906)
    parser.add_argument('--pool', choices=('core', 'challenge', 'all'), default='all')
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--example', action='store_true')
    arguments = parser.parse_args()
    if arguments.example:
        example, _, _ = build_case(90713022, 2, 'local_edges', 0, small=True)
        save_npz(arguments.root / 'participant/input/example.npz', example)
    for pool in ('core', 'challenge') if arguments.pool == 'all' else (arguments.pool,):
        generate_pool(arguments.root, pool, arguments.seed)


if __name__ == '__main__':
    main()
