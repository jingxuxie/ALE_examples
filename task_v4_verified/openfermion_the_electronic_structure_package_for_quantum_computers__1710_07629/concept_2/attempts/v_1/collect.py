import argparse
import sys
import time
from peel import *

sys.path.insert(0, str(ASSETS / 'workspace'))
from simulator import evaluate


def collect():
    circuits = []
    selected = []
    for instance in INSTANCES:
        choices = []
        expected = target(instance)
        for path in Path('.').glob(instance['id'] + '_*.json'):
            try:
                circuit = json.loads(path.read_text())
                if not isinstance(circuit, dict) or set(circuit) != {'id', 'layers'} or circuit['id'] != instance['id']:
                    continue
                matrix = np.diag([complex(mode in instance['initial_occupied']) for mode in range(instance['n_modes'])])
                count = 0
                for layer in circuit['layers']:
                    for gate in layer:
                        matrix = rotate(matrix, gate['u'], gate['v'], gate['theta'], gate['phi'])
                        count += 1
                error = np.linalg.norm(matrix - expected)
                if error > 1e-8:
                    continue
                depth = len(circuit['layers'])
                resource = min(1.0, instance['budgets']['max_gates'] / max(1, count), instance['budgets']['max_depth'] / max(1, depth))
                choices.append(((resource, -count, -depth), circuit, path.name, error))
            except (ValueError, TypeError, KeyError, IndexError):
                continue
        if not choices:
            raise RuntimeError('No accurate candidate for ' + instance['id'])
        score, circuit, source, error = max(choices, key=lambda item: item[0])
        circuits.append(circuit)
        selected.append(dict(id=instance['id'], source=source, gates=-score[1], depth=-score[2], projector_error=float(error), resource_score=score[0]))
    temporary = Path('solution.tmp.json')
    temporary.write_text(json.dumps(dict(version=1, circuits=circuits), separators=(',', ':'), allow_nan=False) + '\n')
    temporary.replace('solution.json')
    report = evaluate(Path('.'))
    Path('report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    Path('selected.json').write_text(json.dumps(selected, indent=2, allow_nan=False) + '\n')
    print(time.ctime(), report['core_score'], report['worst_family_score'], report['resource_score'], selected, flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--duration', type=float, default=0)
    arguments = parser.parse_args()
    started = time.monotonic()
    while True:
        report = collect()
        if report['passed'] or time.monotonic() - started >= arguments.duration:
            break
        time.sleep(15)
