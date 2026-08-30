import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ[variable] = '1'
import argparse
import concurrent.futures
import json
from pathlib import Path
import sys
import time
sys.dont_write_bytecode = True
PARTICIPANT = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/level_statistics_phase_diagram_of_the_random_field_heisenberg_chain_pa__1010_1992/concept_3/participant')
sys.path.insert(0, str(PARTICIPANT / 'workspace'))
import numpy as np
from exact import assess, family_fields, proxy_statistics, spectrum, validate_fields

PROTOCOL = json.loads((PARTICIPANT / 'input/protocol.json').read_text())
OFFSETS = np.array([family['offsets'] for family in PROTOCOL['families']])
SCALES = np.array([family['scale'] for family in PROTOCOL['families']])

def valid(fields):
    try:
        validate_fields(fields)
        return True
    except ValueError:
        return False

def base_measure(candidate):
    fields, kind = candidate
    try:
        statistics = proxy_statistics(spectrum(fields))
        return dict(fields=list(fields), kind=kind, base=statistics['difference'],
                    orientation=1 if statistics['difference'] >= 0 else -1,
                    ranks=[window['nearest_rank'] for window in statistics['windows']])
    except ValueError:
        return None

def partial_measure(candidate):
    fields = np.array(candidate['fields'])
    differences = []
    try:
        for family in range(4):
            for member in (0, 4):
                profile = SCALES[family] * fields + OFFSETS[family, member]
                statistics = proxy_statistics(spectrum(profile))
                differences.append(candidate['orientation'] * statistics['difference'])
        candidate['partial'] = differences
        candidate['partial_score'] = float(np.mean(differences) - 0.2 * np.std(np.mean(np.array(differences).reshape(4, 2), axis=1)))
        return candidate
    except ValueError:
        return None

def objective(report):
    core = report['core']
    worst = report['worst_family']
    base = report['base']['signed_difference']
    coverage = min(sorted(row['signed_difference'] for row in report['members'] if row['family'] == family['family'])[2] for family in report['families'])
    margin = min(core - 0.060, worst - 0.050, base - 0.055, coverage - 0.025)
    return float(margin + 0.15 * core), float(margin), float(coverage)

def full_measure(candidate):
    witness = dict(schema_version=1, fields=candidate['fields'], orientation=candidate['orientation'])
    try:
        report = assess(witness, PROTOCOL)
        score, margin, coverage = objective(report)
        candidate.update(score=score, margin=margin, coverage=coverage,
                         core=report['core'], worst=report['worst_family'],
                         base=report['base']['signed_difference'], passed=report['pass'])
        return candidate, report
    except ValueError:
        return None

def generate(random, count):
    candidates = []
    sites = np.arange(12)
    while len(candidates) < count:
        kind = int(random.integers(0, 12))
        strength = random.uniform(0.9, 7.8)
        noise = random.uniform(0.12, 1.0)
        if kind < 5:
            fields = random.uniform(-strength, strength, 12)
        elif kind == 5:
            fields = random.normal(0, strength / 2, 12)
        elif kind == 6:
            fields = random.choice([-1., 1.], 12) * strength + random.normal(0, noise, 12)
        elif kind == 7:
            fields = np.zeros(12)
            selected = random.choice(12, int(random.integers(1, 6)), replace=False)
            fields[selected] = random.choice([-1., 1.], len(selected)) * strength
            fields += random.normal(0, noise, 12)
        elif kind == 8:
            fields = strength * np.cos(2 * np.pi * random.uniform(0.1, 0.9) * sites + random.uniform(0, 2*np.pi)) + random.normal(0, noise, 12)
        elif kind == 9:
            fields = random.choice([-1., 0., 1.], 12) * strength + random.normal(0, noise, 12)
        elif kind == 10:
            fields = np.tile(random.uniform(-strength, strength, int(random.choice([2, 3, 4, 6]))), 6)[:12] + random.normal(0, noise, 12)
        else:
            fields = strength * np.linspace(-1, 1, 12) + random.normal(0, noise, 12)
            if random.random() < 0.5:
                random.shuffle(fields)
        fields -= fields.mean()
        maximum = np.max(np.abs(fields))
        if maximum > 7.97:
            fields *= 7.97 / maximum
        if valid(fields):
            candidates.append((fields.tolist(), kind))
    return candidates

def save_result(candidate, report, output, label):
    witness = dict(schema_version=1, fields=candidate['fields'], orientation=candidate['orientation'])
    (output / f'{label}.json').write_text(json.dumps(witness, indent=2) + '\n')
    (output / f'{label}.report.json').write_text(json.dumps(report, indent=2) + '\n')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=8101992)
    parser.add_argument('--candidates', type=int, default=6144)
    parser.add_argument('--partial', type=int, default=640)
    parser.add_argument('--finalists', type=int, default=128)
    parser.add_argument('--output', type=Path, default=Path('.'))
    args = parser.parse_args()
    start = time.monotonic()
    random = np.random.default_rng(args.seed)
    candidates = generate(random, args.candidates)
    print('generated', len(candidates), 'seconds', time.monotonic()-start, flush=True)
    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
        screened = []
        for index, candidate in enumerate(executor.map(base_measure, candidates, chunksize=4)):
            if candidate is not None:
                screened.append(candidate)
            if (index + 1) % 512 == 0:
                print('base', index+1, 'best', max(abs(item['base']) for item in screened), 'seconds', time.monotonic()-start, flush=True)
        screened.sort(key=lambda item: abs(item['base']), reverse=True)
        (args.output / 'screened.json').write_text(json.dumps(screened))
        partials = [candidate for candidate in executor.map(partial_measure, screened[:args.partial]) if candidate is not None]
        partials.sort(key=lambda item: item['partial_score'], reverse=True)
        (args.output / 'partials.json').write_text(json.dumps(partials))
        print('partial best', [(item['partial_score'], item['base'], item['kind']) for item in partials[:10]], 'seconds', time.monotonic()-start, flush=True)
        results = []
        best = None
        for result in executor.map(full_measure, partials[:args.finalists]):
            if result is None:
                continue
            candidate, report = result
            results.append(candidate)
            if best is None or candidate['score'] > best['score']:
                best = candidate
                save_result(candidate, report, args.output, 'witness')
                print('BEST', json.dumps({key:value for key,value in candidate.items() if key not in ('fields', 'partial')}), 'seconds', time.monotonic()-start, flush=True)
            if candidate['passed']:
                save_result(candidate, report, args.output, 'passing')
        results.sort(key=lambda item:item['score'], reverse=True)
        (args.output / 'finalists.json').write_text(json.dumps(results, indent=2))
    print('complete', time.monotonic()-start, flush=True)

if __name__ == '__main__':
    main()
