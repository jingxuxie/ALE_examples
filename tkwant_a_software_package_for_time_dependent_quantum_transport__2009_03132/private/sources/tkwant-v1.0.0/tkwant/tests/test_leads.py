# -*- coding: utf-8 -*-
# Copyright 2016-2019 tkwant authors.
#
# This file is part of tkwant.  It is subject to the license terms in the file
# LICENSE.rst found in the top-level directory of this distribution and at
# http://kwant-project.org/license.  A list of tkwant authors can be found in
# the file AUTHORS.rst at the top-level directory of this distribution and at
# http://kwant-project.org/authors.

"""Test module for `tkwant.leads`"""

import pytest
from pytest import raises
import cmath
import tinyarray as ta
import numpy as np
import kwant
from numpy.testing import (assert_array_almost_equal, assert_almost_equal)

from .. import leads
from .common import (make_square, make_square_with_leads, make_simple_lead,
                     make_complex_lead, check_boundary_hamiltonian)

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)


def test_make_time_dependent_hopping():

    def phase(a, b, time):
        return time * a + b

    a_ = 2
    b_ = 3
    c_ = 5
    d_ = -2
    time_ = 10
    ii_ = - 2
    jj_ = - 1
    exp_factor = cmath.exp(1j * phase(a=a_, b=b_, time=time_))

    # hopping is a constant
    old_hopping = -5 + 2 * 1j

    new_hopping = leads._make_time_dependent_hopping(phase, old_hopping, system_to_lead=True)
    signature = kwant._common.get_parameters(new_hopping)
    assert signature == ('_site0_', '_site1_', 'a', 'b', 'time')
    assert new_hopping(None, None, a_, b_, time_) == exp_factor * old_hopping

    new_hopping = leads._make_time_dependent_hopping(phase, old_hopping, system_to_lead=False)
    signature = kwant._common.get_parameters(new_hopping)
    assert signature == ('_site0_', '_site1_', 'a', 'b', 'time')
    assert new_hopping(None, None, a_, b_, time_) == exp_factor.conjugate() * old_hopping

    # hopping is callable
    def old_hopping(ii, jj, c, time, d, a):
        return ii + jj + time * c - d * a

    old_hop_eval = old_hopping(ii=ii_, jj=jj_, c=c_, time=time_, d=d_, a=a_)

    new_hopping = leads._make_time_dependent_hopping(phase, old_hopping, system_to_lead=True)
    signature = kwant._common.get_parameters(new_hopping)
    assert signature == ('ii', 'jj', 'c', 'time', 'd', 'a', 'b')
    assert new_hopping(ii_, jj_, c_, time_, d_, a_, b_) == exp_factor * old_hop_eval

    new_hopping = leads._make_time_dependent_hopping(phase, old_hopping, system_to_lead=False)
    signature = kwant._common.get_parameters(new_hopping)
    assert signature == ('ii', 'jj', 'c', 'time', 'd', 'a', 'b')
    assert new_hopping(ii_, jj_, c_, time_, d_, a_, b_) == exp_factor.conjugate() * old_hop_eval


def test_add_voltage():
    N = 3

    def check_square_lead(syst, hop_expect, lat, args=()):
        # check lead cell was added and interface was updated
        new_cell = set(lat(-1, j) for j in range(N))
        # print([site in syst for site in new_cell])
        assert all(site in syst for site in new_cell)
        assert new_cell == set(syst.leads[0].interface)
        # test value
        hops = [(lat(-1, j), lat(0, j)) for j in range(N)]
        check_hops(syst, hops, hop_expect, args)

    def check_hops(syst, hops, hop_expect, args=()):
        for hop in hops:
            for time in (0,):  # (-1, 0, 1):
                got = syst[hop](*(hop + (time,) + args))
                expected = hop_expect(time, *args)
                assert np.allclose(got, expected)
                rhop = tuple(reversed(hop))
                rgot = syst[rhop](*(rhop + (time,) + args))
                rexpected = expected.conjugate()
                assert np.allclose(rgot, rexpected)

    def raises_ValueError(t):
        raise ValueError('problem in phase function')

    def bad_return_value(t):
        return 'nonsense'

    def bad_return_shape(t):
        return np.eye(2)  # expecting scalar

    def phase(t):
        return t

    def simple_hop(t):
        return -1 * cmath.exp(1j * phase(t))  # hopping should be

    # --- input errors
    lat, syst = make_square(N)
    lead = kwant.Builder(kwant.TranslationalSymmetry((-1, 0)))
    lead[(lat(0, j) for j in range(N))] = 2
    lead[lat.neighbors()] = -1
    # hopping > nearest neighbor lead cell
    lead[kwant.builder.HoppingKind((2, 0), lat)] = -1
    interface = [lat(0, j) for j in range(1, N)]
    syst.leads.append(kwant.builder.BuilderLead(lead, interface))
    # add an extra site sticking out and manually attach lead on right
    # interface contains sites in different domains: error!
    syst[lat(N, 0)] = 4
    lead = kwant.Builder(kwant.TranslationalSymmetry((1, 0)))
    lead[(lat(0, j) for j in range(N))] = 2
    lead[lat.neighbors()] = -1
    interface = [lat(N, 0)] + [lat(N - 1, j) for j in range(1, N)]
    syst.leads.append(kwant.builder.BuilderLead(lead, interface))

    with pytest.raises(ValueError) as exc:
        leads.add_voltage(syst, 0, None)
    assert str(exc.value) == 'Phase function is not callable'
    with pytest.raises(ValueError) as exc:
        leads.add_voltage(syst, 0, phase)
    assert 'hopping connects non-neighboring' in str(exc.value)
    with pytest.raises(ValueError) as exc:
        leads.add_voltage(syst, 1, phase)
    assert str(exc.value) == 'Some interface sites belong to different domains'

    # --- test when Hamiltonian is constants
    lat, syst = make_square_with_leads(N)
    added = leads.add_voltage(syst, 0, phase)
    new_hop = (lat(-1, 0), lat(0, 0))  # one new hopping -- system *to* lead
    check_square_lead(syst, simple_hop, lat)
    # check correct sites are added
    assert set(added) == set(lat(-1, j) for j in range(N))
    #  phase function returns numpy scalar
    lat, syst = make_square_with_leads(N)
    leads.add_voltage(syst, 0, lambda time: np.array(phase(time)))
    check_square_lead(syst, simple_hop, lat)
    # user phase function raises error
    lat, syst = make_square_with_leads(N)
    leads.add_voltage(syst, 0, raises_ValueError)
    with pytest.raises(RuntimeError) as ctx:
        syst[new_hop](*(new_hop + (0.,)))
    msg = ('Error while evaluating user-supplied phase function '
           '"raises_ValueError": problem in phase function')
    assert str(ctx.value) == msg
    # user phase function returns nonsense
    lat, syst = make_square_with_leads(N)
    leads.add_voltage(syst, 0, bad_return_value)
    with pytest.raises(RuntimeError) as ctx:
        syst[new_hop](*(new_hop + (5.,)))  # should raise RuntimeError
    msg = ('Error while evaluating user-supplied phase function '
           '"bad_return_value"')
    assert msg in str(ctx.value)

    # --- test when Hamiltonian is functions
    def phase(t, arg):
        return t

    def simple_hop(t, arg):
        return -1 * cmath.exp(1j * phase(t, arg))

    lat, syst = make_square_with_leads(N, functional=True)
    leads.add_voltage(syst, 0, phase=phase)
    check_square_lead(syst, simple_hop, lat, args=(None,))

    # --- matrix onsite structure
    sigma_z = ta.array([[1, 0], [0, -1]])

    def phase_mat(t):
        return t * ta.array((1, -1))

    def mat_hop(t):
        return np.dot(np.diag(np.exp(1j * phase_mat(t))), -sigma_z)

    def trivial_phase(t):
        return t

    def trivial_hop(t):
        return np.dot(cmath.exp(1j * trivial_phase(t)), -sigma_z)

    def test_mat(phase, should_be):
        lat, syst = make_square_with_leads(N, norbs=2,
                                           mat=lambda n: sigma_z)
        leads.add_voltage(syst, 0, phase=phase)
        check_square_lead(syst, should_be, lat)

    # check when return value is 1D sequence -- the diagonal
    test_mat(phase_mat, mat_hop)
    # check when return value is true scalar
    test_mat(trivial_phase, trivial_hop)
    # check when return value is numpy scalar
    test_mat(lambda t: np.array(trivial_phase(t)), trivial_hop)

    # --- nontrivial leads
    def expected(time):
        return np.dot(np.diag(np.exp(1j * phase_mat(time))), 1j * sigma_z)

    lat, syst = make_square(N, norbs=2)
    lead = kwant.Builder(kwant.TranslationalSymmetry((-2, 0)))
    tags = ((0, 1), (1, 2), (1, 0))
    lead[(lat(*t) for t in tags)] = 4 * sigma_z
    lead[lat.neighbors(2)] = -np.eye(2)
    lead2 = kwant.Builder(kwant.TranslationalSymmetry((2, 0)))
    lead2.update(lead)
    # hoppings in different directions to test different code paths
    lead[(lat(0, 1), lat(1, 2))] = 1j * sigma_z
    lead[(lat(1, 0), lat(0, 1))] = -1j * sigma_z
    syst.attach_lead(lead)
    leads.add_voltage(syst, 0, phase_mat)
    new_hops = ((lat(-2, 1), lat(-1, 0)), (lat(-2, 1), lat(-1, 2)))
    check_hops(syst, new_hops, expected)
    # functional hoppings to test all code paths
    lead2[(lat(0, 1), lat(-1, 2))] = lambda i, j, t: 1j * sigma_z
    lead2[(lat(-1, 0), lat(0, 1))] = lambda i, j, t: -1j * sigma_z
    syst.attach_lead(lead2)
    leads.add_voltage(syst, 1, phase_mat)
    new_hops = ((lat(4, 1), lat(3, 0)), (lat(4, 1), lat(3, 2)))
    check_hops(syst, new_hops, expected)


@pytest.mark.parametrize('lead_maker', [make_simple_lead, make_complex_lead])
def test_free_boundary(lead_maker):

    # test invalid construction
    pytest.raises(ValueError, leads.SimpleBoundary, 0)
    pytest.raises(ValueError, leads.SimpleBoundary, -1)
    pytest.raises(ValueError, leads.SimpleBoundary, num_cells=0)
    pytest.raises(ValueError, leads.SimpleBoundary, num_cells=-1)
    pytest.raises(ValueError, leads.SimpleBoundary, tmax=0)
    pytest.raises(ValueError, leads.SimpleBoundary, tmax=-1)
    pytest.raises(TypeError, leads.SimpleBoundary)
    pytest.raises(TypeError, leads.SimpleBoundary, num_cells=2, tmax=2)

    ncells = 10
    lead = lead_maker(kwant.lattice.square(norbs=1)).finalized()
    norbs = lead.cell_size  # 1 orbital per site
    norbs_iface = lead.graph.num_nodes - lead.cell_size  # 1 orbital per site
    # ord=2 gives us the spectral norm
    tmax = ncells / (2 * np.linalg.norm(lead.inter_cell_hopping(), ord=2))
    eps = 1.1  # 1E-8  # boundary valid up to time = tmax + 1 instead tmax

    bdies = [((ncells,), {}), ((), dict(num_cells=ncells)),
             ((), dict(tmax=tmax))]

    for bdy in (leads.SimpleBoundary(*args, **kwargs) for args, kwargs in bdies):
        evald_bdy = bdy(lead)
        # check format of return arguments
        assert evald_bdy.from_slices == [ta.array([0, norbs])]
        assert evald_bdy.to_slices == [ta.array([0, norbs])]
        assert evald_bdy.solution_is_valid(None)
        assert evald_bdy.time_is_valid(tmax - eps)
        assert not evald_bdy.time_is_valid(tmax + eps)
        # check produced Hamiltonian
        check_boundary_hamiltonian(
            evald_bdy.hamiltonian, norbs, norbs_iface,
            lambda i: lead.cell_hamiltonian(),
            lambda i: lead.inter_cell_hopping())


@pytest.mark.parametrize('nbuffer_cells', [-1, 0, 10])
def test_monomial_absorbing_boundary(nbuffer_cells):
    ncells = 10
    strength = 10
    degree = 6
    lead = make_simple_lead(kwant.lattice.square(norbs=1)).finalized()
    norbs = lead.cell_size  # 1 orbital per site
    norbs_iface = lead.graph.num_nodes - lead.cell_size  # 1 orbital per site

    pytest.raises(ValueError, leads.MonomialAbsorbingBoundary,
                  0, strength, degree, num_buffer_cells=0)
    pytest.raises(ValueError, leads.MonomialAbsorbingBoundary,
                  ncells, strength, -1, num_buffer_cells=0)

    if nbuffer_cells < 0:
        pytest.raises(ValueError, leads.MonomialAbsorbingBoundary,
                      ncells, strength, degree, num_buffer_cells=nbuffer_cells)
        return
    else:
        bdy = leads.MonomialAbsorbingBoundary(ncells, strength, degree,
                                              num_buffer_cells=nbuffer_cells)

    evald_bdy = bdy(lead)

    # check format of return arguments
    assert evald_bdy.from_slices == [ta.array([0, norbs])]
    assert evald_bdy.to_slices == [ta.array([0, norbs])]
    assert evald_bdy.solution_is_valid(None)
    assert evald_bdy.time_is_valid(float('inf'))

    # check produced Hamiltonian

    def absorbing(i):
        if i < nbuffer_cells:
            return 0
        else:
            i = i - nbuffer_cells
            n = degree
            return -1j * np.eye(norbs) * ((n + 1) * strength *
                                          i**n / ncells**(n + 1))

    check_boundary_hamiltonian(
        evald_bdy.hamiltonian, norbs, norbs_iface,
        lambda i: lead.cell_hamiltonian() + absorbing(i),
        lambda i: lead.inter_cell_hopping())

# ---


def test_generic_absorbing_boundary():
    # test that hamiltonian is the same, if we construct our generic
    # boundary condition with the same monomial function that is
    # implemented in MonomialAbsorbingBoundary
    lead = make_simple_lead(kwant.lattice.square(norbs=1)).finalized()
    num_cells, buffer_cells, strength, degree = 100, 40, 14.5, 6

    sigma = leads._monomial_absorbing_potential(strength, degree)
    boundary_1 = leads.GenericAbsorbingBoundary(num_cells, sigma, buffer_cells)
    boundary_2 = leads.MonomialAbsorbingBoundary(num_cells, strength, degree, buffer_cells)

    h1 = boundary_1(lead).hamiltonian
    h2 = boundary_2(lead).hamiltonian
    assert np.allclose(h1.A, h2.A)


def test_absorbing_reflection_solver():
    # create explicitly a system with an imaginary monomial potential
    # and check that this gives the same reflection as by the reflection
    # solver that takes only a lead

    def create_system(L, W=1, a=1):
        gamma = 1 / a**2

        def aborbing_potential(site, strength, degree):
            x = site.pos[0]
            return - 1j / L * (degree + 1) * strength * (x / L)**degree

        def onsite(site, strength, degree):
            return 2 * gamma + aborbing_potential(site, strength, degree)

        lat = kwant.lattice.square(a=a, norbs=1)
        syst = kwant.Builder()
        syst[(lat(x, y) for x in range(L) for y in range(W))] = onsite
        syst[lat.neighbors()] = -gamma
        lead = kwant.Builder(kwant.TranslationalSymmetry((-a, 0)))
        lead[(lat(0, y) for y in range(W))] = 2 * gamma
        lead[lat.neighbors()] = -gamma
        syst.attach_lead(lead)
        return syst

    L = 30
    strength = 10
    degree = 4

    syst = create_system(L, W=2).finalized()
    band = kwant.physics.Bands(syst.leads[0])

    # introduce some small epsilon to avoid energies close to band openings
    eps = 0.0001
    energies = band(0)[0] + np.logspace(np.log10(eps), np.log10(2 - eps), 48)

    # take a lead, add the imaginary potential and calculate reflection
    # note that the system syst is not involved in this calculation but only the lead
    sigma = leads._monomial_absorbing_potential(strength, degree)

    reflection_solver = leads.AbsorbingReflectionSolver(syst.leads[0], L, sigma)
    refl = [reflection_solver(energy)[0][0] for energy in energies]

    # take the system with an imaginary potential and calculate reflection
    # note that the lead is not involved in this calculation but only syst
    def reflection(syst, E, A, n):
        return np.sqrt(kwant.smatrix(syst, E, check_hermiticity=False,
                                     params={'strength': A, 'degree': n}).transmission(0, 0))
    refl_ref = [reflection(syst, energy, strength, degree) for energy in energies]

    assert_array_almost_equal(refl, refl_ref)

    # check exceptions
    lead = syst.leads[0]
    not_a_lead = []
    not_callable = 1
    raises(TypeError, leads.AbsorbingReflectionSolver, not_a_lead, L, sigma)
    raises(ValueError, leads.AbsorbingReflectionSolver, lead, - L, sigma)
    raises(ValueError, leads.AbsorbingReflectionSolver, lead, L, not_callable)


def test_reflection_calculation():

    lead = make_simple_lead(kwant.lattice.square(norbs=1)).finalized()
    bands = kwant.physics.Bands(lead)
    num_cells, strength, degree = 100, 14.5, 6
    imaginary_potential = leads._monomial_absorbing_potential(strength, degree)

    not_callable = 1
    not_a_lead = []
    non_existing_band = 5  # band index too high

    # -------------------------------------------------------------------
    # --- reflection from energy with AbsorbingReflectionSolver
    # -------------------------------------------------------------------
    refl_solver = leads.AbsorbingReflectionSolver(lead, num_cells, imaginary_potential)

    # check for scalar energy value
    momenta, mode = 2., 0
    energies, velocities = bands(momenta, derivative_order=1)
    energies = energies[mode]
    velocities = velocities[mode]

    refl, k, vel = refl_solver(energies)
    assert_array_almost_equal(refl, [0.70653482])  # precalculated value
    assert_array_almost_equal(k, momenta)
    assert_array_almost_equal(vel, velocities)
    # check for array of energies
    energies = [0, 2.5]
    refl, k, vel = refl_solver(energies)
    # check reflection
    refl0 = [[0.59570332], [0.53411935, 0.56524117]]  # precalculated value
    [assert_array_almost_equal(i, i0) for i, i0 in zip(refl, refl0)]
    # check momenta
    k0 = lead.modes(energy=energies[0])[0].momenta[1]
    k1 = lead.modes(energy=energies[1])[0].momenta[2:]
    momenta = [k0, k1]
    [assert_array_almost_equal(i, i0) for i, i0 in zip(k, momenta)]
    # check velocities
    v0 = lead.modes(energy=energies[0])[0].velocities[1]
    v1 = lead.modes(energy=energies[1])[0].velocities[2:]
    velocities = [v0, v1]
    [assert_array_almost_equal(i, i0) for i, i0 in zip(vel, velocities)]

    # check for scalar energy value where no modes are open
    refl, k, vel = refl_solver(energies=10)
    assert refl.size == 0
    assert k.size == 0
    assert vel.size == 0

    # check for an array of energy value where only parts of the modes are open
    energies = [-5, 0.5, 3, 4.5, 11.0]
    refl, k, vel = refl_solver(energies)
    number_pos_modes = [len(lead.modes(energy=e)[0].momenta) // 2 for e in energies]
    assert np.array([r.size == i for r, i in zip(refl, number_pos_modes)]).all()
    assert np.array([r.size == i for r, i in zip(k, number_pos_modes)]).all()
    assert np.array([r.size == i for r, i in zip(vel, number_pos_modes)]).all()

    # check exeptions
    raises(TypeError, leads.AbsorbingReflectionSolver, not_a_lead, num_cells, imaginary_potential)
    raises(ValueError, leads.AbsorbingReflectionSolver, lead, - num_cells, imaginary_potential)
    raises(ValueError, leads.AbsorbingReflectionSolver, lead, num_cells, not_callable)

    # -------------------------------------------------------------------
    # --- reflection from momentum with AnalyzeReflection
    # -------------------------------------------------------------------
    analyze_reflection = leads.AnalyzeReflection(lead, num_cells, imaginary_potential)
    band = 1

    # check for scalar momentum value
    k = 1
    refl, ener, vel = analyze_reflection(k, band)
    energies, velocities = bands(k, derivative_order=1)
    assert_array_almost_equal(refl, [0.80014401727])  # precalculated value
    assert_array_almost_equal(ener, energies[band])
    assert_array_almost_equal(vel, velocities[band])

    # check for an array of momentum value
    k = [-0.2, 2]
    refl, ener, vel = analyze_reflection(k, band)
    energies = [bands(kk)[band] for kk in k]
    velocities = np.abs([bands(kk, derivative_order=1)[1][band] for kk in k])
    assert_array_almost_equal(refl, [0.56059964, 0.64908466])  # precalculated value
    assert_array_almost_equal(ener, energies)
    assert_array_almost_equal(vel, velocities)

    # calc reflection around minimum
    kmin, kmax = 0.5, 2
    refl, ener, vel, k, e0, k0 = analyze_reflection.around_extremum(kmin, kmax, band, nq=2)
    assert_array_almost_equal(refl, [0.74827915, 0.99892086, 0.99892086, 0.64908466])  # precalculated value
    assert_array_almost_equal(ener, [bands(kk)[band] for kk in k])
    assert_array_almost_equal(vel, np.abs([bands(kk, derivative_order=1)[1][band] for kk in k]))
    assert_almost_equal(e0, bands(k0)[band])

    # check exeptions
    raises(TypeError, leads.AnalyzeReflection, not_a_lead, num_cells, imaginary_potential)
    raises(ValueError, leads.AnalyzeReflection, lead, - num_cells, imaginary_potential)
    raises(ValueError, leads.AnalyzeReflection, lead, num_cells, not_callable)

    raises(AssertionError, analyze_reflection, k, non_existing_band)  # band does not exists

    raises(ValueError, analyze_reflection.around_extremum, 1, 2, band, nq=2)  # no minima inside [1,2]
    raises(AssertionError, analyze_reflection.around_extremum, kmax, kmin, band, nq=2)  # left/right swapped
    raises(AssertionError, analyze_reflection.around_extremum, 0.5, 2, non_existing_band, nq=2)  # band does not exists
    raises(ValueError, analyze_reflection.around_extremum, kmin, kmax, band, nq=-2)  # neg. nb of points
    raises(ValueError, analyze_reflection.around_extremum, kmin, kmax, band, nq=0)  # no points

    # -------------------------------------------------------------------
    # --- reflection from momentum with AnalyzeReflectionMonomial
    # -------------------------------------------------------------------
    analyze_reflection = leads.AnalyzeReflectionMonomial(lead, num_cells, strength, degree)

    # calc reflection around minimum
    kmin, kmax = 0.5, 2
    refl, ener, vel, k, e0, k0 = analyze_reflection.around_extremum(kmin, kmax, band, nq=2)

    assert_array_almost_equal(refl, [4.617257e-08, 1.000000e+00, 1.000000e+00, 7.045444e-05])  # precalculated value
    assert_array_almost_equal(ener, [bands(kk)[band] for kk in k])
    assert_array_almost_equal(vel, [bands(kk, derivative_order=1)[1][band] for kk in k])
    assert_almost_equal(e0, bands(k0)[band])

    # check exeptions
#    raises(TypeError, leads.AnalyzeReflectionMonomial, not_a_lead, num_cells, strength, degree) # TODO
    raises(ValueError, leads.AnalyzeReflectionMonomial, lead, - num_cells, strength, degree)

    raises(ValueError, analyze_reflection.around_extremum, 1, 2, band, nq=2)  # no minima inside
    raises(AssertionError, analyze_reflection.around_extremum, kmax, kmin, band, nq=2)  # left/right swapped
    raises(AssertionError, analyze_reflection.around_extremum, 0.5, 2, non_existing_band, nq=2)  # band does not exists
    raises(ValueError, analyze_reflection.around_extremum, kmin, kmax, band, nq=-2)  # neg. nb of points
    raises(ValueError, analyze_reflection.around_extremum, kmin, kmax, band, nq=0)  # no points

    # TODO: velocity sign not consistent
    # TODO: call signature of Reflection routines not consistent
    # TODO: if energies are empty, we get an error


def test_automatic_boundary():
    # for short times, simple boundary condition is more efficient
    # whereas for long times, the algorithm should select absorbing boundaries

    lead = make_simple_lead(kwant.lattice.square(norbs=1)).finalized()

    # make boundary for a single lead
    boundary = leads.automatic_boundary(lead, tmax=10)[0]
    assert type(boundary) == leads.SimpleBoundary
    boundary = leads.automatic_boundary(lead, tmax=100000)[0]
    assert type(boundary) == leads.MonomialAbsorbingBoundary

    # make boundaries for a list of leads
    _leads = [lead] * 3
    boundaries = leads.automatic_boundary(_leads, tmax=10)
    for boundary in boundaries:
        assert type(boundary) == leads.SimpleBoundary
    boundaries = leads.automatic_boundary(_leads, tmax=100000)
    for boundary in boundaries:
        assert type(boundary) == leads.MonomialAbsorbingBoundary

    # check exceptions
    not_a_lead = []
    tmax = 100000
    raises(TypeError, leads.automatic_boundary, lead=not_a_lead, tmax=tmax)  # not a lead
    raises(ValueError, leads.automatic_boundary, lead, tmax=-tmax)  # negative time
    raises(AssertionError, leads.automatic_boundary, tmax, lead)  # interchanged
    raises(ValueError, leads.automatic_boundary, lead, tmax, refl_max=-0.1)  # negative reflection
    raises(ValueError, leads.automatic_boundary, lead, tmax, degree=-1)  # degree not positive
    raises(ValueError, leads.automatic_boundary, lead, tmax, emin=0.4, emax=0.2)  # emin/emax swapped


def test_automatic_boundary_for_lead_with_flat_band():
    # for short times, simple boundary condition is more efficient
    # whereas for long times, the algorithm should select absorbing boundaries

    # edgecase with tree bands, where the second band is flat but with tiny noise
    def make_lead_with_flat_band(ll=3):
        lat = kwant.lattice.square(norbs=1)
        lead = kwant.Builder(kwant.TranslationalSymmetry((-1, 1)))
        lead[[lat(0, j) for j in range(ll)]] = 0
        lead[lat.neighbors()] = -1
        return lead

    lead = make_lead_with_flat_band().finalized()

    # make simple boundary
    boundary = leads.automatic_boundary(lead, tmax=10)[0]
    assert type(boundary) == leads.SimpleBoundary

    # make absorbing boundary
    boundary = leads.automatic_boundary(lead, tmax=100)[0]
    assert type(boundary) == leads.MonomialAbsorbingBoundary
