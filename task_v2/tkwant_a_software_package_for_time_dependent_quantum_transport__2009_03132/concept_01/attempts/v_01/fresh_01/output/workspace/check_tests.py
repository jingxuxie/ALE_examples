import json
import runpy
import time
import traceback
from pathlib import Path


def main():
    records = []
    for path in sorted((Path(__file__).parent / 'tests').glob('test_*.py')):
        for name, function in runpy.run_path(str(path)).items():
            if not name.startswith('test_'):
                continue
            started = time.perf_counter()
            try:
                function()
                record = dict(test=name, passed=True)
            except Exception:
                record = dict(test=name, passed=False, traceback=traceback.format_exc())
            record['seconds'] = time.perf_counter() - started
            records.append(record)
            print(json.dumps(record), flush=True)
    return all(record['passed'] for record in records)


if __name__ == '__main__':
    raise SystemExit(0 if main() else 1)
