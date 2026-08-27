import argparse
import copy
import json
import resource
import time
from pathlib import Path
import numpy as np
from scipy.integrate import DOP853, quad
from scipy.linalg import eigh
from driver import summarize
from experiment import write_csv
from transport.model import load_suite, extend, matrices, encode
from transport.protocols import drive_entries, perturbation
from transport.observables import measure
from transport.reservoirs import fermi
from transport.simulate import simulate, CONFIGS
from legacy_transport.simulate import simulate as legacy_simulate, CONFIGS as LEGACY_CONFIGS


def finite_reference(case, cells, bound_energies):
    started = time.perf_counter()
    hamiltonian, interfaces, ends = extend(case, cells)
    eigenvalues, eigenvectors = eigh(hamiltonian.toarray(), check_finite=False)
    lead = case['leads'][0]
    weights = fermi(eigenvalues, lead['mu'], lead['temperature'])
    for bound_energy in bound_energies:
        index = int(np.argmin(abs(eigenvalues - bound_energy)))
        weights[index] = fermi(eigenvalues[index], case['bound_mu'], case['bound_temperature'])
    selected = weights > 1e-14
    initial = eigenvectors[:, selected] * np.sqrt(weights[selected])
    shape = initial.shape
    entries = drive_entries(case, interfaces)

    def rhs(clock, state):
        dynamic = hamiltonian + perturbation(clock, entries, hamiltonian.shape[0])
        return (-1j * (dynamic @ state.reshape(shape))).ravel()

    density, current = [], []

    def observe(clock, state):
        dynamic = hamiltonian + perturbation(clock, entries, hamiltonian.shape[0])
        densities, currents = measure(case, dynamic, state.reshape(shape))
        density.append(densities)
        current.append(currents)

    observe(0., initial)
    solver = DOP853(rhs, 0., initial.ravel(), case['times'][-1], rtol=2e-11, atol=2e-13, max_step=.3)
    index = 1
    while solver.status == 'running':
        solver.step()
        if solver.status == 'failed':
            raise RuntimeError('finite reference propagation failed')
        if index < len(case['times']) and case['times'][index] <= solver.t + 1e-12:
            interpolation = solver.dense_output()
            while index < len(case['times']) and case['times'][index] <= solver.t + 1e-12:
                clock = case['times'][index]
                observe(clock, interpolation(min(clock, solver.t)))
                index += 1
    return dict(times=np.asarray(case['times']), density=np.asarray(density), current=np.asarray(current)), dict(
        config=dict(method='finite_coupled_spectrum_direct_schrodinger', cells=cells,
                    bound_occupation_override=True, rtol=2e-11, atol=2e-13),
        seconds=time.perf_counter() - started,
        peak_rss_mb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)


def main(input_directory, output_directory):
    output = Path(output_directory).resolve()
    directory = output / 'runs' / 'qualification'
    directory.mkdir(parents=True, exist_ok=True)
    cases = load_suite(Path(input_directory) / 'development.json')
    controls = load_suite(Path(input_directory) / 'controls.json')
    records = []
    requested_cases = []

    def retain(case, configuration, result, metadata, reference=None):
        target = directory / configuration
        target.mkdir(exist_ok=True)
        np.savez_compressed(target / (case['id'] + '.npz'), **result)
        (target / (case['id'] + '.json')).write_text(json.dumps(metadata, indent=2))
        row = summarize(case, result, metadata, configuration)
        row['density_error'] = float(np.max(abs(result['density'] - reference['density']))) if reference is not None else 0.
        row['current_error'] = float(np.max(abs(result['current'] - reference['current']))) if reference is not None and result['current'].size else 0.
        row['spectral_sum_rule_error'] = metadata.get('spectral_sum_rule_error', 0.)
        row['landauer_current_error'] = metadata.get('landauer_current_error', 0.)
        row['late_current_peak'] = metadata.get('late_current_peak', 0.)
        records.append(row)
        requested_cases.append(dict(case=case, configuration=configuration, config=metadata['config']))
        write_csv(output / 'qualification.csv', records)
        print(json.dumps(row), flush=True)

    stationary = controls[0]
    for name, changes in [('legacy_half_step', dict(step=.04)), ('legacy_no_absorber', dict(absorption=0.))]:
        LEGACY_CONFIGS[name] = dict(LEGACY_CONFIGS['production'], **changes)
        result, metadata = legacy_simulate(stationary, name)
        baseline = np.load(output / 'runs' / 'baseline' / 'controls' / (stationary['id'] + '.npz'))
        retain(stationary, name, result, metadata, baseline)

    for case_index, configuration, changes in [
            (0, 'energy_only', dict(quadrature_tolerance=2e-9, quadrature_output_order=16)),
            (2, 'boundary_only', dict(minimum_cells=112, maximum_cells=112)),
            (3, 'time_only', dict(rtol=3e-11, atol=3e-13, max_step=.25))]:
        case = cases[case_index]
        CONFIGS[configuration] = dict(CONFIGS['production'], **changes)
        result, metadata = simulate(case, configuration)
        reference = np.load(output / 'runs' / 'production' / (case['id'] + '.npz'))
        retain(case, configuration, result, metadata, reference)

    for case_index in [0, 1, 3, 4]:
        case = cases[case_index]
        metadata = json.loads((output / 'runs' / 'production' / (case['id'] + '.json')).read_text())
        reference = np.load(output / 'runs' / 'production' / (case['id'] + '.npz'))
        result, finite_metadata = finite_reference(case, 128, metadata['bound_energies'])
        retain(case, 'finite_reference', result, finite_metadata, reference)

    ring = copy.deepcopy(cases[2])
    ring['id'] = 'ring_stationary'
    ring['drives'] = []
    result, metadata = simulate(ring)
    central, leads = matrices(ring)

    def landauer(energy):
        surface = (energy - 1j * np.sqrt(max(0., 4 - energy ** 2))) / 2
        sigmas = [contact @ (surface * np.eye(len(cell))) @ contact.conj().T for cell, hop, contact in leads]
        gammas = [1j * (sigma - sigma.conj().T) for sigma in sigmas]
        green = np.linalg.inv(energy * np.eye(len(central)) - central - sum(sigmas))
        transmission = np.trace(gammas[0] @ green @ gammas[1] @ green.conj().T).real
        difference = fermi(energy, ring['leads'][0]['mu'], ring['leads'][0]['temperature']) - fermi(energy, ring['leads'][1]['mu'], ring['leads'][1]['temperature'])
        return transmission * difference / (2 * np.pi)

    landauer_current, quadrature_error = quad(landauer, -2, 2, epsabs=1e-11, limit=500)
    metadata['independent_landauer_current'] = landauer_current
    metadata['landauer_integral_error'] = quadrature_error
    metadata['outgoing_current_sum'] = float(np.sum(result['current'][0, :2]))
    metadata['landauer_current_error'] = abs(metadata['outgoing_current_sum'] - landauer_current)
    retain(ring, 'production', result, metadata)
    for configuration in ['ablation']:
        alternative, alternative_metadata = simulate(ring, configuration)
        retain(ring, configuration, alternative, alternative_metadata, result)

    side = copy.deepcopy(cases[1])
    side['id'] = 'sidebranch_empty_dark'
    side['bound_mu'] = 0.
    side['bound_temperature'] = 0.
    result, metadata = simulate(side)
    reference = np.load(output / 'runs' / 'production' / (cases[1]['id'] + '.npz'))
    retain(side, 'production', result, metadata, reference)

    side_long = copy.deepcopy(cases[1])
    side_long['id'] = 'sidebranch_late_control'
    side_long['times'] = np.linspace(0, 80, 161).tolist()
    result, metadata = simulate(side_long)
    metadata['late_current_peak'] = float(np.max(abs(result['current'][np.asarray(result['times']) >= 50, 1])))
    retain(side_long, 'production', result, metadata)

    stress = copy.deepcopy(cases[0])
    stress['id'] = 'fast_lead_long_horizon'
    stress['times'] = np.linspace(0, 80, 41).tolist()
    stress['hamiltonian'] = encode(np.array([[0., -3.5], [-3.5, .1]]))
    stress['current_bonds'] = [[1, 0]]
    stress['leads'] = [dict(cell=encode([[0.]]), hop=encode([[-3.5]]), contact=encode([[-3.5], [0.]]), mu=-6.7, temperature=0.),
                       dict(cell=encode([[0.]]), hop=encode([[-3.5]]), contact=encode([[0.], [-3.5]]), mu=.4, temperature=.07)]
    stress['bound_mu'] = -.4
    stress['drives'] = [dict(kind='add', profile='pulse', amplitude=1.7, duration=6., entries=[[0, 0, 1., 0.]]),
                        dict(kind='contact_phase', lead=0, profile='voltage_phase', amplitude=.7, duration=7.)]
    result, metadata = simulate(stress)
    retain(stress, 'production', result, metadata)
    CONFIGS['hard_wall_check'] = dict(CONFIGS['production'], maximum_cells=512)
    alternative, alternative_metadata = simulate(stress, 'hard_wall_check')
    retain(stress, 'hard_wall_check', alternative, alternative_metadata, result)

    random = np.random.default_rng(7423)
    matrix = np.diag(random.normal(0., .2, 12)).astype(complex)
    for index in range(11):
        matrix[index + 1, index] = -.8 + .1j
        matrix[index, index + 1] = -.8 - .1j
    reservoirs = []
    for lead_index in range(3):
        random_cell = random.normal(size=(4, 4)) + 1j * random.normal(size=(4, 4))
        cell = .07 * (random_cell + random_cell.conj().T)
        hop = -.9 * np.eye(4) + .025 * (random.normal(size=(4, 4)) + 1j * random.normal(size=(4, 4)))
        contact = np.zeros((12, 4), complex)
        unitary, triangular = np.linalg.qr(random.normal(size=(4, 4)) + 1j * random.normal(size=(4, 4)))
        contact[4 * lead_index:4 * lead_index + 4] = -.65 * unitary
        reservoirs.append(dict(cell=encode(cell), hop=encode(hop), contact=encode(contact),
                               mu=[-.3, .4, .1][lead_index], temperature=[0., .05, .12][lead_index]))
    multichannel = dict(id='three_four_channel_stress', family='generic_complex_multichannel',
                        hamiltonian=encode(matrix), leads=reservoirs, bound_mu=.05, bound_temperature=.07,
                        times=np.linspace(0, 40, 41).tolist(), current_bonds=[[4, 3], [8, 7]], drives=[
                            dict(kind='contact_phase', lead=0, amplitude=.3, duration=5., profile='voltage_phase'),
                            dict(kind='add', amplitude=.45, duration=6., profile='ac', omega=1.1,
                                 entries=[[4, 5, 0., 1.], [5, 5, 1., 0.]])])
    result, metadata = simulate(multichannel)
    retain(multichannel, 'production', result, metadata)
    alternative, alternative_metadata = simulate(multichannel, 'conservative')
    retain(multichannel, 'conservative', alternative, alternative_metadata, result)
    (directory / 'requests.json').write_text(json.dumps(requested_cases, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    arguments = parser.parse_args()
    main(arguments.input, arguments.output)
