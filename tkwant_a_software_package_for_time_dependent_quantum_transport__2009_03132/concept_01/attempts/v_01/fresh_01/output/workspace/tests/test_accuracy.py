import copy
import numpy as np
from scipy.integrate import solve_ivp
from scipy.linalg import eigh
from scipy import sparse
from scipy.sparse.linalg import spsolve
from transport.model import encode, decode, extend
from transport.protocols import drive_entries, perturbation
from transport.reservoirs import fermi, surface
from transport.simulate import simulate


def uniform_case():
    return dict(id='analytic_wire', family='independent_control',
                hamiltonian=encode([[0., -1.], [-1., 0.]]),
                leads=[dict(cell=encode([[0.]]), hop=encode([[-1.]]),
                            contact=encode([[-1.], [0.]]), mu=.6, temperature=0.),
                       dict(cell=encode([[0.]]), hop=encode([[-1.]]),
                            contact=encode([[0.], [-1.]]), mu=-.4, temperature=0.)],
                bound_mu=0., bound_temperature=0., drives=[],
                current_bonds=[[1, 0], [0, 1]], times=[0., .4, 2.])


def test_zero_temperature_landauer_and_density():
    case = uniform_case()
    result, metadata = simulate(case)
    expected_density = (np.arccos(-.6 / 2) + np.arccos(.4 / 2)) / (2 * np.pi)
    expected_current = 1. / (2 * np.pi)
    assert np.max(abs(result['density'] - expected_density)) < 2e-6
    assert np.max(abs(result['current'][:, 0] - expected_current)) < 2e-6
    assert np.max(abs(result['current'][:, 1] + expected_current)) < 2e-6
    assert metadata['spectral_sum_rule_error'] < 2e-6


def test_fully_isolated_noncommuting_drives():
    matrix = np.array([[.2, .35j], [-.35j, -.3]])
    case = dict(id='isolated', family='independent_control', hamiltonian=encode(matrix),
                leads=[], bound_mu=.1, bound_temperature=.13, times=np.linspace(0, 3, 13).tolist(),
                current_bonds=[[1, 0]], drives=[
                    dict(kind='add', entries=[[0, 0, 1., 0.]], amplitude=.7, duration=1.4, profile='ramp'),
                    dict(kind='add', entries=[[0, 1, 1., 0.]], amplitude=.6, duration=1., profile='ac', omega=2.3)])
    result, metadata = simulate(case)
    eigenvalues, vectors = eigh(matrix)
    initial = vectors * np.sqrt(fermi(eigenvalues, .1, .13))
    entries = drive_entries(case, [])

    def rhs(clock, state):
        dynamic = matrix + perturbation(clock, entries, 2).toarray()
        return (-1j * dynamic @ state.reshape(2, 2)).ravel()

    reference = solve_ivp(rhs, (0, 3), initial.ravel(), t_eval=case['times'],
                          rtol=1e-11, atol=1e-13, method='RK45')
    densities = np.sum(abs(reference.y.T.reshape(-1, 2, 2)) ** 2, axis=2)
    assert np.max(abs(result['density'] - densities)) < 2e-6


def test_dark_state_uses_bound_occupation():
    case = uniform_case()
    case['hamiltonian'] = encode([[0., -1., 0.], [-1., 0., 0.], [0., 0., .2]])
    case['leads'][0]['contact'] = encode([[-1.], [0.], [0.]])
    case['leads'][1]['contact'] = encode([[0.], [-1.], [0.]])
    case['bound_mu'] = .3
    result, metadata = simulate(case)
    assert np.max(abs(result['density'][:, 2] - 1)) < 1e-9
    case['bound_mu'] = -.3
    empty, metadata = simulate(case)
    assert np.max(abs(empty['density'][:, 2])) < 1e-9
    assert np.max(abs(result['density'][:, :2] - empty['density'][:, :2])) < 1e-8


def test_complex_singular_lead_basis_covariance():
    case = uniform_case()
    case['times'] = [0., .7, 1.5]
    case['drives'] = [dict(kind='contact_phase', lead=0, amplitude=.3, duration=.8, profile='voltage_phase')]
    for index, spec in enumerate(case['leads']):
        spec['cell'] = encode([[.1, -.65], [-.65, -.1]])
        spec['hop'] = encode([[0., -1.1j], [0., 0.]])
        spec['contact'] = encode([[-.8, .2j], [0., 0.]] if index == 0 else [[0., 0.], [.1j, -.9]])
        spec['temperature'] = .08
    original, metadata = simulate(case)
    transformed = copy.deepcopy(case)
    unitary = np.array([[1., 1j], [1j, 1.]]) / np.sqrt(2)
    for spec in transformed['leads']:
        spec['cell'] = encode(unitary.conj().T @ decode(spec['cell']) @ unitary)
        spec['hop'] = encode(unitary.conj().T @ decode(spec['hop']) @ unitary)
        spec['contact'] = encode(decode(spec['contact']) @ unitary)
    rotated, rotated_metadata = simulate(transformed)
    assert np.max(abs(original['density'] - rotated['density'])) < 3e-6
    assert np.max(abs(original['current'] - rotated['current'])) < 3e-6
    assert metadata['spectral_sum_rule_error'] < 1e-5


def test_zero_intercell_hopping_is_localized():
    case = uniform_case()
    for lead in case['leads']:
        lead['hop'] = encode([[0.]])
    result, metadata = simulate(case)
    finite, interfaces, ends = extend(case, 1)
    eigenvalues, eigenvectors = eigh(finite.toarray())
    density = np.sum(abs(eigenvectors[:2]) ** 2 * fermi(eigenvalues, 0., 0.), axis=1)
    assert np.max(abs(result['density'] - density)) < 1e-7


def test_shallow_bound_state_infinite_tail_normalization():
    case = uniform_case()
    case['hamiltonian'] = encode([[.02]])
    case['current_bonds'] = []
    case['times'] = [0., 1.]
    for spec in case['leads']:
        spec['contact'] = encode([[-1.]])
        spec['mu'] = 0.
    case['bound_mu'] = 3.
    occupied, metadata = simulate(case)
    case['bound_mu'] = -3.
    empty, empty_metadata = simulate(case)
    expected = .02 / np.sqrt(4 + .02 ** 2)
    assert abs(occupied['density'][0, 0] - empty['density'][0, 0] - expected) < 2e-6
    assert metadata['spectral_sum_rule_error'] < 2e-6


def test_narrow_resonance_is_not_a_bound_state():
    case = uniform_case()
    case['hamiltonian'] = encode([[0.]])
    case['current_bonds'] = []
    case['times'] = [0., 1.]
    for index, spec in enumerate(case['leads']):
        spec['contact'] = encode([[-.001]])
        spec['mu'] = .3 if index == 0 else -.3
    case['bound_mu'] = 1.
    result, metadata = simulate(case)
    assert abs(result['density'][0, 0] - .5) < 2e-5
    assert len(metadata['bound_energies']) == 0
    assert metadata['spectral_sum_rule_error'] < 2e-5


def test_gapped_sector_inside_another_channels_band():
    case = uniform_case()
    case['times'] = [0., 1.]
    for index, spec in enumerate(case['leads']):
        spec['cell'] = encode([[.1, -.65], [-.65, -.1]])
        spec['hop'] = encode([[0., -1.1j], [0., 0.]])
        spec['contact'] = encode([[-.8, .2j], [0., 0.]] if index == 0 else [[0., 0.], [.1j, -.9]])
        spec['mu'] = .04549727993307062
        spec['temperature'] = 0.
    case['bound_mu'] = .08
    original, metadata = simulate(case)
    enlarged = copy.deepcopy(case)
    for spec in enlarged['leads']:
        cell = np.zeros((3, 3), complex)
        hop = np.zeros((3, 3), complex)
        contact = np.zeros((2, 3), complex)
        cell[1:, 1:] = decode(spec['cell'])
        hop[0, 0] = -1.
        hop[1:, 1:] = decode(spec['hop'])
        contact[:, 1:] = decode(spec['contact'])
        spec['cell'], spec['hop'], spec['contact'] = encode(cell), encode(hop), encode(contact)
    result, metadata = simulate(enlarged)
    assert np.max(abs(result['density'] - original['density'])) < 3e-6
    assert metadata['spectral_sum_rule_error'] < 1e-5


def test_dark_state_at_zero_temperature_fermi_boundary_is_empty():
    case = uniform_case()
    case['hamiltonian'] = encode([[0., -1., -1.], [-1., 0., 0.], [-1., 0., 0.]])
    case['times'] = [0., 1.]
    case['current_bonds'] = []
    for spec in case['leads']:
        spec['contact'] = encode([[-1.], [0.], [0.]])
    case['bound_mu'] = 0.
    at_boundary, metadata = simulate(case)
    case['bound_mu'] = -.01
    below, metadata = simulate(case)
    case['bound_mu'] = .01
    above, metadata = simulate(case)
    assert np.max(abs(at_boundary['density'] - below['density'])) < 1e-8
    assert abs(np.sum(above['density'][0] - below['density'][0]) - 1.) < 1e-8


def test_general_surface_matches_finite_resolvent():
    random = np.random.default_rng(801)
    original = random.normal(size=(3, 3)) + 1j * random.normal(size=(3, 3))
    cell = .1 * (original + original.conj().T)
    hop = -.7 * np.eye(3) + .04 * (random.normal(size=(3, 3)) + 1j * random.normal(size=(3, 3)))
    count = 100
    lower = sparse.diags(np.ones(count - 1), -1, shape=(count, count))
    matrix = sparse.kron(sparse.eye(count), cell) + sparse.kron(lower, hop) + sparse.kron(lower.T, hop.conj().T)
    source = np.zeros((3 * count, 3), complex)
    source[:3] = np.eye(3)
    for energy in [-1.1, 0., .9]:
        finite = spsolve(((energy + .2j) * sparse.eye(3 * count) - matrix).tocsc(), source)[:3]
        infinite = surface(energy, cell, hop, eta=.2)
        assert np.max(abs(finite - infinite)) < 1e-8
        residual = ((energy + .2j) * np.eye(3) - cell - hop.conj().T @ infinite @ hop) @ infinite - np.eye(3)
        assert np.max(abs(residual)) < 1e-10


def test_all_flat_lead_bands_use_bound_occupation():
    case = uniform_case()
    case['times'] = [0., 1.]
    case['bound_mu'], case['bound_temperature'] = .13, .08
    for index, spec in enumerate(case['leads']):
        spec['cell'] = encode(np.zeros((2, 2)))
        spec['hop'] = encode([[0., -1.], [0., 0.]])
        spec['contact'] = encode([[-.8, .2], [0., 0.]] if index == 0 else [[0., 0.], [.1, -.7]])
    result, metadata = simulate(case)
    finite, interfaces, ends = extend(case, 3)
    values, states = eigh(finite.toarray())
    expected = np.sum(abs(states[:2]) ** 2 * fermi(values, .13, .08), axis=1)
    assert np.max(abs(result['density'] - expected)) < 1e-7
    assert metadata['spectral_sum_rule_error'] < 1e-7


def test_delayed_narrow_pulse_is_not_skipped():
    case = dict(id='delayed', family='independent_control', hamiltonian=encode([[0., 0.], [0., 1.]]),
                leads=[], bound_mu=.5, bound_temperature=0., current_bonds=[[1, 0]],
                times=[0., 1., 1.037, 1.057, 1.077, 2.], drives=[
                    dict(kind='add', entries=[[1, 0, 1., 0.]], amplitude=3.5, duration=.04, start=1.037, profile='pulse')])
    result, metadata = simulate(case)
    entries = drive_entries(case, [])
    matrix = decode(case['hamiltonian'])

    def rhs(clock, state):
        return -1j * (matrix + perturbation(clock, entries, 2).toarray()) @ state

    reference = solve_ivp(rhs, (0, 2), np.array([1., 0.], complex), t_eval=case['times'],
                          max_step=.002, rtol=1e-10, atol=1e-12)
    assert np.max(abs(result['density'] - abs(reference.y.T) ** 2)) < 2e-7
    assert result['density'][-1, 1] > .004


def test_complex_hopping_extremum_across_brillouin_boundary():
    case = uniform_case()
    for spec in case['leads']:
        spec['hop'] = encode([[-np.exp(.005j)]])
    result, metadata = simulate(case)
    expected = (np.arccos(-.6 / 2) + np.arccos(.4 / 2)) / (2 * np.pi)
    assert np.max(abs(result['density'] - expected)) < 2e-6
    assert np.max(abs(result['current'][:, 0] - 1 / (2 * np.pi))) < 2e-6
    assert metadata['spectral_sum_rule_error'] < 2e-6
