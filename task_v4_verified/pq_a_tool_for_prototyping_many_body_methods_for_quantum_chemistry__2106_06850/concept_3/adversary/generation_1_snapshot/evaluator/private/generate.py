"""Private one-time authoring tool; never distribute its source or metadata."""

import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import sys

import numpy as np
from scipy.sparse import csr_matrix


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
from fermion import (
    Case, FIDELITY_THRESHOLD, allowed_excitations, apply_generator, apply_rotation,
    determinant_basis, reference_state, rotation_pairs,
)


def patch_files(files):
    patch = "*** Begin Patch\n"
    for relative, contents in files.items():
        destination = ROOT / relative
        if destination.exists():
            raise RuntimeError("refusing to overwrite frozen asset: " + relative)
        patch += "*** Add File: " + str(destination) + "\n"
        patch += "".join("+" + line + "\n" for line in contents.splitlines())
    patch += "*** End Patch\n"
    subprocess.run(["apply_patch"], input=patch, text=True, check=True)


def serialize(data):
    return json.dumps(data, indent=2, allow_nan=False) + "\n"


def make_case(n_orbitals, n_electrons, cap, singles_count, random):
    determinants = determinant_basis(n_orbitals, n_electrons)
    case = Case(
        "sector_%d_%d" % (n_orbitals, n_electrons), n_orbitals, n_electrons,
        n_electrons // 2, n_electrons // 2, (1 << n_electrons) - 1,
        cap, determinants, np.zeros(len(determinants)),
    )
    labels = allowed_excitations(n_orbitals)
    pairs_list = [rotation_pairs(n_orbitals, n_electrons, label) for label in labels]
    matrices = []
    for sources, destinations, signs in pairs_list:
        matrices.append(csr_matrix((np.concatenate((signs, -signs)), (
            np.concatenate((destinations, sources)), np.concatenate((sources, destinations)),
        )), shape=(len(determinants), len(determinants))))
    alpha_mask = sum(1 << orbital for orbital in range(0, n_orbitals, 2))
    sector_dimension = sum((mask & alpha_mask).bit_count() == case.n_alpha for mask in determinants)
    for trial in range(256):
        ranks = [1] * singles_count + [2] * (cap - singles_count)
        random.shuffle(ranks)
        state = reference_state(case)
        selected, angles, effects = [], [], []
        for rank in ranks:
            options = random.permutation(len(labels))
            winner = None
            for index in options:
                index = int(index)
                if len(labels[index].annihilate) != rank or index in selected:
                    continue
                derivative = apply_generator(state, pairs_list[index])
                if float(derivative @ derivative) < 0.04:
                    continue
                if selected:
                    commutator = matrices[selected[-1]] @ matrices[index] - matrices[index] @ matrices[selected[-1]]
                    if not commutator.count_nonzero():
                        continue
                winner = index
                break
            if winner is None:
                break
            theta = float(random.uniform(0.35, 1.15) * random.choice((-1, 1)))
            rotated = apply_rotation(state, pairs_list[winner], theta)
            effects.append(float(np.linalg.norm(rotated - state)))
            state = rotated
            selected.append(winner)
            angles.append(theta)
        if len(selected) != cap:
            continue
        support = int(np.count_nonzero(np.abs(state) > 1e-12))
        participation = float(1.0 / np.sum(state ** 4))
        covered = set().union(*(set(labels[index].annihilate + labels[index].create) for index in selected))
        if support < 0.85 * sector_dimension or participation < 6 or len(covered) != n_orbitals:
            continue
        gates = [{"annihilate": list(labels[index].annihilate), "create": list(labels[index].create),
                  "theta": theta} for index, theta in zip(selected, angles)]
        target = {"case_id": case.case_id, "n_orbitals": n_orbitals, "n_electrons": n_electrons,
                  "n_alpha": case.n_alpha, "n_beta": case.n_beta, "reference_mask": case.reference_mask,
                  "max_gates": cap, "determinants": list(determinants), "target_amplitudes": state.tolist()}
        diagnostics = {"case_id": case.case_id, "accepted_trial": trial, "candidate_count": len(labels),
                       "spin_sector_dimension": sector_dimension, "support_above_1e-12": support,
                       "participation_ratio": participation, "minimum_step_effect": min(effects),
                       "minimum_absolute_angle": min(abs(theta) for theta in angles),
                       "singles": singles_count, "doubles": cap - singles_count,
                       "noncommuting_adjacent_pairs": cap - 1, "distinct_gates": len(set(selected))}
        return target, {"case_id": case.case_id, "gates": gates}, diagnostics
    raise RuntimeError("bounded generation did not produce a sufficiently mixed case")


def main():
    if (ROOT / "participant" / "input" / "targets.json").exists():
        raise RuntimeError("targets already frozen; never regenerate after launch")
    seed = secrets.randbits(128)
    random = np.random.default_rng(seed)
    generated = [make_case(*specification, random) for specification in ((8, 4, 14, 4), (10, 4, 18, 5), (10, 6, 20, 6))]
    targets = serialize({"schema_version": 1, "fidelity_threshold": FIDELITY_THRESHOLD,
                         "cases": [entry[0] for entry in generated]})
    certificates = serialize({"schema_version": 1, "circuits": [entry[1] for entry in generated]})
    engine = (ROOT / "participant" / "workspace" / "fermion.py").read_text(encoding="utf-8")
    files = {"participant/input/targets.json": targets, "evaluator/private/targets.json": targets,
             "evaluator/private/certificates.json": certificates, "evaluator/private/engine.py": engine,
             "evaluator/private/generation.json": serialize({"private_seed": str(seed), "cases": [entry[2] for entry in generated]})}
    public_hashes = {str(path.relative_to(ROOT / "participant")): hashlib.sha256(path.read_bytes()).hexdigest()
                     for path in (ROOT / "participant").rglob("*") if path.is_file() and "__pycache__" not in path.parts}
    public_hashes["input/targets.json"] = hashlib.sha256(targets.encode()).hexdigest()
    files["evaluator/private/frozen_manifest.json"] = serialize({
        "frozen_date": "2026-08-28", "fidelity_threshold": FIDELITY_THRESHOLD, "gate_caps": [14, 18, 20],
        "participant_sha256": public_hashes,
        "private_sha256": {name: hashlib.sha256(files["evaluator/private/" + name].encode()).hexdigest()
                           for name in ("engine.py", "targets.json", "certificates.json")},
    })
    patch_files(files)
    print(serialize({"generated_cases": [entry[2] for entry in generated], "participant_frozen": True}))


if __name__ == "__main__":
    main()
