import sys
import time
from pathlib import Path

import numpy as np
import phono3py
from phonopy.harmonic.dynamical_matrix import get_dynamical_matrix
from phonopy.physical_units import get_physical_units

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT.parents[1]
sys.path.insert(0, str(ROOT / "private/reference"))
sys.path.insert(0, str(ROOT / "participant/workspace"))
from oracle import Oracle, runtime_versions
from solve import solve, single_origin, contract_modes

print(runtime_versions(), flush=True)
started = time.perf_counter()
crystal = phono3py.load(
    TARGET / "author/source/phono3py/test/phono3py_params_NaCl222.yaml.xz",
    is_nac=False, is_compact_fc=True, symmetrize_fc=True,
    fc_calculator="traditional", make_r0_average=True,
)
print("loaded", time.perf_counter() - started, crystal.fc3.shape, crystal.fc2.shape, flush=True)
primitive = crystal.primitive
vectors, multiplicities = primitive.get_smallest_vectors()
print("vectors", vectors.shape, multiplicities.shape, "maps", primitive.p2s_map, flush=True)
qpoints = np.array([[[.13, .21, -.17], [-.31, .11, .24], [.18, -.32, -.07]]])
dynamical_matrix = get_dynamical_matrix(crystal.fc2, crystal.phonon_supercell, crystal.phonon_primitive)
frequencies = []
eigenvectors = []
for triplet in qpoints:
    triplet_frequencies = []
    triplet_eigenvectors = []
    for wavevector in triplet:
        dynamical_matrix.run(wavevector)
        values, modes = np.linalg.eigh(dynamical_matrix.dynamical_matrix)
        triplet_frequencies.append(np.sign(values) * np.sqrt(np.abs(values)) * get_physical_units().DefaultToTHz)
        triplet_eigenvectors.append(modes)
    frequencies.append(triplet_frequencies)
    eigenvectors.append(triplet_eigenvectors)
data = dict(fc3=crystal.fc3, p2s_map=primitive.p2s_map, s2p_map=primitive.s2p_map,
            shortest_vectors=vectors, multiplicities=multiplicities, primitive_positions=primitive.scaled_positions,
            masses=primitive.masses, qpoints=qpoints, frequencies=np.array(frequencies),
            eigenvectors=np.array(eigenvectors), cutoff_frequency=np.array(.01))
oracle = Oracle()
on = oracle.solve(data)
off = oracle.solve(data, average=False)
weak = solve(data)
averaged = (single_origin(data, qpoints[0]) +
            single_origin(data, qpoints[0][[1, 0, 2]]).transpose(1, 0, 2, 4, 3, 5) +
            single_origin(data, qpoints[0][[2, 1, 0]]).transpose(2, 1, 0, 5, 4, 3)) / 3
for key in on:
    print(key, "on norm", np.linalg.norm(on[key]), "off-on relative", np.linalg.norm(off[key]-on[key])/np.linalg.norm(on[key]),
          "baseline-off relative", np.linalg.norm(weak[key]-off[key])/np.linalg.norm(off[key]), flush=True)
print("literal average relative", np.linalg.norm(averaged-on["reciprocal_fc3"][0])/np.linalg.norm(averaged), flush=True)
crystal.mesh_numbers = [5, 5, 5]
crystal.init_phph_interaction()
interaction = crystal.phph_interaction
print("API flag", interaction.make_r0_average, "shortest count", interaction.all_shortest.sum(), flush=True)
optimized = oracle.solve(data, all_shortest=interaction.all_shortest)
print("optimized relative", np.linalg.norm(optimized["reciprocal_fc3"]-on["reciprocal_fc3"])/np.linalg.norm(on["reciprocal_fc3"]), flush=True)
interaction.set_grid_point(1)
interaction.run_phonon_solver()
interaction.run()
print("interaction shape", interaction.interaction_strength.shape, "time", time.perf_counter()-started, flush=True)
