import os
import json
import resource
import subprocess
import time
import argparse
from pathlib import Path


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (2048 * 1024**2, 2048 * 1024**2))
    available = sorted(os.sched_getaffinity(0))
    offset = int(os.environ.get('TEST_CORE_OFFSET', 0))
    os.sched_setaffinity(0, available[offset:offset+4])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source')
    parser.add_argument('--offset', type=int, default=0)
    parser.add_argument('--count', type=int, default=320)
    parser.add_argument('--report', default='runtime_check.json')
    parser.add_argument('--cwd')
    args = parser.parse_args()
    root = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/level_statistics_phase_diagram_of_the_random_field_heisenberg_chain_pa__1010_1992/concept_1/generations/generation_2/participant/input')
    source = Path(args.source) if args.source else root / 'validation.jsonl'
    records = [json.loads(line) for line in source.read_text().splitlines()][args.offset:args.offset+args.count]
    cases = [{'id': f'check_{index}', 'L': 14, 'fields': records[index % len(records)]['fields']} for index in range(args.count)]
    started = time.monotonic()
    process = subprocess.Popen(['python3', '-s', str(Path(__file__).with_name('predict.py').resolve())], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, preexec_fn=limits, cwd=args.cwd)
    ready = process.stdout.readline()
    startup = time.monotonic() - started
    if ready != 'READY\n':
        raise RuntimeError((ready, process.stderr.read()))
    started = time.monotonic()
    stdout, stderr = process.communicate(json.dumps({'cases': cases}) + '\n', timeout=15)
    runtime = time.monotonic() - started
    response = json.loads(stdout)
    predictions = response['predictions']
    assert process.returncode == 0, stderr
    assert set(response) == {'predictions'}
    assert len(predictions) == len(cases)
    assert {entry['id'] for entry in predictions} == {entry['id'] for entry in cases}
    assert all(set(entry) == {'id', 'f'} and type(entry['f']) in (int, float) and 0 <= entry['f'] <= 1 for entry in predictions)
    lookup = {entry['id']: entry['f'] for entry in predictions}
    residuals = [(lookup[f'check_{index}'] - record['f'])**2 for index, record in enumerate(records)]
    families = {family: (sum(error for error, record in zip(residuals, records) if record['family'] == family) / sum(record['family'] == family for record in records))**.5 for family in sorted({record['family'] for record in records})}
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    result = {'startup_seconds': startup, 'inference_seconds': runtime, 'cpu_seconds_including_startup': usage.ru_utime + usage.ru_stime, 'peak_rss_kib': usage.ru_maxrss, 'overall_rmse': (sum(residuals) / len(residuals))**.5, 'family_rmse': families, 'worst_family_rmse': max(families.values()), 'protocol_valid': True, 'resource_valid': startup <= 60 and runtime <= 3, 'source': str(source), 'offset': args.offset, 'records_scored': len(records), 'batch_size': len(cases), 'stderr': stderr}
    print(json.dumps(result, indent=2))
    Path(args.report).write_text(json.dumps(result, indent=2) + '\n')
    assert result['resource_valid'], 'Startup or inference exceeds its time limit'
