import bootstrap
import io
import json
import shutil
import sys
import numpy as np
from build import digest, save_json

sys.path.insert(0, str(bootstrap.PRIVATE))
from evaluator import check_digest, grade_answer, load_npz, summarize


def independent_pairing(error_x, error_z, operator_x, operator_z):
    signatures = np.empty((len(error_x), len(operator_x)), dtype=np.uint8)
    for index, (row_x, row_z) in enumerate(zip(operator_x, operator_z)):
        signatures[:, index] = (np.bitwise_xor.reduce(error_x[:, np.flatnonzero(row_z)], axis=1, initial=0)
                                ^ np.bitwise_xor.reduce(error_z[:, np.flatnonzero(row_x)], axis=1, initial=0))
    return signatures


def independent_rank(matrix):
    basis = {}
    for row in matrix:
        value = int.from_bytes(np.packbits(row, bitorder='little').tobytes(), 'little')
        while value:
            pivot = value.bit_length()
            if pivot in basis:
                value ^= basis[pivot]
            else:
                basis[pivot] = value
                break
    return len(basis)


def payload(correction_x, correction_z):
    stream = io.BytesIO()
    np.savez_compressed(stream, correction_x=correction_x, correction_z=correction_z)
    return stream.getvalue()


def main():
    evidence = {'independent_dense_support_audit': True, 'logical_degeneracy_audit': True,
                'reference_correction_validity': True, 'splits': {}}
    hashes = set()
    for split in ('pilot', 'challenge'):
        directory = bootstrap.PRIVATE / 'challenge_pool' / split
        manifest = json.loads((directory / 'manifest.json').read_text())
        by_mode = {'strong': [], 'weak': []}
        for entry in manifest['cases']:
            for label in ('case', 'truth', 'strong', 'weak'):
                check_digest(directory / entry[label], entry[label + '_sha256'])
            assert entry['case_sha256'] not in hashes
            hashes.add(entry['case_sha256'])
            replay = bootstrap.REFERENCE / 'replay_reference' / 'answers'
            replay.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(directory / entry['strong'], replay / (entry['case_sha256'] + '.npz'))
            case, truth = load_npz(directory / entry['case']), load_npz(directory / entry['truth'])
            error_x, error_z = truth['error_x'], truth['error_z']
            canonical_x, canonical_z = np.empty_like(error_x), np.empty_like(error_z)
            for canonical, physical in enumerate(case['permutation']):
                frame = case['frame'][canonical]
                canonical_x[:, canonical] = ((frame[1, 1] * error_x[:, physical])
                                             ^ (frame[0, 1] * error_z[:, physical]))
                canonical_z[:, canonical] = ((frame[1, 0] * error_x[:, physical])
                                             ^ (frame[0, 0] * error_z[:, physical]))
            canonical_syndrome = np.concatenate((canonical_z @ case['base_hx'].T % 2,
                                                  canonical_x @ case['base_hz'].T % 2), axis=1)
            np.testing.assert_array_equal(canonical_syndrome, case['syndrome'])
            np.testing.assert_array_equal(independent_pairing(error_x, error_z, case['gx'], case['gz']),
                                          case['syndrome'])
            np.testing.assert_array_equal(independent_pairing(error_x, error_z,
                truth['logical_x'], truth['logical_z']), truth['logical_signature'])
            generator = np.concatenate((case['gx'], case['gz']), axis=1)
            logical = np.concatenate((truth['logical_x'], truth['logical_z']), axis=1)
            dimension = len(logical) // 2
            assert independent_rank(generator) == len(case['frame']) - dimension
            assert independent_rank(np.vstack((generator, logical))) == len(case['frame']) + dimension
            assert not independent_pairing(truth['logical_x'], truth['logical_z'], case['gx'], case['gz']).any()
            for mode in by_mode:
                assert manifest['families'][entry['family']]['metrics'][mode]['cpu_seconds'] < 60
                answer = (directory / entry[mode]).read_bytes()
                metric = grade_answer(answer, case, truth)
                assert metric['consistency'] == 1.
                actual = load_npz(directory / entry[mode])
                np.testing.assert_array_equal(independent_pairing(actual['correction_x'], actual['correction_z'],
                    case['gx'], case['gz']), case['syndrome'])
                actual['correction_x'] ^= case['gx'][0]
                actual['correction_z'] ^= case['gz'][0]
                assert grade_answer(payload(**actual), case, truth) == metric
                metric.update(family=entry['family'], case=entry['case'],
                              runtime_cpu_seconds=manifest['families'][entry['family']]['metrics'][mode]['cpu_seconds'],
                              runtime_wall_seconds=0)
                by_mode[mode].append(metric)
            perfect = grade_answer(payload(error_x, error_z), case, truth)
            assert perfect['raw_logical_success'] == 1
            logical_failure = grade_answer(payload(error_x ^ truth['logical_x'][0],
                                                    error_z ^ truth['logical_z'][0]), case, truth)
            assert logical_failure['consistency'] == 1
            assert logical_failure['raw_logical_success'] == 0
            invalid = grade_answer(payload(error_x ^ np.eye(1, error_x.shape[1], dtype=np.uint8)[0],
                                            error_z), case, truth)
            assert invalid['consistency'] == 0
            for bad in (payload(error_x.astype(float), error_z), payload(error_x.T, error_z), b'not an npz'):
                try:
                    grade_answer(bad, case, truth)
                except (ValueError, OSError):
                    pass
                else:
                    raise AssertionError('Malformed answer was accepted')
        reports = {mode: summarize(manifest, records) for mode, records in by_mode.items()}
        assert reports['strong']['mean_core'] > .9 and reports['strong']['worst_family'] > .9
        assert reports['weak']['mean_core'] == 0
        for mode, report in reports.items():
            report['validation_mode'] = 'precomputed actual decoder corrections; independent support audit; not an agent run'
            report['runtime_wall_seconds'] = None
            save_json(bootstrap.REFERENCE / 'evidence' / f'{split}_{mode}_report.json', report)
        evidence['splits'][split] = {mode: {name: report[name] for name in
            ('mean_core', 'worst_family', 'consistency', 'runtime_cpu_seconds')} for mode, report in reports.items()}
    assert not list((bootstrap.ROOT / 'attempt').iterdir())
    assert not (bootstrap.PRIVATE / 'challenge_pool' / 'holdout').exists()
    public_files = {}
    for path in (bootstrap.ROOT / 'participant').rglob('*'):
        if path.is_file():
            assert not path.is_symlink()
            public_files[str(path.relative_to(bootstrap.ROOT / 'participant'))] = digest(path)
            if path.suffix == '.npz':
                with np.load(path, allow_pickle=False) as archive:
                    assert not {'lx', 'lz', 'logical_signature', 'error_x', 'error_z', 'seed',
                                'correction_x', 'correction_z'} & set(archive.files)
    save_json(bootstrap.REFERENCE / 'participant_manifest.json', public_files)
    evidence.update(attempt_empty=True, holdout_unallocated=True, public_label_audit=True,
                    no_agents_launched=True, no_pilots_launched=True)
    save_json(bootstrap.REFERENCE / 'evidence' / 'audit.json', evidence)
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
