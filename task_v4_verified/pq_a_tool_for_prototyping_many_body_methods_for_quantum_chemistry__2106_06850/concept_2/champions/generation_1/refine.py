import argparse
import json
from pathlib import Path

import numpy as np

from optimize import Search


class Refine(Search):
    def evaluate(self, vector):
        objective, derivative, margins, derivatives = super().evaluate(vector)
        margins = margins.copy()
        margins[:2] -= 100 * (0.000095 - 0.00002)
        margins[2] -= 100 * (0.9995 - 0.99905)
        margins[3] -= 0.51 - 0.455
        margins[4] -= 0.2 - 0.105
        margins[5:7] -= 0.15 - 0.055
        margins[7] -= (95 - 45) / 20
        margins[8] -= 1.48 - 1.2
        margins[9] -= 1.24 - 1.1
        margins[10] -= 0.12 - 0.055
        margins = np.append(margins, -objective - 0.05)
        derivatives = np.vstack((derivatives, -derivative))
        difference = vector - self.origin
        return difference @ difference, 2 * difference, margins, derivatives


parser = argparse.ArgumentParser()
parser.add_argument('start')
parser.add_argument('--name', default='refined')
args = parser.parse_args()
search = Refine('high')
search.prefix = args.name
search.radius = 0.15
search.objective_scale = 1
data = json.loads(Path(args.start).read_text())
vector = np.array(data['pair_matrix'])[search.rows, search.cols]
search.origin = vector.copy()
search.initial = np.array(data['amplitudes'])
try:
    answer = search.run(vector, iterations=300)
    search.callback(answer.x)
    print(answer.message, search.info)
except StopIteration as success:
    print(str(success), flush=True)
