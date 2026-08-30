import argparse
import json
import time
from pathlib import Path

from solve import fingerprint, validate


def main():
    parser = argparse.ArgumentParser(description='Replay a privileged case-specific contraction certificate, not a universal participant solver.')
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--portfolio', type=Path, default=Path(__file__).resolve().parent / 'best')
    args = parser.parse_args()
    started = time.monotonic()
    case = json.loads(args.input.read_text())
    digest = fingerprint(case)
    summary = json.loads((args.portfolio / 'summary.json').read_text())
    matches = [record for record in summary['cases'] if record['case_sha256'] == digest]
    if not matches:
        raise ValueError('no privileged certificate for this exact input; run solve.py for fresh optimization')
    name = Path(matches[0]['file']).stem
    plan = json.loads((args.portfolio / (name + '.plan.json')).read_text())
    result = validate(case, plan)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan))
    print(json.dumps({'classification': 'privileged exact-input certificate replay', 'result': result,
                      'case_sha256': digest, 'wall_seconds': time.monotonic() - started}))


if __name__ == '__main__':
    main()
