import argparse
import concurrent.futures
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'participant/workspace'))
sys.path.insert(0, str(ROOT / 'evaluator'))
from atlas import Atlas
from evaluate import aggregate, fingerprints, validate_result, verify_frozen_package
from isolation import replay, safe_tree


def run_case(job):
    case, cases, submission, output, cores = job
    os.sched_setaffinity(0, cores)
    atlas = Atlas.load(cases / case['directory'])
    row = {'case_id': case['id'], 'family': case['family'], 'baseline_objective': atlas.metadata['baseline_objective']}
    try:
        (output / case['id']).mkdir()
        result, runtime = replay(submission, ROOT / 'participant/workspace', cases / case['directory'],
                                 output / case['id'] / 'output', seconds=90)
        row['runtime'] = runtime
        if result is not None:
            score = validate_result(result, atlas)
            row['score'] = score
            row['feasible'] = score['feasible']
            if score['feasible']:
                row['gain'] = 1.0 - score['objective'] / row['baseline_objective']
        else:
            row['feasible'] = False
    except Exception as error:
        row['feasible'] = False
        row['error'] = str(error)
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cases', required=True, type=Path)
    parser.add_argument('--submission', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--workers', type=int, default=2)
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    output.relative_to(ROOT / 'adversary/ratchet3')
    output.mkdir(parents=True, exist_ok=False)
    frozen_hash = verify_frozen_package()
    policy = json.loads((ROOT / 'participant/workspace/policy.json').read_text())
    assert (policy['mean_gain_min'], policy['worst_family_gain_min'], policy['wall_seconds_per_case']) == (0.07, 0.057, 90)
    safe_tree(arguments.submission)
    source_hashes = fingerprints(arguments.submission)
    submission = output / 'submission'
    shutil.copytree(arguments.submission, submission)
    assert fingerprints(submission) == source_hashes
    cases = arguments.cases.resolve()
    case_hashes = fingerprints(cases)
    manifest = json.loads((cases / 'manifest.json').read_text())
    available = sorted(os.sched_getaffinity(0))
    cores = available[-4 * arguments.workers:]
    assert len(cores) == 4 * arguments.workers
    pools = [concurrent.futures.ProcessPoolExecutor(max_workers=1, mp_context=multiprocessing.get_context('spawn')) for worker in range(arguments.workers)]
    started = time.monotonic()
    futures = []
    for position, case in enumerate(manifest['cases']):
        worker = position % arguments.workers
        futures.append(pools[worker].submit(run_case, (case, cases, submission, output, cores[4 * worker:4 * worker + 4])))
    rows = []
    for future in concurrent.futures.as_completed(futures):
        row = future.result()
        rows.append(row)
        summary = aggregate(rows, policy)
        report = {'policy': policy, 'rows': sorted(rows, key=lambda item: item['case_id']), 'summary': summary,
                  'elapsed_seconds': time.monotonic() - started, 'submission_sha256': source_hashes,
                  'input_sha256': case_hashes, 'frozen_manifest_sha256': frozen_hash,
                  'complete': len(rows) == len(manifest['cases']), 'workers': arguments.workers,
                  'caps': {'seconds_per_case': 90, 'cores_per_case': 4, 'address_space_bytes': 2147483648}}
        (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        print(row['case_id'], 'gain', row.get('gain'), 'runtime', row.get('runtime'), flush=True)
    for pool in pools:
        pool.shutdown()
    assert fingerprints(cases) == case_hashes
    assert verify_frozen_package() == frozen_hash
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
