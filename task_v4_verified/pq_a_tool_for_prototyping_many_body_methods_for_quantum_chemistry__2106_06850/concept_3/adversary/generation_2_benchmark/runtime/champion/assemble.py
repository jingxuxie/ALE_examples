import json
from pathlib import Path
from explore import *


def from_reverse(case, data):
    labels = allowed_excitations(case.n_orbitals)
    remaining = data['mask']
    reference = case.reference_mask
    transitions = []
    for spin in range(2):
        removed = [orbital for orbital in range(spin, case.n_orbitals, 2) if reference & (1 << orbital) and not remaining & (1 << orbital)]
        added = [orbital for orbital in range(spin, case.n_orbitals, 2) if remaining & (1 << orbital) and not reference & (1 << orbital)]
        transitions.extend(zip(removed, added))
    gates = []
    for position in range(0, len(transitions), 2):
        selected = transitions[position:position+2]
        annihilate = tuple(sorted(source for source, destination in selected))
        create = tuple(sorted(destination for source, destination in selected))
        theta = math.pi/2
        if annihilate > create:
            annihilate, create = create, annihilate
            theta = -theta
        gates.append((Excitation(annihilate, create), theta))
    gates.extend((labels[label], -theta) for label, theta in reversed(data['reverse']))
    return gates


if __name__ == '__main__':
    circuits = []
    for case in load_cases():
        path = Path(case.case_id + '.reverse.json')
        if path.exists():
            gates = from_reverse(case, json.loads(path.read_text()))
        else:
            gates = []
        fidelity = squared_overlap(case.target, circuit_state(case, gates))
        print(case.case_id, len(gates), repr(fidelity), flush=True)
        circuits.append({'case_id': case.case_id, 'gates': [{'annihilate':list(label.annihilate), 'create':list(label.create), 'theta':theta} for label, theta in gates]})
    Path('submission.json').write_text(json.dumps({'schema_version':1, 'circuits':circuits}, indent=2, allow_nan=False)+'\n')
