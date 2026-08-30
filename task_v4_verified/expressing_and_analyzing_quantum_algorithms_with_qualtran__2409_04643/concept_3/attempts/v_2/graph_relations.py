from analyze import SUITE, np
from relations import columns, truth_bits, nullspace
from itertools import combinations

for inst in SUITE:
    width = inst['n']
    table = np.array(inst['table'])
    inputs = columns(width)
    values = [inputs[1 << bit] for bit in range(width)] + [truth_bits((table >> bit) & 1) for bit in range(inst['m'])]
    monomials = [()]
    vectors = [inputs[0]]
    print(inst['id'], flush=True)
    for degree in (1, 2, 3):
        for combo in combinations(range(len(values)), degree):
            vector = inputs[0]
            for index in combo:
                vector &= values[index]
            vectors.append(vector)
            monomials.append(combo)
        relations = nullspace(vectors)
        print(degree, len(vectors), len(relations), flush=True)
        if relations:
            print([[monomials[index] for index in range(len(monomials)) if relation >> index & 1] for relation in relations[:2]], flush=True)
