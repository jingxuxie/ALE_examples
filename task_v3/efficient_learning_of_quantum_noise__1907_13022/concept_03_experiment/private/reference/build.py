import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np
from scipy.optimize import least_squares
from solver import solve, walsh, fit_modes, marginal, diagnostics


ROOT = Path(__file__).resolve().parents[2]
SOURCES = ROOT.parent / 'private' / 'sources' / 'Juqst.jl' / 'docs' / 'examples' / 'quantumNoise' / 'data'


def make_metadata(qubits, seed):
    random = np.random.default_rng(seed)
    blocks = np.eye(qubits, dtype=np.uint8)
    queries = []
    for index in range(16):
        order = random.permutation(qubits)
        widths = (1 + index % 2, 1 + (index // 2) % 2, index % 3)
        query = np.zeros((3, qubits), dtype=np.uint8)
        start = 0
        for group, width in enumerate(widths):
            query[group, order[start:start + width]] = 1
            start += width
        queries.append(query)
    parents = np.zeros((qubits, qubits), dtype=np.uint8)
    order = []
    for index in range((qubits + 1) // 2):
        order.append(index)
        if qubits - 1 - index != index:
            order.append(qubits - 1 - index)
    for position, qubit in enumerate(order[:-1]):
        parents[qubit, order[position + 1:min(position + 3, qubits)]] = 1
    return dict(blocks=blocks, conditional_queries=np.asarray(queries), parents=parents)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=19713022)
    args = parser.parse_args()
    reference = ROOT / 'private' / 'reference'
    cases = reference / 'cases'
    cases.mkdir(exist_ok=True)
    source_specs = [
        ('single', 'results14Single_1_5_10_15_20_30_45_60_75_90_105.csv', [1,5,10,15,20,30,45,60,75,90,105]),
        ('mixed_a', 'results14InterleavedAC_0.csv', list(range(11))),
        ('mixed_b', 'results14InterleavedAC_1.csv', list(range(11))),
        ('mixed_c', 'results14InterleavedAC_2.csv', list(range(11)))]
    manifest = []
    checks = []
    for source_index, (family, filename, depths) in enumerate(source_specs):
        raw = np.loadtxt(SOURCES / filename, delimiter=',', dtype=np.int64)
        for variant in range(5):
            keep = np.arange(len(depths) - variant) if variant < 3 else np.arange(variant - 2, len(depths))
            pool = 'core' if variant < 3 else 'challenge'
            identifier = f'{family}_{variant}'
            directory = cases if pool == 'core' else ROOT / 'private' / 'challenge_pool'
            input_path = directory / f'{identifier}.npz'
            target_path = directory / f'{identifier}.reference.npz'
            metadata = make_metadata(14, args.seed + 31 * source_index + variant)
            if source_index and variant % 2:
                blocks = []
                for first in range(0, 14, 2):
                    block = np.zeros(14, dtype=np.uint8)
                    block[first:first + 2] = 1
                    blocks.append(block)
                metadata['blocks'] = np.asarray(blocks)
            np.savez_compressed(input_path, n=np.array(14), depths=np.asarray(depths)[keep], counts=raw[keep], **metadata)
            started = time.monotonic()
            solve(input_path, target_path)
            target = np.load(target_path)
            check = dict(case=identifier, reference_seconds=time.monotonic()-started,
                         normalized=float(target['probabilities'].sum()), minimum=float(target['probabilities'].min()))
            if variant == 0:
                probabilities = raw / raw.sum(axis=1, keepdims=True)
                modes = walsh(probabilities)
                rates, amplitudes, stops = fit_modes(np.asarray(depths), modes)
                differences = []
                for mode in np.random.default_rng(81).choice(np.arange(1, 16384), 32, replace=False):
                    stop = stops[mode - 1]
                    selected_depths = np.asarray(depths[:stop])
                    response = modes[:stop, mode]
                    fit = least_squares(lambda parameters: parameters[0]*parameters[1]**selected_depths-response,
                                        [.8,.8], bounds=([.01,.01],[1.,1.]), ftol=1e-12, xtol=1e-12, gtol=1e-12)
                    differences.append(abs(fit.x[1]-rates[mode]))
                check['max_independent_rate_difference'] = max(differences)
                assert max(differences) < 1e-5, check
            assert abs(check['normalized']-1.) < 1e-10
            checks.append(check)
            manifest.append(dict(id=identifier, family=family, pool=pool,
                                 input=str(input_path.relative_to(ROOT/'private')),
                                 reference=str(target_path.relative_to(ROOT/'private')),
                                 source=filename, rows=keep.tolist(),
                                 sha256=hashlib.sha256(input_path.read_bytes()).hexdigest()))
        if source_index == 0:
            sample_counts = np.stack([np.bincount(np.arange(16384)&7, weights=row, minlength=8) for row in raw]).astype(np.int64)
            np.savez_compressed(ROOT/'participant'/'input'/'example.npz', n=np.array(3),
                                counts=sample_counts, depths=np.asarray(depths), **make_metadata(3, args.seed))
    (reference/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    (reference/'validation.json').write_text(json.dumps(checks, indent=2)+'\n')
    print(json.dumps(dict(cases=len(manifest), max_reference_seconds=max(row['reference_seconds'] for row in checks))))


if __name__ == '__main__':
    main()
