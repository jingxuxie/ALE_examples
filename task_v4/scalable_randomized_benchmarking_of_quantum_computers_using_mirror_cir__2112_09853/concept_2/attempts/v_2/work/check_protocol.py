import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[1] / 'participant' / 'workspace'))
from model import Episode, FAMILIES, SHAPES
from transport import launch_command, run_episode, aggregate

parser = argparse.ArgumentParser()
parser.add_argument('--isolation', default='audit')
parser.add_argument('--family', default='all')
parser.add_argument('--shape', default='all')
parser.add_argument('--seed', type=int, default=2026)
arguments = parser.parse_args()
records = []
for family in FAMILIES:
    if arguments.family not in ('all', family):
        continue
    for shape in SHAPES:
        if arguments.shape not in ('all', 'x'.join(map(str, shape))):
            continue
        seed = arguments.seed + 1009 * FAMILIES.index(family) + 53 * SHAPES.index(shape)
        episode = Episode(seed, family, shape)
        isolation = 'bwrap' if arguments.isolation == 'filesystem' else arguments.isolation
        command = launch_command(ROOT / 'submission', 'policy.py', isolation)
        if arguments.isolation == 'filesystem':
            command.insert(command.index('--unshare-all') + 1, '--share-net')
        stderr_path = ROOT / 'work' / f'protocol_{arguments.isolation}_{family}_{shape[0]}x{shape[1]}.stderr'
        record = run_episode(episode, command, ROOT / 'submission', stderr_path)
        record.update(family=family, qubits=episode.grid.qubits, public_seed=seed)
        records.append(record)
        print(json.dumps(record), flush=True)
report = aggregate(records, isolated=arguments.isolation == 'bwrap')
(ROOT / 'work' / f'protocol_{arguments.isolation}_report.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report), flush=True)
