import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'reference'))
import bootstrap
import argparse
import hashlib
import io
import json
import tempfile
import zipfile
import numpy as np
from geometry import assess


def load_npz(path):
    with np.load(path, allow_pickle=False) as archive:
        return dict(archive)


def check_digest(path, expected):
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError(f'Frozen private asset changed: {path.name}')


def grade_answer(payload, case, truth):
    if not payload or len(payload) > 16 * 1024 * 1024:
        raise ValueError('Missing or oversized output')
    expected = (len(case['syndrome']), len(case['frame']))
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as container:
            if sorted(container.namelist()) != ['correction_x.npy', 'correction_z.npy']:
                raise ValueError('Invalid NPZ members')
            for member in container.infolist():
                if member.file_size > 8 * 1024 * 1024:
                    raise ValueError('Oversized uncompressed array')
                with container.open(member) as stream:
                    version = np.lib.format.read_magic(stream)
                    if version == (1, 0):
                        shape, _, dtype = np.lib.format.read_array_header_1_0(stream)
                    elif version == (2, 0):
                        shape, _, dtype = np.lib.format.read_array_header_2_0(stream)
                    else:
                        raise ValueError('Unsupported NPY version')
                    if shape != expected or dtype.kind not in 'biu' or dtype.itemsize > 8:
                        raise ValueError('Invalid declared correction shape or dtype')
    except zipfile.BadZipFile as error:
        raise ValueError('Malformed NPZ') from error
    with np.load(io.BytesIO(payload), allow_pickle=False) as archive:
        if set(archive.files) != {'correction_x', 'correction_z'} or len(archive.files) != 2:
            raise ValueError('Output keys must be exactly correction_x and correction_z')
        answers = [archive[name] for name in ('correction_x', 'correction_z')]
    for answer in answers:
        if answer.shape != expected or answer.dtype.kind not in 'biu':
            raise ValueError('Invalid correction shape or dtype')
        if not np.all((answer == 0) | (answer == 1)):
            raise ValueError('Corrections must be binary')
    return assess(case, truth, *(answer.astype(np.uint8) for answer in answers))


def summarize(manifest, records):
    families = {}
    for family, anchors in manifest['families'].items():
        selected = [record for record in records if record['family'] == family]
        shots = sum(record['shots'] for record in selected)
        success_count = sum(record['success_count'] for record in selected)
        consistent_count = sum(record['consistent_count'] for record in selected)
        rate = success_count / shots
        gap = anchors['strong'] - anchors['weak']
        if gap <= 0:
            raise ValueError('Invalid anchor separation')
        families[family] = dict(raw_logical_success=rate, success_count=success_count, shots=shots,
            consistency=consistent_count / shots, weak_anchor=anchors['weak'],
            strong_anchor=anchors['strong'], normalized_quality=(rate - anchors['weak']) / gap,
            runtime_cpu_seconds=sum(record.get('runtime_cpu_seconds', 0) for record in selected),
            runtime_wall_seconds=sum(record.get('runtime_wall_seconds', 0) for record in selected))
    qualities = [family['normalized_quality'] for family in families.values()]
    total_shots = sum(record['shots'] for record in records)
    return dict(schema_version=1, split=manifest['split'], mean_core=float(np.mean(qualities)),
        worst_family=float(min(qualities)), families=families, cases=records,
        consistency=sum(record['consistent_count'] for record in records) / total_shots,
        runtime_cpu_seconds=sum(record.get('runtime_cpu_seconds', 0) for record in records),
        runtime_wall_seconds=sum(record.get('runtime_wall_seconds', 0) for record in records),
        normalization='unclipped (logical_success - frozen_weak)/(frozen_strong - frozen_weak)')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--submission', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--split', choices=('pilot', 'challenge', 'holdout'), required=True)
    args = parser.parse_args()
    submission = args.submission.resolve()
    report_path = bootstrap.confined(args.report)
    directory = bootstrap.PRIVATE / 'challenge_pool' / args.split
    if not (directory / 'manifest.json').exists():
        parser.error('Split not generated. Holdout stays deferred until a fresh failure-region build.')
    if not (submission / 'solve.py').is_file():
        parser.error('Submission must contain solve.py')
    manifest = json.loads((directory / 'manifest.json').read_text())
    from isolation import run_submission
    temporary_root = bootstrap.REFERENCE / '.runtime'
    temporary_root.mkdir(exist_ok=True)
    tempfile.tempdir = str(temporary_root)
    records = []
    for entry in manifest['cases']:
        case_path, truth_path = directory / entry['case'], directory / entry['truth']
        check_digest(case_path, entry['case_sha256'])
        check_digest(truth_path, entry['truth_sha256'])
        case, truth = load_npz(case_path), load_npz(truth_path)
        result = run_submission(submission, bootstrap.ROOT / 'participant', case_path,
                                timeout=max(60, 3 * manifest['cpu_budget_seconds']),
                                memory_mb=manifest['memory_mb'])
        cpu = result.get('user_seconds', 0) + result.get('system_seconds', 0)
        record = dict(family=entry['family'], case=entry['case'], shots=entry['shots'],
                      runtime_cpu_seconds=cpu, runtime_wall_seconds=result['elapsed_seconds'],
                      max_rss_kb=result.get('max_rss_kb'), returncode=result['returncode'],
                      timeout=result['timeout'], stderr=result.get('stderr', '')[-1000:])
        try:
            if result['timeout'] or result['returncode'] != 0:
                raise ValueError('Submission failed or timed out')
            if 'user_seconds' not in result or 'system_seconds' not in result:
                raise ValueError('Missing CPU accounting from isolation launcher')
            if cpu > manifest['cpu_budget_seconds']:
                raise ValueError('CPU budget exceeded')
            record.update(grade_answer(result['answer_bytes'], case, truth))
        except (ValueError, KeyError, OSError, EOFError) as error:
            record.update(success_count=0, consistent_count=0,
                          raw_logical_success=0., consistency=0., error=str(error))
        records.append(record)
    report = summarize(manifest, records)
    report.update(submission=str(submission), isolation='bwrap via shared run_submission; no host imports')
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({name: report[name] for name in ('mean_core', 'worst_family', 'consistency',
                                                     'runtime_cpu_seconds', 'runtime_wall_seconds')}))


if __name__ == '__main__':
    main()
