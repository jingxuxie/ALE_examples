import argparse
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'authoring'))
sys.path.insert(0, str(ROOT / 'participant' / 'workspace'))
from sandbox import run_submission
from physics import score


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--submission', type=Path, required=True)
    args = parser.parse_args()
    folder = ROOT / 'adversary' / 'challenge_pool'
    cases = json.loads((folder / 'manifest.json').read_text())
    spec = importlib.util.spec_from_file_location('private_generator', ROOT / 'evaluator' / 'make_data.py')
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    for offset, (family, state_count, branches) in enumerate([('forward', 256, 6), ('valleys', 256, 6),
                                                             ('valleys', 384, 8), ('hot_regions', 384, 8)]):
        name = f'scaling_{family}_{state_count}'
        data = generator.make_case(552819 + offset * 73, family, state_count, branches)
        temperatures = np.geomspace(18, 350, 10)
        energies = np.geomspace(2.5, 85, branches)
        thermal = energies[None, :] / (0.08617333262145 * temperatures[:, None])
        mixing = thermal / np.sinh(thermal / 2) ** 2
        mixing /= mixing.sum(axis=1)[:, None]
        data.update(temperatures=temperatures, mixing=mixing)
        np.savez_compressed(folder / f'{name}.npz', **data)
        cases.append({'name': name, 'family': family, 'path': f'{name}.npz', 'states': state_count,
                      'branches': branches, 'expanded_range': True})
    (folder / 'broad_manifest.json').write_text(json.dumps(cases, indent=2) + '\n')
    results = ROOT / 'adversary' / 'champion_search'
    results.mkdir(exist_ok=True)

    def test(item):
        row = dict(item, valid=False, passed=False, score=0.0)
        try:
            with tempfile.TemporaryDirectory(prefix='epw_champion_probe_') as temporary:
                output = Path(temporary)
                runtime = run_submission(args.submission, folder / item['path'], output, timeout=90)
                row['runtime'] = runtime
                if runtime['returncode'] != 0 or runtime['timed_out']:
                    raise ValueError('resource or process failure')
                with np.load(output / 'result.npz', allow_pickle=False) as archive:
                    indices, multipliers = archive['indices'], archive['multipliers']
                with np.load(folder / item['path'], allow_pickle=False) as archive:
                    row.update(score(archive, indices, multipliers))
                row.update(valid=True, passed=row['score'] >= 80, reason='scored')
        except Exception as error:
            row['reason'] = str(error)
        (results / f'{item["name"]}.json').write_text(json.dumps(row, indent=2, allow_nan=False) + '\n')
        print(json.dumps({key: row.get(key) for key in ['name', 'score', 'valid', 'reason', 'relative_error']}), flush=True)
        return row

    with ThreadPoolExecutor(max_workers=4) as executor:
        rows = list(executor.map(test, cases))
    (results / 'summary.json').write_text(json.dumps({'cases': len(rows), 'valid': sum(row['valid'] for row in rows),
                                                    'below_80': sum(row['score'] < 80 for row in rows),
                                                    'rows': rows}, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
