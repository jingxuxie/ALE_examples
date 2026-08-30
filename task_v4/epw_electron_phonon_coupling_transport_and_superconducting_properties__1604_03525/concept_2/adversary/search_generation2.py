import argparse
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import numpy as np
from scipy.linalg import solve


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'authoring'))
sys.path.insert(0, str(ROOT / 'participant/workspace'))
from sandbox import run_submission
from physics import laplacian, score


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--submission', type=Path, required=True)
    args = parser.parse_args()
    directory = ROOT / 'adversary/generation_2_search'
    directory.mkdir(exist_ok=True)
    spec = importlib.util.spec_from_file_location('private_graph_generator', ROOT / 'evaluator/make_data.py')
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    settings = [('forward', 512, None), ('valleys', 640, None), ('hot_regions', 640, None),
                ('valleys', 768, None), ('mixed_scales', 768, None), ('hot_regions', 896, None),
                ('valleys', 384, 1e-6), ('valleys', 384, 1e-8)]
    jobs = []
    for index, (family, count, rare_scale) in enumerate(settings):
        name = f'{index}_{family}_{count}'
        data = generator.make_case(5139158 + index * 113, family, count, 8)
        temperatures = np.geomspace(10 if rare_scale else 18, 350, 10)
        thermal = np.geomspace(2.5, 85, 8)[None, :] / (0.08617333262145 * temperatures[:, None])
        mixing = thermal / np.sinh(thermal / 2) ** 2
        data.update(temperatures=temperatures, mixing=mixing / mixing.sum(axis=1)[:, None])
        if rare_scale:
            labels = np.argmax(data['probes'][:, 15:], axis=1)
            cross = labels[data['source']] != labels[data['target']]
            data['channels'][cross, :2] *= rare_scale
        path = directory / f'{name}.npz'
        np.savez_compressed(path, **data)
        jobs.append({'name': name, 'family': family, 'states': count, 'rare_scale': rare_scale, 'path': path.name})
    (directory / 'manifest.json').write_text(json.dumps(jobs, indent=2) + '\n')

    def test(item):
        result = dict(item, score=0.0, valid=False)
        try:
            with np.load(directory / item['path'], allow_pickle=False) as archive:
                data = dict(archive)
            if item['rare_scale']:
                weights = data['channels'] @ data['mixing'][0]
                matrix = laplacian(item['states'], data['source'], data['target'], weights)
                regular = solve(matrix + np.ones_like(matrix) / item['states'], data['velocities'], assume_a='pos')
                grounded = np.vstack([solve(matrix[:-1, :-1], data['velocities'][:-1], assume_a='pos'), np.zeros((1, 3))])
                conductivity = data['velocities'].T @ regular
                alternative = data['velocities'].T @ grounded
                error = np.linalg.norm(conductivity - alternative) / np.linalg.norm(conductivity)
                result['independent_reference_relative_error'] = float(error)
                if error > 1e-5:
                    raise ValueError('reference discrepancy: do not use this challenge case')
            with tempfile.TemporaryDirectory(prefix='epw_scale_probe_') as temporary:
                output = Path(temporary)
                runtime = run_submission(args.submission, directory / item['path'], output, timeout=90)
                result['runtime'] = runtime
                if runtime['returncode'] != 0 or runtime['timed_out']:
                    raise ValueError('resource or process failure')
                with np.load(output / 'result.npz', allow_pickle=False) as archive:
                    result.update(score(data, archive['indices'], archive['multipliers']))
                result.update(valid=True, reason='scored')
        except Exception as error:
            result['reason'] = str(error)
        (directory / f'{item["name"]}.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({key: result.get(key) for key in ['name', 'score', 'valid', 'reason', 'independent_reference_relative_error']}), flush=True)
        return result

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(test, jobs))
    (directory / 'summary.json').write_text(json.dumps({'cases': len(results), 'rows': results}, indent=2) + '\n')


if __name__ == '__main__':
    main()
