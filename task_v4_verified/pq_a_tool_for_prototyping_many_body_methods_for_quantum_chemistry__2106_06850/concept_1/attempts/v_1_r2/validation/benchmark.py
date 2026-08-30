import json
import math
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
PARTICIPANT = ROOT.parents[1] / 'participant'
REPORTS = ROOT / 'validation' / 'reports'
ARTIFACTS = ROOT / 'validation' / 'artifacts'
REPORTS.mkdir(parents=True, exist_ok=True)
ARTIFACTS.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(PARTICIPANT / 'workspace'))
from solve import solve
from contract import validate


def main():
    results = []
    for path in sorted((PARTICIPANT / 'input').glob('*.json')):
        if 'baseline' in path.name:
            continue
        case = json.loads(path.read_text())
        started = time.monotonic()
        plan = solve(case)
        elapsed = time.monotonic() - started
        result = validate(case, plan)
        baseline = json.loads(path.with_suffix('.baseline.json').read_text())['flops']
        result.update(family=path.stem, speedup=baseline / result['flops'], seconds=elapsed)
        print(json.dumps(result), flush=True)
        results.append(result)
        (ARTIFACTS / (path.stem + '.plan.json')).write_text(json.dumps(plan))
    print('Geometric mean:', math.exp(sum(math.log(result['speedup']) for result in results) / len(results)))
    (REPORTS / 'sample_results.json').write_text(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
