import json
import sys
import numpy as np
from search import ROOT, NAMES, load_instances, evaluate
from validate import generate
from refine import Objective


def main(filename, label, count=120):
    artifact = json.loads((ROOT / filename).read_text())
    word = np.array([NAMES.index(stage['component']) for stage in artifact['stages'][:17]])
    values = np.array([stage['coefficient'] for stage in artifact['stages'][:17]])
    values[16] /= 2
    public = load_instances()
    synthetic = generate(count)
    for iteration in range(3):
        full_word = np.r_[word, word[-2::-1]]
        full_coeff = np.r_[values[:16], values[16] * 2, values[15::-1]]
        summary, ratios = evaluate(full_word, full_coeff, instances=synthetic, verbose=True)
        selected = []
        for family_index in range(8):
            family_ratios = ratios[family_index * count:(family_index + 1) * count]
            scores = family_ratios.max(axis=1)
            indices = np.argsort(scores)[-12:]
            selected.extend(public[family_index * 6:(family_index + 1) * 6])
            selected.extend(synthetic[family_index * count + int(index)] for index in indices)
        objective = Objective(selected)
        values = objective.optimize(word, values, seconds=180, penalty=-1, label=label)
    evaluate(np.r_[word, word[-2::-1]], np.r_[values[:16], values[16] * 2, values[15::-1]], instances=synthetic, verbose=True)
    evaluate(np.r_[word, word[-2::-1]], np.r_[values[:16], values[16] * 2, values[15::-1]], instances=public, verbose=True)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 120)
