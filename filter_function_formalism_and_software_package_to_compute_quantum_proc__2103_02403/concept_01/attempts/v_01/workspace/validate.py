import importlib.util
import json
import sys
import time
import traceback
from pathlib import Path


def main():
    results = []
    for source in sorted((Path(__file__).parent / 'tests').glob('test*.py')):
        specification = importlib.util.spec_from_file_location(source.stem, source)
        module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(module)
        for name in sorted(vars(module)):
            if not name.startswith('test_'):
                continue
            started = time.perf_counter()
            try:
                getattr(module, name)()
                result = dict(test=name, source=str(source.relative_to(Path(__file__).parent)),
                              passed=True, seconds=time.perf_counter() - started)
            except Exception:
                result = dict(test=name, source=str(source.relative_to(Path(__file__).parent)),
                              passed=False, seconds=time.perf_counter() - started,
                              error=traceback.format_exc())
            results.append(result)
            print(json.dumps(result), flush=True)
    destination = Path(sys.argv[1])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(results, indent=2) + '\n')
    if not all(result['passed'] for result in results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
