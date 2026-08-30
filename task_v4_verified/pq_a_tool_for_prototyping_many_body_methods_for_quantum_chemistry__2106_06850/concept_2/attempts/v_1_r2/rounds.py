import argparse
import json
from pathlib import Path

import numpy as np

from optimize import Search


parser = argparse.ArgumentParser()
parser.add_argument('start')
parser.add_argument('--mode', default='low')
parser.add_argument('--name', default='rounds')
parser.add_argument('--radius', type=float, default=0.06)
args = parser.parse_args()
search = Search(args.mode)
search.prefix = args.name
search.radius = args.radius
search.objective_scale = 100
data = json.loads(Path(args.start).read_text())
vector = np.array(data['pair_matrix'])[search.rows, search.cols]
search.initial = np.array(data['amplitudes'])
try:
    search.callback(vector)
    for round_index in range(80):
        previous_best = search.best
        answer = search.run(vector, iterations=180)
        search.callback(answer.x)
        if Path(search.prefix + '.json').exists():
            data = json.loads(Path(search.prefix + '.json').read_text())
            vector = np.array(data['pair_matrix'])[search.rows, search.cols]
            search.initial = np.array(data['amplitudes'])
        search.last_x = None
        search.evaluate(vector)
        print('ROUND', round_index, 'BEST', search.best, 'RADIUS', search.radius, search.info, flush=True)
        if search.best < previous_best + 1e-12:
            search.radius *= 0.7
            if search.radius < 0.002:
                break
        elif answer.success:
            search.radius = min(0.15, search.radius * 1.1)
except StopIteration as success:
    print(str(success), flush=True)
