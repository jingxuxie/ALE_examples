from explore import *
from pathlib import Path

for case in load_cases():
    alpha_mask = sum(1 << orbital for orbital in range(0, case.n_orbitals, 2))
    keep = [index for index, mask in enumerate(case.determinants) if (mask & alpha_mask).bit_count() == case.n_alpha]
    positions = {old: new for new, old in enumerate(keep)}
    labels = allowed_excitations(case.n_orbitals)
    rows = [f'{len(keep)} {len(labels)} {case.max_gates} {positions[case.determinants.index(case.reference_mask)]}', ' '.join(map(repr, case.target[keep].tolist())), ' '.join(str(case.determinants[index]) for index in keep)]
    for label in labels:
        sources, destinations, signs = rotation_pairs(case.n_orbitals, case.n_electrons, label)
        pairs = [(positions[source], positions[destination], int(sign)) for source, destination, sign in zip(sources, destinations, signs) if source in positions]
        rows.append(' '.join(map(str, [len(label.annihilate), *label.annihilate, *label.create, len(pairs), *(value for pair in pairs for value in pair)])))
    Path(case.case_id + '.dat').write_text('\n'.join(rows) + '\n')
