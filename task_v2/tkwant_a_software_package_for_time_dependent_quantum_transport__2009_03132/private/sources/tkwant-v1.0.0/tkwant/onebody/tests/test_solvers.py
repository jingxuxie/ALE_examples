# -*- coding: utf-8 -*-
# Copyright 2016-2018 tkwant authors.
#
# This file is part of tkwant.  It is subject to the license terms in the file
# LICENSE.rst found in the top-level directory of this distribution and at
# http://kwant-project.org/license.  A list of tkwant authors can be found in
# the file AUTHORS.rst at the top-level directory of this distribution and at
# http://kwant-project.org/authors.

import pytest
from math import cos, sin
import itertools as it
import functools as ft
import numpy as np
from numpy.testing import assert_array_almost_equal
import tinyarray as ta
import scipy
import scipy.integrate._ode as ode
import scipy.sparse.linalg as spla
import kwant
import pickle
import cmath
from scipy.special import erf
import collections
import copy


from ... import leads
from .. import solvers, kernels, WaveFunction, ScatteringStates


solvers = {
    'scipy': (
        solvers.Scipy,
        [
            dict(integrator=ode.dopri5),
            dict(integrator=ode.dop853),
        ]
    ),
}


# TODO: focus on default kernel only for params
available_kernels = {
    'scipy': kernels.Scipy
}


# available_kernels = {
#    'scipy': kernels.Scipy,
#    'simple': kernels.Simple,
#    'sparseblas': getattr(kernels, 'SparseBlas', None)
# }


def get_solver_kernel(solver_t, kernel_t):
    skip = False
    reasons = []
    if kernel_t in ('sparseblas',):
        if not hasattr(kernels, 'SparseBlas'):
            skip = True
            reasons.append('No sparse BLAS available.')
    skip = pytest.mark.skipif(skip, reason=', '.join(reasons))

    kernel_t = available_kernels[kernel_t]
    solver_t, solver_params = solvers[solver_t]

    return [pytest.param(ft.partial(solver_t, **p), kernel_t, marks=skip)
            for p in solver_params]


def all_solvers_kernels():
    return pytest.mark.parametrize(
        ('solver_type', 'kernel_type'),
        list(it.chain.from_iterable(
            it.starmap(get_solver_kernel,
                       it.product(solvers.keys(), available_kernels.keys())))))


def all_solvers():  # test only with the pure python kernel
    return pytest.mark.parametrize(
        ('solver_type', 'kernel_type'),
        list(it.chain.from_iterable(
            it.starmap(get_solver_kernel,
                       it.product(solvers.keys(), ['scipy'])))))


def make_simple_lead(lat, N):
    I0 = ta.identity(lat.norbs)
    syst = kwant.Builder(kwant.TranslationalSymmetry((-1, 0)))
    syst[(lat(0, j) for j in range(N))] = 4 * I0
    syst[lat.neighbors()] = -1 * I0
    return syst


def make_complex_lead(lat, N):
    I0 = ta.identity(lat.norbs)
    syst = kwant.Builder(kwant.TranslationalSymmetry((-1, 0)))
    syst[(lat(0, j) for j in range(N))] = 4 * I0
    syst[kwant.HoppingKind((0, 1), lat)] = -1 * I0
    syst[(lat(0, 0), lat(1, 0))] = -1j * I0
    syst[(lat(0, 1), lat(1, 0))] = -1 * I0
    syst[(lat(0, 2), lat(1, 2))] = (-1 + 1j) * I0
    return syst


class RandomOnsite:
    def __init__(self, I0):
        self.I0 = I0

    def __call__(self, site, time, salt):
        return (4 + kwant.digest.uniform(site.tag, salt=salt)) * self.I0


def make_system(lat, N):
    I0 = ta.identity(lat.norbs)
    syst = kwant.Builder()
    syst[(lat(i, j) for i in range(N) for j in range(N))] = RandomOnsite(I0)
    syst[lat.neighbors()] = -1 * I0
    return syst


def make_td_system(lat, N, td_onsite):
    I0 = ta.identity(2)
    syst = kwant.Builder()
    square = it.product(range(N), range(N))
    syst[(lat(i, j) for i, j in square)] = td_onsite
    syst[lat.neighbors()] = -1 * I0
    return syst


def make_system_with_leads(lat, N, lead_maker):
    syst = make_system(lat, N)
    syst.attach_lead(lead_maker(lat, N))
    syst.attach_lead(lead_maker(lat, N).reversed())
    return syst


def make_td_system_with_leads(lat, N, lead_maker, td_onsite):
    syst = make_td_system(lat, N, td_onsite)
    syst.attach_lead(lead_maker(lat, N))
    syst.attach_lead(lead_maker(lat, N).reversed())
    return syst


@pytest.mark.integtest  # run only as integration test
@all_solvers_kernels()
def test_finite_time_independent(solver_type, kernel_type):
    N = 10
    salt = '1'
    lat = kwant.lattice.square(norbs=2)
    syst = make_system(lat, N)
    fsyst = syst.finalized()

    ### Start from eigenstate
    # no time dependence and starting from an eigenstate
    # φ means that we should evolve to φ * exp(-1j * E * t)
    H0 = fsyst.hamiltonian_submatrix(params={'time': 0, 'salt': salt})
    evals, evecs = spla.eigsh(H0)
    psi_st = evecs[:, 0]
    E = evals[0]
    # Solve "trivially" using (H0-E) @ psibar + W(t) @ psibar.
    # The actual ODE that we solve is 0=0, as W(t) = 0 for this system.
    psi = WaveFunction.from_kwant(syst=fsyst, params={'salt': salt}, psi_init=psi_st, energy=E,
                                  solver_type=solver_type, kernel_type=kernel_type)
    # Test that we get the same result when we use (H0 + W(t)) * psi directly.
    # We can do this because the system is *finite*
    psi_alt = WaveFunction.from_kwant(syst=fsyst, psi_init=psi_st, params={'salt': salt},
                                      solver_type=solver_type, kernel_type=kernel_type)
    # Construct a wavefunction directly from Hamiltonian matrices with sparse H0
    H0_sparse = fsyst.hamiltonian_submatrix(params={'time': 0, 'salt': salt}, sparse=True)
    W = kernels.PerturbationExtractor(fsyst, time_name='time', time_start=0,
                                      params=dict(salt=salt))
    psi_sparse = WaveFunction(H0=H0_sparse, W=W, psi_init=psi_st, energy=E, params={'salt': salt},
                              solver_type=solver_type, kernel_type=kernel_type)

    for time in (0., 1., 5.):
        psi.evolve(time)
        psi_alt.evolve(time)
        psi_sparse.evolve(time)
        assert np.allclose(psi.psi(), psi_st * np.exp(-1j * E * time))
        assert np.allclose(psi_alt.psi(), psi.psi())
        assert np.allclose(psi_sparse.psi(), psi_st * np.exp(-1j * E * time))


# TODO: pickle works only with the python kernel for the moment.
# Make it working for all kernels such that the test runs with
# @all_solvers_kernels().
@all_solvers()
def test_finite_time_independent_restart_pickle(solver_type, kernel_type):
    N = 10
    salt = '1'
    lat = kwant.lattice.square(norbs=2)
    syst = make_system(lat, N)
    fsyst = syst.finalized()

    ### Start from eigenstate
    # no time dependence and starting from an eigenstate
    # φ means that we should evolve to φ * exp(-1j * E * t)
    H0 = fsyst.hamiltonian_submatrix(params={'time': 0, 'salt': salt})
    evals, evecs = spla.eigsh(H0)

    ### test restarting a calculation
    psi_rand = (np.random.random((H0.shape[0],)) +
                1j * np.random.random((H0.shape[0],)))
    for psi_init, E in [(psi_rand, None), (evecs[:, 0], evals[0])]:
        psi = WaveFunction.from_kwant(syst=fsyst, psi_init=psi_init, params={'salt': salt}, energy=E,
                                      solver_type=solver_type, kernel_type=kernel_type)
        psi.evolve(2)
        saved = pickle.dumps(psi)
        psi2 = pickle.loads(saved)
        psi.evolve(5)
        psi2.evolve(5)
        assert np.allclose(psi.psi(), psi2.psi())


@pytest.mark.integtest  # run only as integration test
@all_solvers_kernels()
def test_finite_time_dependent(solver_type, kernel_type):
    N = 10
    salt = '1'
    lat = kwant.lattice.square(norbs=2)
    I0 = ta.identity(2)
    SX = ta.array([[0, 1], [1, 0]])
    uniform = kwant.digest.uniform

    def td_onsite(site, time, salt):
        static_part = (4 + uniform(site.tag, salt=salt)) * I0
        td_part = uniform(site.tag, salt=salt + '1') * SX * cos(time)
        return static_part + td_part

    syst = make_td_system(lat, N, td_onsite)
    fsyst = syst.finalized()
    nsites, _, norbs = fsyst.site_ranges[-1]
    sx_op = kwant.operator.Density(fsyst, np.array([[0, 1], [1, 0]]))

    H0 = fsyst.hamiltonian_submatrix(params={'time': 0, 'salt': salt})
    evals, evecs = spla.eigsh(H0)
    psi_st = evecs[:, 0]
    E = evals[0]

    perturb_types = [kernels.PerturbationExtractor, kernels.PerturbationInterpolator]

    for perturb in perturb_types:
        ### system has s_z symmetry: test for conservation of s_z
        psi = WaveFunction.from_kwant(syst=fsyst, psi_init=psi_st, energy=E, params={'salt': salt},
                                      perturbation_type=perturb,
                                      solver_type=solver_type, kernel_type=kernel_type)
        density = sx_op(psi.psi())
        should_be = np.sum(density)
        for time in (1., 5., 10.):
            density = sx_op(psi.psi())
            assert np.isclose(
                should_be,
                np.sum(density)
            )


@pytest.mark.integtest  # run only as integration test
@all_solvers_kernels()
def test_infinite_time_independent(solver_type, kernel_type):
    N = 10
    tmax = 5
    eps = 1.1  # 1E-8  # boundary valid up to time = tmax + 1 instead tmax
    salt = '1'
    E = 1.
    lat = kwant.lattice.square(norbs=2)
    syst = make_system_with_leads(lat, N, make_simple_lead)
    fsyst = syst.finalized()
    norbs = fsyst.site_ranges[-1][-1]

    boundaries = [leads.SimpleBoundary(tmax=tmax)] * 2

    ### Starting from the trivial state
    # solution should be zero everywhere
    zeros = np.zeros((norbs,), complex)
    psi = WaveFunction.from_kwant(fsyst, zeros, params={'salt': salt}, boundaries=boundaries,
                                  solver_type=solver_type, kernel_type=kernel_type)
    for time in (0., tmax / 4, tmax / 2, tmax - eps):
        psi.evolve(time)
        assert np.allclose(psi.psi(), np.zeros((norbs,)))
    pytest.raises(RuntimeError, psi.evolve, tmax + eps)

    ### Start from eigenstate
    # No time dependence and starting from an eigenstate
    # φ means that we should evolve to φ * exp(-1j * E * t).
    # The actual ODE that we solve is 0=0, as W(t) = 0 for this system.
    # Call to Kwant requires time arg to be passed explicitly
    psi_st = kwant.wave_function(fsyst, energy=E, params={'time': 0, 'salt': salt})(0)[0]
    psi = WaveFunction.from_kwant(fsyst, psi_st, params={'salt': salt},
                                  boundaries=boundaries, energy=E,
                                  solver_type=solver_type, kernel_type=kernel_type)
    for time in (0., tmax / 4, tmax / 2, tmax - eps):
        psi.evolve(time)
        assert np.allclose(psi.psi(), psi_st * np.exp(-1j * E * time))

    norbs = fsyst.site_ranges[-1][-1]
    psi_random = np.random.random((norbs,)) + 1j * np.random.random((norbs,))

    ### test that boundary conditions are OK by testing that solutions
    ### match when the boundary conditions are extended
    extended_boundaries = [leads.SimpleBoundary(tmax=2 * tmax)] * 2
    psi = WaveFunction.from_kwant(fsyst, psi_random, boundaries=boundaries, params={'salt': salt},
                                  solver_type=solver_type, kernel_type=kernel_type)
    psi_ext = WaveFunction.from_kwant(fsyst, psi_random, boundaries=extended_boundaries, params={'salt': salt},
                                      solver_type=solver_type, kernel_type=kernel_type)
    size = psi.psibar.shape[0]  # largest subset of psi_ext and psi
    for time in (0., tmax / 4, tmax / 2, tmax - eps):
        psi.evolve(time)
        psi_ext.evolve(time)
        assert np.allclose(psi_ext.psi()[:size], psi.psi()[:size])


# TODO: pickle works only with the python kernel for the moment.
# Make it working for all kernels such that the test runs with
# @all_solvers_kernels().
@pytest.mark.integtest  # run only as integration test
@all_solvers()
def test_infinite_time_independent_restart_pickle(solver_type, kernel_type):
    N = 10
    tmax = 5
    eps = 1.1  # 1E-8  # boundary valid up to time = tmax + 1 instead tmax
    salt = '1'
    E = 1.
    lat = kwant.lattice.square(norbs=2)
    syst = make_system_with_leads(lat, N, make_simple_lead)
    fsyst = syst.finalized()
    norbs = fsyst.site_ranges[-1][-1]

    boundaries = [leads.SimpleBoundary(tmax=tmax)] * 2
    psi_st = kwant.wave_function(fsyst, energy=E, params={'time': 0, 'salt': salt})(0)[0]

    norbs = fsyst.site_ranges[-1][-1]
    psi_random = np.random.random((norbs,)) + 1j * np.random.random((norbs,))

    ### test restarting a calculation
    for psi_k, E in [(psi_random, None), (psi_st, E)]:
        psi = WaveFunction.from_kwant(fsyst, psi_k, boundaries=boundaries, params={'salt': salt}, energy=E,
                                      solver_type=solver_type, kernel_type=kernel_type)
        psi.evolve(tmax / 2)  # evolve forward a bit
        saved = pickle.dumps(psi)
        psi2 = pickle.loads(saved)
        psi.evolve(tmax - eps)
        psi2.evolve(tmax - eps)
        assert np.allclose(psi.psi(), psi2.psi())


@pytest.mark.integtest  # run only as integration test
@all_solvers_kernels()
def test_infinite_time_dependent(solver_type, kernel_type):
    N = 10
    salt = '1'
    lat = kwant.lattice.square(norbs=2)
    I0 = ta.identity(2)
    SZ = ta.array([[1, 0], [0, -1]])
    uniform = kwant.digest.uniform

    def td_onsite(site, time, salt):
        static_part = (4 + uniform(site.tag, salt=salt)) * I0
        td_part = SZ * sin(time)
        return static_part + td_part

    def phi_t(time, salt):
        return (1 - cos(time)) * ta.array([1, -1])  # diagonal part

    ### test when adding time-dependent voltage everywhere
    syst = make_td_system_with_leads(lat, N, make_simple_lead, td_onsite)
    # add TD voltage to leads as well
    leads.add_voltage(syst, 0, phi_t)
    leads.add_voltage(syst, 1, phi_t)
    # finalize
    fsyst = syst.finalized()
    nsites, _, norbs = fsyst.site_ranges[-1]

    sz_op = kwant.operator.Density(fsyst, SZ)
    boundaries = [leads.SimpleBoundary(tmax=11.)] * 2
    E = 1.

    # same time-dependent voltage everywhere, there should
    # be no change in the observables
    scattering_states = kwant.wave_function(fsyst, energy=E, params={'time': 0, 'salt': salt})
    psi_st = scattering_states(0)[0]
    perturbation_type = kernels.PerturbationExtractor
    psi = WaveFunction.from_kwant(syst=fsyst, boundaries=boundaries, params={'salt': salt},
                                  psi_init=psi_st, energy=E,
                                  perturbation_type=perturbation_type,
                                  solver_type=solver_type, kernel_type=kernel_type)
    should_be = sz_op(psi.psi())
    for time in (1., 5., 10.):
        psi.evolve(time)
        density = sz_op(psi.psi())
        assert np.allclose(
            should_be,
            density
        )


TIMESTEPS = [0, 1., 5]


def one_level_system(only_open=True):

    def make_system_2(a=1, gamma=1.0, W=1, L=30):

        lat = kwant.lattice.square(a=a, norbs=1)
        syst = kwant.Builder()

        def onsite_potential(site, time):
            return 4 * gamma * cmath.exp(- 1j * time)

        def gaussian(time, t0, A, sigma):
            return A * (1 + erf((time - t0) / sigma))

        # time dependent coupling with gaussian pulse
        def coupling_nn(site1, site2, time, t0, A, sigma):
            return - gamma * cmath.exp(- 1j * gaussian(time, t0, A, sigma))

        # Define the scattering region.
        syst[(lat(x, y) for x in range(L) for y in range(W))] = onsite_potential
        syst[lat.neighbors()] = -gamma
        # time dependent coupling between two sites 0 and 1
        for y in range(W):
            syst[lat(0, y), lat(1, y)] = coupling_nn

        # Define and attach the leads.
        # Construct the left lead.
        lead = kwant.Builder(kwant.TranslationalSymmetry((-a, 0)))
        lead[(lat(0, j) for j in range(W))] = 4 * gamma
        lead[lat.neighbors()] = -gamma

        # Attach the left lead and its reversed copy.
        syst.attach_lead(lead)
        syst.attach_lead(lead.reversed())

        return syst

    syst = make_system_2().finalized()
    if only_open:  # return only open mode
        return pytest.mark.parametrize('syst, energy, nb_open_modes',
                                       [(syst, 3, 1)])
    # return open and closed modes
    return pytest.mark.parametrize('syst, energy, nb_open_modes',
                                   [(syst, 3, 1), (syst, 0, 0)])


def make_boundaries(nb_leads, tmax=50):
    boundaries = [leads.SimpleBoundary(tmax=tmax)] * nb_leads
    return boundaries, tmax


def closed_sytem():
    def make_system(a=1, t=1.0, r=10, r_time_dep=3):
        # Start with an empty tight-binding system and a single square lattice.
        # `a` is the lattice constant (by default set to 1 for simplicity).

        lat = kwant.lattice.square(a, norbs=1)

        syst = kwant.Builder()

        # Define the quantum dot
        def circle(r):
            def _(pos):
                (x, y) = pos
                rsq = x ** 2 + y ** 2
                return rsq < r ** 2
            return _

        # Formally takes the `time` parameter, but does not use it.
        def hopx(site1, site2, time, V, B):
            # The magnetic field is controlled by the parameter B
            # and oscillates in time
            y = site1.pos[1]
            if time > 0:
                return -t * np.exp(-1j * B * y)
            return 0

        # Decorated to notify tkwant that the function uses the `time` parameter.
        def potential(site, time, V, B):
            x, y = site.pos
            return 4 * t + np.sqrt(x**2 + y**2) * V * (1 - np.cos(time))

        syst[lat.shape(circle(r), (0, 0))] = 4 * t
        syst[lat.shape(circle(r_time_dep), (0, 0))] = potential
        # hoppings in x-direction
        syst[kwant.builder.HoppingKind((1, 0), lat, lat)] = hopx
        # hoppings in y-directions
        syst[kwant.builder.HoppingKind((0, 1), lat, lat)] = -t

        # It's a closed system, so no leads
        return syst

    syst = make_system().finalized()

    params = {'V': 0, 'B': 0}
    tparams = params.copy()
    tparams['time'] = 0

    H = syst.hamiltonian_submatrix(params=tparams)
    evals, evecs = np.linalg.eigh(H)

    energy = evals[0]
    psi_init = evecs[:, 0]

    psi_random = np.random.random(psi_init.shape) + 1j * np.random.random(psi_init.shape)

    return pytest.mark.parametrize('psi_init, syst, energy, params',
                                   [(psi_init, syst, energy, params),
                                    (psi_random, syst, None, params)])


def open_sytem():

    lat = kwant.lattice.square(norbs=1)

    def make_circle_system(radius):
        syst = kwant.Builder()
        syst[lat.shape(lambda pos: np.linalg.norm(pos) < radius, (0, 0))] = 4
        syst[lat.neighbors()] = -1
        return syst

    def make_lead(width):
        lead = kwant.Builder(kwant.TranslationalSymmetry((-1, 0)))
        lead[(lat(0, j) for j in range(-(width - 1) // 2, width // 2 + 1))] = 4
        lead[lat.neighbors()] = -1
        return lead

    syst = make_circle_system(radius=10)
    lead = make_lead(width=7)
    syst.attach_lead(lead)
    syst.attach_lead(lead.reversed())

    def faraday_flux(time, a, b):
        return a * (time - b * np.sin(0.1 * time)) / 2

    leads.add_voltage(syst, 0, faraday_flux)
    syst = syst.finalized()

    # create a time-dependent wavefunction that starts in a scattering state
    # originating from the left lead

    energy = 1.
    params = {'a': 0.1, 'b': 10}
    tparams = params.copy()
    tparams['time'] = 0
    scattering_states = kwant.wave_function(syst, energy=energy, params=tparams)
    psi_st = scattering_states(0)[0]

    psi_random = np.random.random(psi_st.shape) + 1j * np.random.random(psi_st.shape)

    return pytest.mark.parametrize('psi_init, syst, energy, params',
                                   [(psi_st, syst, energy, params),
                                    (psi_random, syst, None, params)])


@closed_sytem()
def test_WaveFunction_closed_system_params_copied(psi_init, syst, energy, params):

    params_copy = params.copy()
    wave_function = WaveFunction.from_kwant(psi_init=psi_init, syst=syst,
                                            energy=energy, params=params_copy)

    assert wave_function.params == params_copy
    wave_function.params = None
    assert params_copy == params


@open_sytem()
def test_WaveFunction_open_system_params_copied(psi_init, syst, energy, params):

    params_copy = params.copy()
    boundaries, tmax = make_boundaries(nb_leads=len(syst.leads))

    wave_function = WaveFunction.from_kwant(psi_init=psi_init, syst=syst, energy=energy,
                                            boundaries=boundaries, params=params_copy)

    assert wave_function.params == params_copy
    wave_function.params = None
    assert params_copy == params


@closed_sytem()
@pytest.mark.integtest
def test_WaveFunction_closed_system_default(psi_init, syst, energy, params):

    density_operator = kwant.operator.Density(syst)

    wave_function = WaveFunction.from_kwant(psi_init=psi_init, syst=syst,
                                            energy=energy, params=params)

    assert wave_function.time == 0
    assert wave_function.params == params

    if energy is None:
        assert wave_function.energy is None
    else:
        assert wave_function.energy == energy

    for time in TIMESTEPS:

        wave_function.evolve(time)
        assert wave_function.time == time
        assert wave_function.params == params

        density = wave_function.evaluate(density_operator)
        assert isinstance(density, np.ndarray)
        assert density.shape == psi_init.shape
        assert np.array([isinstance(x, float) for x in density]).all()

        assert isinstance(wave_function.psi(), np.ndarray)
        assert wave_function.psi().shape == psi_init.shape
        assert np.array([isinstance(x, complex) for x in wave_function.psi()]).all()


@open_sytem()
@pytest.mark.integtest
def test_WaveFunction_open_system_default(psi_init, syst, energy, params):

    density_operator = kwant.operator.Density(syst)
    boundaries, tmax = make_boundaries(nb_leads=len(syst.leads))

    wave_function = WaveFunction.from_kwant(psi_init=psi_init, syst=syst, energy=energy,
                                            boundaries=boundaries, params=params)

    assert wave_function.time == 0
    if energy is None:
        assert wave_function.energy is None
    else:
        assert wave_function.energy == energy

    for time in TIMESTEPS:

        assert time <= tmax
        wave_function.evolve(time)
        assert wave_function.time == time
        assert wave_function.params == params

        density = wave_function.evaluate(density_operator)
        assert isinstance(density, np.ndarray)
        assert density.shape == psi_init.shape
        assert np.array([isinstance(x, float) for x in density]).all()

        assert isinstance(wave_function.psi(), np.ndarray)
        assert wave_function.psi().shape == psi_init.shape
        assert np.array([isinstance(x, complex) for x in wave_function.psi()]).all()


@open_sytem()
def test_WaveFunction_open_system__init__raises(psi_init, syst, energy, params):

    # open system without boundaries
    pytest.raises(ValueError, WaveFunction.from_kwant, psi_init=psi_init, syst=syst,
                  energy=energy, params=params)

    boundaries, tmax = make_boundaries(nb_leads=len(syst.leads), tmax=6)

    params_with_time = params.copy()
    params_with_time['time'] = 0
    with pytest.raises(KeyError) as exc:
        WaveFunction.from_kwant(psi_init=psi_init, syst=syst, boundaries=boundaries,
                                energy=energy, params=params_with_time)
    error_string = str(exc.value).strip('\"')  # remove etra quotes
    assert error_string == "'params' must not contain time"

    # no params passed at all
    with pytest.raises(TypeError) as exc:
        WaveFunction.from_kwant(psi_init=psi_init, syst=syst, boundaries=boundaries,
                                energy=energy)
    assert str(exc.value) == 'System is missing required arguments: "a", "b"'

    params_not_matching = {'a': 0.1, 'B': 0.2}
    with pytest.raises(TypeError) as exc:
        WaveFunction.from_kwant(psi_init=psi_init, syst=syst, boundaries=boundaries,
                                energy=energy, params=params_not_matching)
    assert str(exc.value) == 'System is missing required arguments: "b"'


@closed_sytem()
def test_WaveFunction_closed_system__init__raises(psi_init, syst, energy, params):

    # provide boundaries to a closed system
    boundaries, tmax = make_boundaries(nb_leads=len(syst.leads), tmax=6)
    with pytest.raises(ValueError) as exc:
        WaveFunction.from_kwant(psi_init=psi_init, syst=syst, boundaries=boundaries,
                                energy=energy, params=params)
    msg = 'No boundary conditions must be provided for a system without leads.'
    assert msg in str(exc.value)

    params_with_time = params.copy()
    params_with_time['time'] = 0
    with pytest.raises(KeyError) as exc:
        WaveFunction.from_kwant(psi_init=psi_init, syst=syst,
                                energy=energy, params=params_with_time)
    error_string = str(exc.value).strip('\"')  # remove etra quotes
    assert error_string == "'params' must not contain time"

    # no params passed at all
    with pytest.raises(TypeError) as exc:
        WaveFunction.from_kwant(psi_init=psi_init, syst=syst, energy=energy)
    assert str(exc.value) == 'System is missing required arguments: "V", "B"'

    params_not_matching = {'V': 0.1, 'b': 0.2}
    with pytest.raises(TypeError) as exc:
        WaveFunction.from_kwant(psi_init=psi_init, syst=syst,
                                energy=energy, params=params_not_matching)
    assert str(exc.value) == 'System is missing required arguments: "B"'


@open_sytem()
@pytest.mark.integtest
def test_WaveFunction_open_system_evolve_raises(psi_init, syst, energy, params):

    boundaries, tmax = make_boundaries(nb_leads=len(syst.leads), tmax=6)
    wave_function = WaveFunction.from_kwant(psi_init=psi_init, syst=syst, energy=energy,
                                            boundaries=boundaries, params=params)
    wave_function.evolve(time=5)

    # evolve back in time
    backward_time = wave_function.time - 0.5
    pytest.raises(ValueError, wave_function.evolve, time=backward_time)

    # max evolution time
    time_larger_tmax = tmax + 2
    pytest.raises(RuntimeError, wave_function.evolve, time=time_larger_tmax)


@closed_sytem()
@pytest.mark.integtest
def test_WaveFunction_closed_system_evolve_raises(psi_init, syst, energy, params):

    wave_function = WaveFunction.from_kwant(psi_init=psi_init, syst=syst,
                                            energy=energy, params=params)

    wave_function.evolve(time=5)
    # evolve back in time
    backward_time = wave_function.time - 0.5
    pytest.raises(ValueError, wave_function.evolve, time=backward_time)


@open_sytem()
def test_WaveFunction_open_system_evaluate_raises(psi_init, syst, energy, params):

    boundaries, tmax = make_boundaries(nb_leads=len(syst.leads), tmax=6)
    wave_function = WaveFunction.from_kwant(psi_init=psi_init, syst=syst,
                                            energy=energy, boundaries=boundaries, params=params)

    # bind should fail
    def radius(site):
        x, y = site.pos
        return np.sqrt(x**2 + y**2)
    density_operator = kwant.operator.Density(syst, radius).bind()

    with pytest.raises(ValueError) as exc:
        wave_function.evaluate(density_operator)
    assert str(exc.value) == 'Operator must not use pre-bind values'


@closed_sytem()
def test_WaveFunction_closed_system_evaluate_raises(psi_init, syst, energy, params):

    wave_function = WaveFunction.from_kwant(psi_init=psi_init, syst=syst, energy=energy,
                                            params=params)

    # bind should fail
    def radius(site):
        x, y = site.pos
        return np.sqrt(x**2 + y**2)
    density_operator = kwant.operator.Density(syst, radius).bind()

    with pytest.raises(ValueError) as exc:
        wave_function.evaluate(density_operator)
    assert str(exc.value) == 'Operator must not use pre-bind values'


@one_level_system(only_open=False)
def test_scattering_states_default(syst, energy, nb_open_modes):

    tmax = 50
    params = {'t0': 0, 'A': 0.00157, 'sigma': 24}
    for lead in range(len(syst.leads)):
        states = ScatteringStates(syst, energy, lead, tmax, params=params)
        assert states.energy == energy
        assert states.lead == lead
        assert isinstance(states, collections.abc.Iterable)
        assert len(states) == nb_open_modes
        assert np.array([isinstance(state, WaveFunction) for state in states]).all()

        # check added attribute in each instance
        for mode, state in enumerate(states):
            assert isinstance(state.lead, int)
            assert isinstance(state.mode, int)
            assert state.lead == lead
            assert state.mode == mode


@one_level_system()
@pytest.mark.parametrize('time', TIMESTEPS)
def test_scattering_states_against_reference(syst, energy, nb_open_modes, time):

    boundaries, tmax = make_boundaries(nb_leads=len(syst.leads))
    assert time <= tmax

    # test only for one lead/mode pair, as calculations are expensive
    lead = 0
    mode = 0
    params = {'t0': 0, 'A': 0.00157, 'sigma': 24}

    states = ScatteringStates(syst, energy, lead, tmax, params=params)
    state = states[mode]
    state.evolve(time)

    # reference result
    tparams = params.copy()
    tparams['time'] = 0
    scattering_states = kwant.wave_function(syst, energy=energy, params=tparams)
    psi_st = scattering_states(lead)[mode]
    psi_ref = WaveFunction.from_kwant(psi_init=psi_st, syst=syst, boundaries=boundaries, energy=energy, params=params)
    psi_ref.evolve(time)

    assert np.allclose(state.psi(), psi_ref.psi())


@one_level_system()
def test_scattering_states__init__raises(syst, energy, nb_open_modes):

    lead = 0
    boundaries, tmax = make_boundaries(nb_leads=len(syst.leads))
    params = {'t0': 0, 'A': 0.00157, 'sigma': 24}

    # system has no leads
    system_without_leads = copy.deepcopy(syst)
    delattr(system_without_leads, 'leads')
    pytest.raises(AttributeError, ScatteringStates, syst=system_without_leads,
                  energy=energy, lead=lead, tmax=tmax, params=params)
    # energy is not a float
    pytest.raises(TypeError, ScatteringStates, syst=syst,
                  energy=energy + 1j, lead=lead, tmax=tmax, params=params)
    # lead index is not an integer
    pytest.raises(TypeError, ScatteringStates, syst=syst,
                  energy=energy, lead=float(lead), tmax=tmax, params=params)
    # lead index is out of range
    pytest.raises(ValueError, ScatteringStates, syst=syst,
                  energy=energy, lead=len(syst.leads) + 1, tmax=tmax, params=params)
    # tmax/boundaries are both present, but mutually exclusive
    pytest.raises(ValueError, ScatteringStates, syst=syst,
                  energy=energy, lead=lead, tmax=tmax, boundaries=boundaries, params=params)

    params_with_time = {'t0': 0, 'A': 0.00157, 'sigma': 24, 'time': 0}
    with pytest.raises(KeyError) as exc:
        ScatteringStates(syst, lead=0, energy=2.4, tmax=tmax,
                         params=params_with_time)
    error_string = str(exc.value).strip('\"')  # remove etra quotes
    assert error_string == "'params' must not contain time"

    # no params passed at all
    with pytest.raises(TypeError) as exc:
        ScatteringStates(syst, lead=0, energy=2.4, tmax=tmax)
    assert str(exc.value) == 'System is missing required arguments: "t0", "A", "sigma"'

    params_without_sigma = {'t0': 0, 'A': 0.00157}
    with pytest.raises(TypeError) as exc:
        ScatteringStates(syst, lead=0, energy=2.4, tmax=tmax,
                         params=params_without_sigma)
    assert str(exc.value) == 'System is missing required arguments: "sigma"'


@one_level_system()
def test_scattering_states__getitem__raises(syst, energy, nb_open_modes):
    params = {'t0': 0, 'A': 0.00157, 'sigma': 24}
    states = ScatteringStates(syst, energy, lead=0, tmax=50, params=params)
    # mode index out of range
    pytest.raises(KeyError, lambda: states[len(states) + 1])
    # mode index is not an integer
    pytest.raises(TypeError, lambda: states[float(len(states))])


@pytest.mark.integtest
@all_solvers_kernels()
def test_time_argument_name_and_initial_time_change(solver_type, kernel_type):

    N = 10
    lat = kwant.lattice.square(norbs=2)
    I0 = ta.identity(2)
    SX = ta.array([[0, 1], [1, 0]])
    uniform = kwant.digest.uniform

    # make twice a system, one where time time variable is named time
    # and the initial time starts at time=0 (the default case)
    # and a second system where the time varible is named zeit
    # and the initial time starts at zeit = 42

    def td_onsite_time(site, time, salt):
        static_part = (4 + uniform(site.tag, salt=salt)) * I0
        td_part = uniform(site.tag, salt=salt + '1') * SX * cos(time)
        return static_part + td_part

    zeit_offset = 42  # the initial time

    def td_onsite_zeit(site, zeit, salt):
        time = zeit - zeit_offset
        static_part = (4 + uniform(site.tag, salt=salt)) * I0
        td_part = uniform(site.tag, salt=salt + '1') * SX * cos(time)
        return static_part + td_part

    fsyst_time = make_td_system(lat, N, td_onsite_time).finalized()
    fsyst_zeit = make_td_system(lat, N, td_onsite_zeit).finalized()

    # the time is named time and starts at zero
    H0_time = fsyst_time.hamiltonian_submatrix(params={'time': 0, 'salt': '1'})
    # the scipy.sparse.linalg.eigsh routine is not re-entrant
    evals_time, evecs_time = np.linalg.eigh(H0_time)
    psi_st_time = evecs_time[:, 0]
    E_time = evals_time[0]

    psi_time = WaveFunction.from_kwant(syst=fsyst_time, params={'salt': '1'},
                                       psi_init=psi_st_time, energy=E_time,
                                       solver_type=solver_type, kernel_type=kernel_type)

    assert psi_time.time == 0
    assert psi_time.time_start == 0
    assert psi_time.time_name == 'time'

    # the time is named zeit and starts at 42
    H0_zeit = fsyst_zeit.hamiltonian_submatrix(params={'zeit': zeit_offset, 'salt': '1'})
    evals_zeit, evecs_zeit = np.linalg.eigh(H0_zeit)
    psi_st_zeit = evecs_zeit[:, 0]
    E_zeit = evals_zeit[0]

    psi_zeit = WaveFunction.from_kwant(syst=fsyst_zeit, params={'salt': '1'},
                                       psi_init=psi_st_zeit, energy=E_zeit,
                                       solver_type=solver_type, kernel_type=kernel_type,
                                       time_name='zeit', time_start=zeit_offset)

    assert psi_zeit.time == zeit_offset
    assert psi_zeit.time_start == zeit_offset
    assert psi_zeit.time_name == 'zeit'

    # check that initial condition is similar
    assert np.allclose(psi_st_time, psi_st_zeit)
    assert E_time == E_zeit

    for time in (0., 1., 5.):
        psi_time.evolve(time)
        psi_zeit.evolve(time + zeit_offset)

        assert psi_time.time_start == 0
        assert psi_zeit.time_start == zeit_offset
        assert psi_time.time == time
        assert psi_zeit.time == time + zeit_offset

        assert np.allclose(psi_time.psi(), psi_zeit.psi())

    for t0 in [1 + 1j, 'a', None, -float('inf'), float('inf')]:
        with pytest.raises(TypeError) as exc:
            WaveFunction.from_kwant(syst=fsyst_time, params={'salt': '1'},
                                    psi_init=psi_st_time, energy=E_time,
                                    solver_type=solver_type, kernel_type=kernel_type,
                                    time_start=t0)
        assert str(exc.value) == "time must be a finite real number"


@pytest.mark.integtest
def test_time_name_and_start_default_change_scattering_state():
    N = 10
    lat = kwant.lattice.square(norbs=2)
    I0 = ta.identity(2)
    SZ = ta.array([[1, 0], [0, -1]])
    uniform = kwant.digest.uniform

    # test only for one lead/mode pair, as calculations are expensive
    tmax = 100
    lead = 0
    mode = 0
    energy = 1
    params = {'salt': '1'}

    def td_onsite_time(site, time, salt):
        static_part = (4 + uniform(site.tag, salt=salt)) * I0
        td_part = SZ * sin(time)
        return static_part + td_part

    def phi_time(time, salt):
        return (1 - cos(time)) * ta.array([1, -1])  # diagonal part

    zeit_offset = 42  # the initial time

    def td_onsite_zeit(site, zeit, salt):
        time = zeit - zeit_offset
        static_part = (4 + uniform(site.tag, salt=salt)) * I0
        td_part = SZ * sin(time)
        return static_part + td_part

    def phi_zeit(zeit, salt):
        time = zeit - zeit_offset
        return (1 - cos(time)) * ta.array([1, -1])  # diagonal part

    ### test when adding time-dependent voltage everywhere
    syst = make_td_system_with_leads(lat, N, make_simple_lead, td_onsite_time)
    leads.add_voltage(syst, 0, phi_time)
    leads.add_voltage(syst, 1, phi_time)
    fsyst_time = syst.finalized()

    syst = make_td_system_with_leads(lat, N, make_simple_lead, td_onsite_zeit)
    leads.add_voltage(syst, 0, phi_zeit)
    leads.add_voltage(syst, 1, phi_zeit)
    fsyst_zeit = syst.finalized()

    # default
    states_time = ScatteringStates(fsyst_time, energy, lead, tmax, params=params)
    state_time = states_time[mode]

    assert state_time.time == 0
    assert state_time.time_start == 0
    assert state_time.time_name == 'time'

    # changed
    WaveFunction_zeit = ft.partial(WaveFunction.from_kwant, time_name='zeit',
                                   time_start=zeit_offset)

    states_zeit = ScatteringStates(fsyst_zeit, energy, lead, tmax, params=params,
                                   wavefunction_type=WaveFunction_zeit)
    state_zeit = states_zeit[mode]

    assert state_zeit.time == zeit_offset
    assert state_zeit.time_start == zeit_offset
    assert state_zeit.time_name == 'zeit'

    for time in (0., 1., 5.):
        state_time.evolve(time)
        state_zeit.evolve(time + zeit_offset)

        assert state_time.time_start == 0
        assert state_zeit.time_start == zeit_offset
        assert state_time.time == time
        assert state_zeit.time == time + zeit_offset

        assert np.allclose(state_time.psi(), state_zeit.psi())

    for t0 in [1 + 1j, 'a', None, -float('inf'), float('inf')]:
        WaveFunction_zeit = ft.partial(WaveFunction.from_kwant, time_name='zeit', time_start=t0)
        with pytest.raises(TypeError) as exc:
            ScatteringStates(fsyst_zeit, energy, lead, tmax, params=params,
                             wavefunction_type=WaveFunction_zeit)
        assert str(exc.value) == "time must be a finite real number"


def test_wavefunction_from_hamiltonian():
    def create_system(L):

        # system building
        lat = kwant.lattice.square(a=1, norbs=1)
        syst = kwant.Builder()

        # central scattering region
        syst[(lat(x, 0) for x in range(L))] = 1
        syst[lat.neighbors()] = -1

        return syst

    num_sites = 400
    syst = create_system(num_sites).finalized()

    # lattice sites and time steps
    xi = np.arange(num_sites)
    times = np.arange(0, 600, 50)

    # initial condition
    k = np.pi / 6
    psi_init = np.exp(- 0.001 * (xi - 100)**2 + 1j * k * xi)

    # hamiltonian matrix
    diag = np.ones(len(xi))
    offdiag = - np.ones(len(xi) - 1)
    H0 = scipy.sparse.diags([diag, offdiag, offdiag],
                            [0, 1, -1])

    H0_kwant = syst.hamiltonian_submatrix(params={'time': 0}, sparse=True)

    assert_array_almost_equal(H0.todense(), H0_kwant.todense())

    wave_func = WaveFunction(H0, W=None, psi_init=psi_init)

    wave_func_kwant = WaveFunction.from_kwant(syst, psi_init)

    for time in times:
        wave_func.evolve(time)
        wave_func_kwant.evolve(time)
        psi = wave_func.psi()
        psi_kwant = wave_func_kwant.psi()
        assert_array_almost_equal(psi, psi_kwant)


def test_wavefunction_from_hamiltonian_raises():
    num_sites = 400

    # lattice sites and time steps
    xi = np.arange(num_sites)

    # initial condition
    k = np.pi / 6
    psi_init = np.exp(- 0.001 * (xi - 100)**2 + 1j * k * xi)

    # hamiltonian matrix which is too small
    diag = np.ones(len(xi) - 1)
    offdiag = - np.ones(len(xi) - 2)
    H0 = scipy.sparse.diags([diag, offdiag, offdiag], [0, 1, -1])

    with pytest.raises(ValueError) as exc:
        WaveFunction(H0, W=None, psi_init=psi_init)
    assert 'initial condition size=400 is larger than the Hamiltonian matrix H0 size=399' in str(exc.value)

    # hamiltonian matrix
    diag = np.ones(len(xi) - 1)
    offdiag = - np.ones(len(xi) - 2)
    H0 = scipy.sparse.diags([diag, offdiag, offdiag], [0, 1, -1])

    # perturbation which is too small
    diag = np.ones(len(xi))
    offdiag = - np.ones(len(xi) - 1)
    H0 = scipy.sparse.diags([diag, offdiag, offdiag], [0, 1, -1])

    def W(*args, **kwargs):
        pass
    W.size = num_sites - 1

    with pytest.raises(ValueError) as exc:
        WaveFunction(H0, W, psi_init=psi_init)
    assert 'initial condition size=400 must be equal to the perturbation W size=399' in str(exc.value)
