import json
import random
import sys
from pathlib import Path

import synthesis as syn
import ppr_optimize as ppr
import peephole3 as peep

def main():
    iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    sources = []
    for path in Path('candidates').glob('*_metrics.json'):
        metrics = json.loads(path.read_text())
        source = path.with_name(path.name.replace('_metrics', ''))
        sources.append((metrics['score'], source))
    sources.sort(reverse=True)
    triples = []
    for center, neighbors in enumerate(syn.NEIGHBORS):
        for first_index, first in enumerate(neighbors):
            for second in neighbors[first_index + 1:]:
                triples.append((first, center, second))
    rng = random.Random(9567)
    for score, source in sources:
        record = source.with_name(source.stem + '_optimized_metrics.json')
        if record.exists():
            continue
        gates = [tuple(operation) for operation in json.loads(source.read_text())]
        best = None
        for iteration in range(iterations):
            rotations, frames = ppr.extract(gates)
            rotations = ppr.cancel(rotations)
            rotations = ppr.conjugate_reduce(rotations)
            rotations = ppr.reorder(rotations, iteration)
            gates = syn.simplify(ppr.native(rotations, frames))
            rng.shuffle(triples)
            for qubits in triples:
                gates = peep.reduce_block(gates, qubits)
            result = syn.save(gates[:], f'bulk:{source}:{iteration}')
            if best is None or result['score'] > best['score']:
                best = result
                source.with_name(source.stem + '_optimized.json').write_text(json.dumps(gates) + '\n')
        record.write_text(json.dumps(best) + '\n')

if __name__ == '__main__':
    main()
