import csv
import json
from pathlib import Path
import resource
import sys
import time
from engine import Evolution
from numerics import policy


def solve(case_path, output_path, profile='production'):
    started = time.perf_counter()
    case = json.loads(Path(case_path).read_text())
    output = Path(output_path)
    output.mkdir(parents=True, exist_ok=True)
    settings = policy(case, profile)
    engine = Evolution(case, output, settings)
    ground_energy = engine.prepare()
    rows = []
    previous = 0
    for instant in case['times']:
        if instant > previous:
            engine.advance(instant - previous)
        rows.append(engine.measure(instant))
        previous = instant
    with (output / 'trajectory.csv').open('w') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    stats = {'case': case['id'], 'profile': profile, 'initial_energy': ground_energy,
             'seconds': time.perf_counter() - started, 'peak_rss_mb': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
             'settings': settings, 'order': engine.order}
    (output / 'stats.json').write_text(json.dumps(stats, indent=2))
    engine.close()
    return stats


if __name__ == '__main__':
    print(json.dumps(solve(*sys.argv[1:])))
