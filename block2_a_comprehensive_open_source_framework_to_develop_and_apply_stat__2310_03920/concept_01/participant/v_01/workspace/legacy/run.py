import csv
import json
from pathlib import Path
import resource
import sys
import time
from simulate import simulate


def main():
    case_path, output_path = sys.argv[1:3]
    profile = sys.argv[3] if len(sys.argv) > 3 else 'production'
    output = Path(output_path)
    output.mkdir(parents=True, exist_ok=True)
    settings = json.loads(Path(__file__).with_name('schedules.json').read_text())[profile]
    case = json.loads(Path(case_path).read_text())
    started = time.perf_counter()
    energy, rows = simulate(case, settings, output / 'scratch')
    with (output / 'trajectory.csv').open('w') as handle:
        writer = csv.DictWriter(handle, fieldnames=['time', 'norm', 'charge', 'number', 'spin', 'phonon', 'current', 'source', 'energy'])
        writer.writeheader()
        writer.writerows(rows)
    stats = {'initial_energy': energy, 'seconds': time.perf_counter() - started,
             'peak_rss_mb': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
             'settings': settings, 'profile': profile, 'case': case['id']}
    (output / 'stats.json').write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats))


if __name__ == '__main__':
    main()
