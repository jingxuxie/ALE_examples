import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import sys
import json
from pathlib import Path
import numpy as np
from optimize import unpack, pack, full_hamiltonian, WEIGHTS, BOUNDS
from model import components

def fourier(coefficients, core=False):
    axis = 2*np.pi*np.arange(9)/9
    horizontal, vertical = np.meshgrid(axis, axis, indexing='ij')
    matrices = full_hamiltonian(unpack(coefficients), horizontal, vertical)
    if core:
        matrices[..., :2, 2:] = 0
        matrices[..., 2:, :2] = 0
    transformed = np.fft.fftn(matrices, axes=(0, 1))/81
    modes = []
    for horizontal in range(-3, 4):
        for vertical in range(-3, 4):
            modes.append((horizontal, vertical, transformed[horizontal%9, vertical%9]))
    return modes

def derivative_bounds(modes):
    norms = np.array([np.linalg.norm(value, 2)*(1+1e-12)+1e-14 for _, _, value in modes])
    orders = np.array([[horizontal, vertical] for horizontal, vertical, _ in modes])
    linear = np.abs(orders).T @ norms
    quadratic = (orders**2).T @ norms
    return linear, quadratic, norms.sum()

def chern(vectors):
    link_x = np.sum(vectors.conj()*np.roll(vectors, -1, axis=0), axis=-1)
    link_y = np.sum(vectors.conj()*np.roll(vectors, -1, axis=1), axis=-1)
    min_link = min(np.min(np.abs(link_x)), np.min(np.abs(link_y)))
    link_x /= np.abs(link_x)
    link_y /= np.abs(link_y)
    phases = np.angle(link_x*np.roll(link_y, -1, axis=0)*np.roll(link_x, -1, axis=1).conj()*link_y.conj())
    return float(np.sum(phases)/(2*np.pi)), float(min_link), float(np.max(np.abs(phases)))

def certificate(coefficients, mesh=320, topology=True):
    modes = fourier(coefficients)
    linear, quadratic, totalnorm = derivative_bounds(modes)
    padding = 2e-10*(1+totalnorm)
    linear += .06
    quadratic += .06
    steps = np.array([2*np.pi/mesh, 2*np.pi/mesh, .025, .03])
    first = np.r_[linear, 1., np.sqrt(2)]
    second = np.r_[quadratic, 0., 0.]
    axis = np.linspace(-np.pi, np.pi, mesh, endpoint=False)
    horizontal, vertical = np.meshgrid(axis, axis, indexing='ij')
    nominal = full_hamiltonian(unpack(coefficients), horizontal, vertical)
    width = 0.
    gap01 = gap12 = indirect = float('inf')
    worst = None
    for mass in np.linspace(-.05, .05, 5):
        for anisotropy in np.linspace(-.06, .06, 5):
            current = nominal.copy()
            current[..., 0, 0] += mass
            current[..., 1, 1] -= mass
            current[..., 0, 1] += anisotropy*(np.sin(horizontal)+1j*np.sin(vertical))
            current[..., 1, 0] = current[..., 0, 1].conj()
            spectrum = np.linalg.eigvalsh(current)
            this_width = np.ptp(spectrum[..., 0])
            if this_width > width:
                width = float(this_width)
                worst = [float(mass), float(anisotropy)]
            gap01 = min(gap01, float(np.min(spectrum[..., 1]-spectrum[..., 0])))
            gap12 = min(gap12, float(np.min(spectrum[..., 2]-spectrum[..., 1])))
            indirect = min(indirect, float(np.min(spectrum[..., 1])-np.max(spectrum[..., 0])))
    lower01 = gap01 - first@steps - 2*padding
    lower12 = gap12 - first@steps - 2*padding
    eta = .004*WEIGHTS@np.abs(coefficients)
    epsilon0 = np.dot(second+2*first**2/lower01, steps**2)/8
    epsilon1 = np.dot(second+2*first**2/min(lower01, lower12), steps**2)/8
    width_cert = width + 2*(epsilon0+eta+padding)
    direct_cert = gap01 - epsilon0-epsilon1-2*eta-2*padding
    indirect_cert = indirect-epsilon0-epsilon1-2*eta-2*padding
    result = dict(channels=int(np.count_nonzero(coefficients[1:])), bounds_valid=bool(np.all(coefficients>=BOUNDS[:, 0]) and np.all(coefficients<=BOUNDS[:, 1])), sampled_width=width, sampled_direct=gap01, sampled_indirect=indirect, sampled_gap12=gap12, worst_error=worst, linear=first.tolist(), quadratic=second.tolist(), a=float(lower01), b=float(lower12), eta=float(eta), epsilon0=float(epsilon0), epsilon1=float(epsilon1), width_cert=float(width_cert), direct_cert=float(direct_cert), indirect_cert=float(indirect_cert), spectral_score=float(max(0, min(1, .175/width_cert, direct_cert/3, indirect_cert/3))))
    if topology:
        core_modes = fourier(coefficients, True)
        core_linear, _, _ = derivative_bounds(core_modes)
        full_linear, _, _ = derivative_bounds(modes)
        hybrid_bound = sum(np.linalg.norm(full[2]-core[2], 2)*(1+1e-12)+1e-14 for full, core in zip(modes, core_modes))
        axis = np.linspace(-np.pi, np.pi, 128, endpoint=False)
        horizontal, vertical = np.meshgrid(axis, axis, indexing='ij')
        full = full_hamiltonian(unpack(coefficients), horizontal, vertical)
        core = full.copy()
        core[..., :2, 2:] = 0
        core[..., 2:, :2] = 0
        spectrum_core, vectors_core = np.linalg.eigh(core[..., :2, :2])
        spectrum_full, vectors_full = np.linalg.eigh(full)
        result['core_chern'] = chern(vectors_core[..., :, 0])
        result['full_chern'] = chern(vectors_full[..., :, 0])
        sphere = components(unpack(coefficients), horizontal, vertical)[..., 1:]
        sphere /= np.linalg.norm(sphere, axis=-1, keepdims=True)
        right = np.roll(sphere, -1, axis=0)
        upper = np.roll(sphere, -1, axis=1)
        diagonal = np.roll(right, -1, axis=1)
        area = 0.
        for middle, last in [(right, diagonal), (diagonal, upper)]:
            numerator = np.sum(sphere*np.cross(middle, last), axis=-1)
            denominator = 1+np.sum(sphere*middle, axis=-1)+np.sum(middle*last, axis=-1)+np.sum(last*sphere, axis=-1)
            area += np.sum(2*np.arctan2(numerator, denominator))
        result['core_spherical_degree'] = float(area/(4*np.pi))
        shifted = full_hamiltonian(unpack(coefficients), horizontal+.37*2*np.pi/128, vertical+.23*2*np.pi/128)
        _, shifted_vectors = np.linalg.eigh(shifted)
        phases = np.exp(1j*np.random.default_rng(50421).uniform(-np.pi, np.pi, size=(128, 128)))
        result['shifted_phased_chern'] = chern(shifted_vectors[..., :, 0]*phases[..., None])
        result['core_remote_clearance'] = float(5.5-np.max(spectrum_core[..., 1])-np.sum(core_linear)*np.pi/128)
        result['core_nonzero_margin'] = float(np.min((spectrum_core[..., 1]-spectrum_core[..., 0])/2)-np.sum(core_linear)*np.pi/128)
        homotopy_gap = np.inf
        for coupling in np.linspace(0, 1, 9):
            spectrum = np.linalg.eigvalsh(core+coupling*(full-core))
            homotopy_gap = min(homotopy_gap, np.min(spectrum[..., 1]-spectrum[..., 0]))
        homotopy_margin = 2*(np.maximum(core_linear, full_linear).sum()*np.pi/128+hybrid_bound/16)+1e-9
        result['homotopy_gap_bound'] = float(homotopy_gap-homotopy_margin)
        result['topology_pass'] = bool(
            all(abs(result[key][0]+1)<2e-8 and result[key][1]>1e-8 and result[key][2]<np.pi/2 for key in ['core_chern', 'full_chern', 'shifted_phased_chern'])
            and abs(result['core_spherical_degree']-1)<2e-8
            and min(result['core_remote_clearance'], result['core_nonzero_margin'], result['homotopy_gap_bound'])>0
        )
    result['spectral_pass'] = bool(lower01>0 and lower12-2*eta>0 and width_cert<=.175 and direct_cert>=3 and indirect_cert>=3)
    return result

def read_checked(path):
    content = Path(path).read_bytes()
    if len(content)>32768:
        raise ValueError('Witness exceeds size limit')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate key')
            result[key] = value
        return result
    witness = json.loads(content, object_pairs_hook=unique)
    if set(witness) != {'schema_version', 'mass', 'spin_orbit', 'orbital_mass', 'scalar'}:
        raise ValueError('Incorrect keys')
    if type(witness['schema_version']) is not int or witness['schema_version'] != 1:
        raise ValueError('Incorrect schema version')
    for key, length in [('spin_orbit', 11), ('orbital_mass', 9), ('scalar', 9)]:
        if type(witness[key]) is not list or len(witness[key]) != length:
            raise ValueError('Incorrect coefficient array')
    values = [witness['mass']]+witness['spin_orbit']+witness['orbital_mass']+witness['scalar']
    if not all(type(value) in (int, float) and np.isfinite(value) for value in values):
        raise ValueError('Invalid coefficient type or value')
    coefficients = np.asarray(values)
    if np.count_nonzero(coefficients[1:])>8 or np.any(coefficients<BOUNDS[:, 0]) or np.any(coefficients>BOUNDS[:, 1]):
        raise ValueError('Coefficient bounds or channel budget exceeded')
    return coefficients

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('witness')
    parser.add_argument('--mesh', type=int, default=320)
    parser.add_argument('--no-topology', action='store_true')
    parser.add_argument('--output')
    args = parser.parse_args()
    coefficients = read_checked(args.witness)
    result = certificate(coefficients, args.mesh, not args.no_topology)
    content = json.dumps(result, indent=2)+'\n'
    print(content, flush=True)
    if args.output:
        Path(args.output).write_text(content)
