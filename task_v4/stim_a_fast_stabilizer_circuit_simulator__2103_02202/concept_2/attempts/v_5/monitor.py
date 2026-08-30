import json
import time
from datetime import datetime, timezone
from pathlib import Path
from select_best import inspect


def main():
    deadline = datetime(2026, 8, 28, 17, 54, 5, tzinfo=timezone.utc).timestamp()
    current = inspect(Path('witness.json'))
    best_score = current[0] if current else 0
    modified = {}
    while time.time() < deadline:
        for path in Path('.').glob('*.json'):
            try:
                timestamp = path.stat().st_mtime_ns
            except OSError:
                continue
            if modified.get(path) == timestamp:
                continue
            result = inspect(path)
            if result is None:
                continue
            modified[path] = timestamp
            if result[0] <= best_score:
                continue
            best_score = result[0]
            temporary = Path('watcher.pending')
            temporary.write_text(json.dumps({'faults': result[-1]}, separators=(',', ':')) + '\n')
            temporary.replace('witness.json')
            print(datetime.now(timezone.utc).isoformat(), path.name, result[:5], flush=True)
            if result[4]:
                return
        time.sleep(2)
    print('Monitor finished', inspect(Path('witness.json'))[:5], flush=True)


if __name__ == '__main__':
    main()
