import json
from pathlib import Path

from search import evaluate


def main():
    paths = [Path('counterexample.json')]
    for prefix in ['robust', 'mutate', 'structured', 'condition', 'target', 'optimal', 'highenergy', 'ulp', 'batch', 'physical', 'surrogate', 'coordinate']:
        paths.extend(Path('.').glob(prefix + '-*.json'))
    best = None
    for path in paths:
        try:
            data = json.loads(path.read_text())
            Path('counterexample.json').write_text(json.dumps(data) + '\n')
            result = evaluate(Path.cwd())
            minimum = result.get('minimum_rms_error', 0)
            print(path, result.get('admissible'), minimum, flush=True)
            if result.get('admissible') and (best is None or minimum > best[0]):
                best = (minimum, data, result, str(path))
        except (OSError, ValueError) as error:
            print('SKIP', path, error, flush=True)
    if best is not None:
        Path('counterexample.json').write_text(json.dumps(best[1]) + '\n')
        Path('report.json').write_text(json.dumps(best[2], indent=2) + '\n')
        print('SELECTED', best[3], best[0], flush=True)


if __name__ == '__main__':
    main()
