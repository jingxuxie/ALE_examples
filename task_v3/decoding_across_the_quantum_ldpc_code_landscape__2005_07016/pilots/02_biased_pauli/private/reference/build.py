import bootstrap
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import time
import numpy as np
from scipy.sparse import csr_matrix
from ldpc.mod2 import rank
from geometry import CLIFFORDS, PAULIS, assess, pairing, physical_generators, physical_logicals

ROOT = bootstrap.ROOT
REFERENCE = bootstrap.REFERENCE
POOL = bootstrap.PRIVATE / 'challenge_pool'
PROFILES = [
    dict(name='lp416_hadamard_x', n=416, frame='hadamard', rate=.10, weights=[24, 1, 1]),
    dict(name='lp416_clifford_joint', n=416, frame='clifford', rate=.115, weights=[1, 9, 13]),
    dict(name='lp882_hadamard_z', n=882, frame='hadamard', rate=.075, weights=[1, 1, 30]),
    dict(name='lp882_clifford_joint', n=882, frame='clifford', rate=.120, weights=[1, 9, 13]),
]
SEEDS = {'public': 190274633, 'calibration': 789031512, 'pilot': 270936111,
         'challenge': 846219735, 'correlation_screening_416': 589306157,
         'correlation_screening_882': 589306158}


def save_json(path, value):
    path = bootstrap.confined(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def gf_rank(matrix):
    sparse = csr_matrix(np.asarray(matrix, dtype=np.uint8) % 2)
    sparse.sum_duplicates()
    sparse.eliminate_zeros()
    assert sparse.nnz == np.count_nonzero(matrix)
    return int(rank(sparse))


def prepare():
    if (POOL / 'pilot' / 'manifest.json').exists() or (POOL / 'challenge' / 'manifest.json').exists():
        raise FileExistsError('Prestate is frozen; refusing to replace source assets or weak anchor')
    sources = bootstrap.RESEARCH / 'sources'
    upstream = REFERENCE / 'upstream'
    upstream.mkdir(parents=True, exist_ok=True)
    donor = sources / 'bp_osd' / 'src' / 'bposd' / 'css_decode_sim.py'
    shutil.copyfile(donor, upstream / 'bposd_css_decode_sim.py')
    shutil.copyfile(bootstrap.RESEARCH / 'isolation.py', REFERENCE / 'isolation.py')
    for repository in ('bp_osd', 'bias_tailored_qldpc'):
        shutil.copyfile(sources / repository / 'LICENSE', upstream / (repository + '.LICENSE'))
    shutil.copyfile(ROOT / 'participant' / 'workspace' / 'solve.py', REFERENCE / 'weak.py')
    legacy = ROOT.parent / '01_local_recovery' / 'participant' / 'workspace' / 'legacy_2020'
    if not legacy.is_dir():
        raise FileNotFoundError('Required fair-prestate legacy_2020 snapshot is missing')
    shutil.copytree(legacy, ROOT / 'participant' / 'workspace' / 'legacy_2020', dirs_exist_ok=True)
    provenance = {'source_files': {}, 'revisions': {}, 'matrix_audits': {},
                  'decoder': 'unmodified css_decode_sim._decoder_setup and _channel_update',
                  'parameters': {'max_iter': 'n//10', 'osd_order': 10, 'osd_method': 'osd_cs',
                                 'bp_method': 'minimum_sum', 'ms_scaling_factor': .625}}
    for repository in ('bp_osd', 'bias_tailored_qldpc'):
        provenance['revisions'][repository] = subprocess.check_output(
            ['git', '-C', str(sources / repository), 'rev-parse', 'HEAD'], text=True).strip()
    provenance['source_files']['css_decode_sim.py'] = digest(donor)
    for block_length, dimension, distance in ((416, 18, 20), (882, 24, 24)):
        code = {}
        for label in ('hx', 'hz', 'lx', 'lz'):
            name = f'lifted_product_[[{block_length},{dimension},{distance}]]_{label}.txt'
            path = sources / 'bias_tailored_qldpc' / 'parity_check_matrices' / name
            matrix = np.loadtxt(path)
            assert np.all((matrix == 0) | (matrix == 1))
            code['base_' + label if label in ('hx', 'hz') else label] = matrix.astype(np.uint8)
            provenance['source_files'][name] = digest(path)
        base_x, base_z, logical_x, logical_z = (code[name] for name in ('base_hx', 'base_hz', 'lx', 'lz'))
        assert not np.any(base_x @ base_z.T % 2)
        assert not np.any(logical_x @ base_z.T % 2)
        assert not np.any(logical_z @ base_x.T % 2)
        assert gf_rank(logical_x @ logical_z.T % 2) == dimension
        rank_x, rank_z = gf_rank(base_x), gf_rank(base_z)
        assert block_length - rank_x - rank_z == dimension
        assert gf_rank(np.vstack((base_x, logical_x))) == rank_x + dimension
        assert gf_rank(np.vstack((base_z, logical_z))) == rank_z + dimension
        code.update(n=np.array(block_length), k=np.array(dimension))
        (REFERENCE / 'codes').mkdir(exist_ok=True)
        np.savez_compressed(REFERENCE / 'codes' / f'lp{block_length}.npz', **code)
        (ROOT / 'participant' / 'input' / 'codes').mkdir(parents=True, exist_ok=True)
        np.savez_compressed(ROOT / 'participant' / 'input' / 'codes' / f'lp{block_length}.npz',
                            **{name: code[name] for name in ('base_hx', 'base_hz', 'n', 'k')})
        provenance['matrix_audits'][str(block_length)] = dict(n=block_length, k=dimension,
            rank_hx=rank_x, rank_hz=rank_z, logical_pairing_rank=dimension,
            hx_nonzeros=int(np.count_nonzero(base_x)), hz_nonzeros=int(np.count_nonzero(base_z)),
            lx_nonzeros=int(np.count_nonzero(logical_x)), lz_nonzeros=int(np.count_nonzero(logical_z)),
            explicit_sparse_zeros=0, logical_completeness=True)
    import scipy
    import ldpc
    provenance['runtime_versions'] = dict(numpy=np.__version__, scipy=scipy.__version__,
        ldpc_module=ldpc.__version__, bposd='2.1', ldpc_distribution='2.4.1; module banner says 2.4.0')
    save_json(REFERENCE / 'provenance.json', provenance)
    save_json(POOL / 'seed_manifest.json', {'generated_streams': SEEDS,
        'holdout': 'UNALLOCATED: choose fresh secret seed after challenge failure-region selection',
        'no_rejection_sampling': True})


def make_case(profile, seed, shots, shift=False):
    generator = np.random.default_rng(seed)
    with np.load(REFERENCE / 'codes' / f"lp{profile['n']}.npz", allow_pickle=False) as archive:
        code = dict(archive)
    block_length = profile['n']
    permutation = generator.permutation(block_length).astype(np.int64)
    if profile['frame'] == 'hadamard':
        frame = CLIFFORDS[np.concatenate((np.zeros(block_length // 2, dtype=int),
                                         np.ones(block_length - block_length // 2, dtype=int)))]
    else:
        frame = CLIFFORDS[generator.integers(0, len(CLIFFORDS), block_length)]
    generator_x, generator_z = physical_generators(code, frame, permutation)
    weights = np.asarray(profile['weights'], dtype=float)
    if shift:
        weights = weights * np.array([1.3, .85, 1.15])
    weights = weights / weights.sum()
    rates = profile['rate'] * generator.uniform(.88, 1.12, block_length)
    if shift:
        rates *= 1.05
    probabilities = np.column_stack((1 - rates, rates[:, None] * weights))
    if profile['frame'] == 'clifford':
        mapped = np.einsum('nij,kj->nki', frame, PAULIS) % 2
        labels = np.array([[0, 3], [1, 2]])[mapped[:, :, 0], mapped[:, :, 1]]
        physical = np.empty_like(probabilities)
        physical[permutation[:, None], labels] = probabilities
        probabilities = physical
    sampled = (generator.random((shots, block_length, 1))
               > np.cumsum(probabilities, axis=1)[None, :, :]).sum(axis=2)
    error_x, error_z = PAULIS[sampled, 0], PAULIS[sampled, 1]
    case = dict(schema_version=np.array(1), base_hx=code['base_hx'], base_hz=code['base_hz'],
                gx=generator_x, gz=generator_z, frame=frame, permutation=permutation,
                pauli_probs=probabilities,
                syndrome=pairing(error_x, error_z, generator_x, generator_z))
    logical_x, logical_z = physical_logicals(code, frame, permutation)
    truth = dict(logical_x=logical_x, logical_z=logical_z,
                 logical_signature=pairing(error_x, error_z, logical_x, logical_z),
                 error_x=error_x, error_z=error_z)
    assert not np.any(pairing(generator_x, generator_z, generator_x, generator_z))
    assert not np.any(pairing(logical_x, logical_z, generator_x, generator_z))
    assert gf_rank(pairing(logical_x, logical_z, logical_x, logical_z)) == 2 * int(code['k'])
    assert np.allclose(probabilities.sum(axis=1), 1)
    return case, truth


def materialize(split, shots, seed=None, profiles=None):
    from solve import decode
    spec = importlib.util.spec_from_file_location('weak_prestate', REFERENCE / 'weak.py')
    weak = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(weak)
    directory = POOL / split
    if directory.exists() and any(directory.iterdir()):
        raise FileExistsError(f'{split} is frozen; do not overwrite inspected seeds')
    directory.mkdir(parents=True, exist_ok=True)
    root_seed = SEEDS[split] if seed is None else seed
    manifest = {'split': split, 'seed': root_seed, 'cases': [], 'families': {},
                'normalization': 'unclipped affine success, frozen before participant runs',
                'cpu_budget_seconds': 60, 'wall_timeout_seconds': 180, 'memory_mb': 4096}
    for index, profile in enumerate(PROFILES if profiles is None else profiles):
        case_seed = np.random.SeedSequence([root_seed, index])
        case, truth = make_case(profile, case_seed, shots, shift=split in ('challenge', 'holdout'))
        case_path = directory / f'case_{index:02d}.npz'
        truth_path = directory / f'truth_{index:02d}.npz'
        np.savez_compressed(case_path, **case)
        metrics = {}
        for mode in ('weak', 'strong', 'independent', 'no_frame'):
            started = time.process_time()
            correction_x, correction_z = weak.decode(case) if mode == 'weak' else decode(case, mode)
            metrics[mode] = assess(case, truth, correction_x, correction_z)
            metrics[mode]['cpu_seconds'] = time.process_time() - started
            if mode in ('weak', 'strong'):
                assert metrics[mode]['consistency'] == 1.0
                np.savez_compressed(directory / f'{mode}_{index:02d}.npz',
                                    correction_x=correction_x, correction_z=correction_z)
            print(split, profile['name'], mode, metrics[mode], flush=True)
        gap = metrics['strong']['raw_logical_success'] - metrics['weak']['raw_logical_success']
        if gap < .15:
            raise ValueError(f'Insufficient strong/weak anchor separation: {profile["name"]}: {gap}')
        np.savez_compressed(truth_path, **truth)
        entry = dict(family=profile['name'], case=case_path.name, truth=truth_path.name,
                     case_sha256=digest(case_path), truth_sha256=digest(truth_path), shots=shots,
                     strong=f'strong_{index:02d}.npz', weak=f'weak_{index:02d}.npz',
                     strong_sha256=digest(directory / f'strong_{index:02d}.npz'),
                     weak_sha256=digest(directory / f'weak_{index:02d}.npz'), profile=profile)
        manifest['cases'].append(entry)
        manifest['families'][profile['name']] = {'weak': metrics['weak']['raw_logical_success'],
            'strong': metrics['strong']['raw_logical_success'], 'metrics': metrics}
    save_json(directory / 'manifest.json', manifest)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--split', choices=('calibration', 'pilot', 'challenge', 'holdout'))
    parser.add_argument('--shots', type=int, default=128)
    parser.add_argument('--holdout-seed', type=int)
    parser.add_argument('--profiles', type=Path)
    args = parser.parse_args()
    if args.prepare:
        prepare()
        examples = ROOT / 'participant' / 'input' / 'examples'
        examples.mkdir(exist_ok=True)
        for index, profile in enumerate((PROFILES[0], PROFILES[3])):
            case, _ = make_case(profile, np.random.SeedSequence([SEEDS['public'], index]), 3)
            np.savez_compressed(examples / f'smoke_{profile["n"]}.npz', **case)
    if args.split:
        if not 64 <= args.shots <= 256:
            parser.error('Scored/calibration batches require 64..256 shots')
        if args.split == 'holdout':
            if args.holdout_seed is None or args.profiles is None:
                parser.error('Holdout requires a NEW secret --holdout-seed and failure-region --profiles JSON')
            if args.holdout_seed in SEEDS.values():
                parser.error('Holdout seed must not reuse any inspected stream')
        elif args.holdout_seed is not None or args.profiles is not None:
            parser.error('Seed/profile overrides are reserved for fresh holdout')
        materialize(args.split, args.shots, args.holdout_seed,
                    json.loads(args.profiles.read_text()) if args.profiles else None)


if __name__ == '__main__':
    main()
