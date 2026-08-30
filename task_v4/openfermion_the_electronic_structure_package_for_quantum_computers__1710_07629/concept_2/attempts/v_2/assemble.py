import json
from pathlib import Path
import sys

from synthesize import PARTICIPANT, load_instances

sys.path.insert(0, str(PARTICIPANT / 'workspace'))
from simulator import circuit_metrics, evaluate
sys.path.insert(0, str(PARTICIPANT / 'baseline'))
from compile import compile_instance


def main():
    circuits = []
    for instance in load_instances():
        candidates = []
        for path in Path('.').glob(instance['id'] + '*.json'):
            try:
                circuit = json.loads(path.read_text())
                if type(circuit) is not dict or set(circuit) != {'id', 'layers'}:
                    continue
                metrics = circuit_metrics(instance, circuit)
                if metrics['accurate']:
                    candidates.append((metrics['certified'], metrics['resource_score'], -metrics['gates'], -metrics['depth'], path.name, circuit, metrics))
            except Exception:
                continue
        if candidates:
            best = max(candidates, key=lambda entry: entry[:4])
            circuit = best[5]
            print('SELECT', best[4], best[6], flush=True)
        else:
            circuit, diagnostic = compile_instance(instance)
            print('BASELINE', diagnostic, flush=True)
        circuits.append(circuit)
    Path('solution.json').write_text(json.dumps(dict(version=1, circuits=circuits), indent=2, allow_nan=False) + '\n')
    report = evaluate('.')
    Path('report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
