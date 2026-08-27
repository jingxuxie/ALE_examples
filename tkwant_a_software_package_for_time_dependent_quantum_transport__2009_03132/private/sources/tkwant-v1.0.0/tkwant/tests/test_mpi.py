# -*- coding: utf-8 -*-
# Copyright 2016-2020 tkwant authors.
#
# This file is part of tkwant.  It is subject to the license terms in the file
# LICENSE.rst found in the top-level directory of this distribution and at
# http://kwant-project.org/license.  A list of tkwant authors can be found in
# the file AUTHORS.rst at the top-level directory of this distribution and at
# http://kwant-project.org/authors.

"""Test module for routines using MPI"""

import pytest
from pytest import raises
import cmath
import numpy as np
import kwant
from numpy.testing import assert_array_almost_equal
from scipy.special import erf
import warnings


from . import mpi_testdriver
from .. import onebody, manybody, system, leads, integration, mpi
import kwantspectrum

pytestmark = pytest.mark.mpitest  # module level marker for mpi tests
num_processes = 4


def make_simple_lead(W=3):
    lat = kwant.lattice.square(a=1, norbs=1)
    sym = kwant.TranslationalSymmetry((-1, 0))
    H = kwant.Builder(sym)
    H[(lat(0, y) for y in range(W))] = 0
    H[lat.neighbors()] = -1
    return H


def onsite_potential(site, time, v):
    return 4 * (1 + v * cmath.exp(- 1j * time))


def gaussian(time):
    t0 = 0
    A = 0.00157
    sigma = 24
    return A * (1 + erf((time - t0) / sigma))


# time dependent coupling with gaussian pulse
def coupling_nn(site1, site2, time):
    return - cmath.exp(- 1j * gaussian(time))


def make_system(a=1, gamma=1.0, W=1, L=30):

    lat = kwant.lattice.square(a=a, norbs=1)
    syst = kwant.Builder()

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


class ManybodyIntegrand:

    def __init__(self, syst, interval, operator, time=0, params=None, element=None):
        """Diagnostic routine to evaluate the integrand in the manybody integral"""

        tparams = system.add_time_to_params(params, time_name='time',
                                            time=0, check_numeric_type=True)

        spectra = kwantspectrum.spectra(syst.leads, params=tparams)
        self.boundaries = leads.automatic_boundary(spectra, tmax=time)

        self.syst = syst
        self.band = interval.band
        self.lead = interval.lead
        self.time = time
        self.operator = operator
        self.params = params
        self.spectrum = spectra[self.lead]
        self.element = element

    def _f(self, k):
        """integrand (momentum integration) for the manybody expectation value
        at zero temperature"""
        energy = self.spectrum(k, band=self.band)
        velocity = self.spectrum(k, band=self.band, derivative_order=1)
        mode = self.spectrum.momentum_to_scattering_mode(k, self.band)

        psi = onebody.ScatteringStates(self.syst, energy=energy, lead=self.lead,
                                       params=self.params,
                                       boundaries=self.boundaries)[mode]

        psi.evolve(self.time)

        result = velocity * psi.evaluate(self.operator) / (2 * np.pi)
        if result.shape == (1,):  # if result is an array with only one element
            result = result[0]
        if self.element is None:
            return result
        return result[self.element]

    def func(self, k):
        return np.array([self._f(xi) for xi in k])


def quadpack_error_per_interval(func, order, ai, bi):

    def calc_ik(x, w, kronrod):
        integrand = np.abs(func(x) - kronrod / (bi - ai))
        return np.sum(w * integrand, axis=1)[1]

    x, w = integration.calc_abscissas_and_weights(ai, bi, order, quadrature='kronrod')

    gauss, kronrod = np.sum(w * func(x), axis=1)
    ik = calc_ik(x, w, kronrod)
    tmp = 200 * np.abs(gauss - kronrod) / ik
    return ik * np.minimum(1, tmp * np.sqrt(tmp))


def quadpack_qag(func, a, b, atol=1.49e-8, rtol=1.49e-8, limit=50, order=5):
    # import sys

    def estimate_interval(ai, bi):
        x, w = integration.calc_abscissas_and_weights(ai, bi, order, quadrature='kronrod')
        return np.sum(w * func(x), axis=1)[1]

    def estimate_full_integral(intervals):
        return [estimate_interval(*interval) for interval in intervals]

    def estimate_errors(intervals):
        return np.array([quadpack_error_per_interval(func, order, *interval)
                         for interval in intervals])

    intervals = [(a, b)]

    i = 1
    while True:  # loop until converged

        # print('cycle {}'.format(i))

        results = estimate_full_integral(intervals)

        result = np.sum(results)

        tol = max(atol, rtol * result)

        errors = estimate_errors(intervals)

        max_error_per_interval = [np.max(error - tol) for error in errors]

        max_index = np.argsort(max_error_per_interval)[::-1]

        intervals = [intervals[i] for i in max_index]
        results = [results[i] for i in max_index]
        errors = errors[max_index]

        # for inte, res, err in zip(intervals, results, errors):
        #     print(inte, float(res), float(err))
        # print('errorsum, errorbnd {} {}'.format(float(np.sum(errors)), tol))
        # sys.stdout.flush()

        if np.where(errors < tol, True, False).all():
            break

        i += 1
        if i > limit:
            warnings.warn('maxdepth for interval refinement exceeded')
            break

        ai, bi = intervals.pop(0)
        mi = (ai + bi) / 2

        intervals.append((ai, mi))
        intervals.append((mi, bi))

    return result, errors, max_error_per_interval, intervals


@mpi_testdriver.wrap(num_processes)
def test_mpi_communicator_init():

    assert mpi._COMM is None
    mpi.communicator_init()
    assert mpi._COMM is not None
    from mpi4py import MPI
    assert MPI.Comm.Compare(mpi._COMM, MPI.COMM_WORLD) == MPI.CONGRUENT

    # check reinitialization
    # TODO: it would be nice if we could check the warning message
    mpi.communicator_init()


@mpi_testdriver.wrap(num_processes)
def test_mpi_communicator_init_with_argument():

    assert mpi._COMM is None

    # split COMM_WORLD in two communicators of half size with colour 0 and 1
    from mpi4py import MPI
    colour = MPI.COMM_WORLD.rank // 2
    key = 0
    new_comm = MPI.COMM_WORLD.Split(colour, key)
    assert new_comm.size == MPI.COMM_WORLD.size / 2

    mpi.communicator_init(new_comm)

    assert mpi._COMM is not None
    assert MPI.Comm.Compare(mpi._COMM, new_comm) == MPI.CONGRUENT
    assert MPI.Comm.Compare(mpi._COMM, MPI.COMM_WORLD) == MPI.UNEQUAL


@mpi_testdriver.wrap(num_processes)
def test_mpi_get_communicator():

    comm = mpi.get_communicator()
    assert comm is not None
    from mpi4py import MPI
    assert MPI.Comm.Compare(comm, MPI.COMM_WORLD) == MPI.CONGRUENT

    # split COMM_WORLD in two communicators of half size with colour 0 and 1
    colour = MPI.COMM_WORLD.rank // 2
    key = 0
    new_comm = MPI.COMM_WORLD.Split(colour, key)
    assert new_comm.size == MPI.COMM_WORLD.size / 2

    # check that passing a communicator only return the same communicator again
    comm_1 = mpi.get_communicator(new_comm)
    assert MPI.Comm.Compare(new_comm, comm_1) == MPI.IDENT

    # check that the tkwant global communicator is still the same
    comm_2 = mpi.get_communicator()

    assert MPI.Comm.Compare(comm_2, comm) == MPI.IDENT
    assert MPI.Comm.Compare(comm_2, MPI.COMM_WORLD) == MPI.CONGRUENT
    assert MPI.Comm.Compare(comm_2, comm_1) == MPI.UNEQUAL


@mpi_testdriver.wrap(num_processes)
def test_mpi_get_communicator_does_not_set_state():

    from mpi4py import MPI
    comm = MPI.COMM_WORLD
    comm_1 = mpi.get_communicator(comm)
    assert MPI.Comm.Compare(comm, comm_1) == MPI.IDENT
    assert mpi._COMM is None


@mpi_testdriver.wrap(num_processes)
def test_mpi_round_robin():

    comm = mpi.get_communicator()
    rank = comm.rank
    size = comm.size

    assert size >= 4

    # test condition: rank == key + m * size

    for key in range(size):  # m = 0
        if rank == key:
            assert mpi.round_robin(comm, key)
        else:
            assert not mpi.round_robin(comm, key)

    for key in range(size, 2 * size):  # m = -1
        if rank == key - size:
            assert mpi.round_robin(comm, key)
        else:
            assert not mpi.round_robin(comm, key)

    for key in range(- size, 0):  # m = 1
        if rank == key + size:
            assert mpi.round_robin(comm, key)
        else:
            assert not mpi.round_robin(comm, key)


@mpi_testdriver.wrap(num_processes)
def test_mpi_distribute_dict():

    comm = mpi.get_communicator()
    rank = comm.rank
    size = comm.size

    assert size >= 4

    non_distributed_dict = {'a': 5, 'b': 8}

    def map_keys_to_ranks(commun, key):
        # map a -> rank 1 and b to rank 0
        if (key == 'a' and commun.rank == 1) or (key == 'b' and commun.rank == 0):
            return True
        return False

    distributed_dict = mpi.distribute_dict(non_distributed_dict,
                                           map_keys_to_ranks, comm)

    assert isinstance(distributed_dict, dict)

    if rank == 0:
        assert [('b', 8)] == list(distributed_dict.items())
    if rank == 1:
        assert [('a', 5)] == list(distributed_dict.items())
    if rank > 1:
        assert len(distributed_dict) == 0


@mpi_testdriver.wrap(num_processes)
def test_distributed_dict():

    comm = mpi.get_communicator()
    rank = comm.rank
    size = comm.size

    assert size >= 4

    if rank == 3:
        data = {'a': 7, 'b': 3.14}
    elif rank == 2:
        data = {'c': 7}
    else:
        data = {}

    non_present_key = 'd'
    non_present_rank = size

    distributed_dict = mpi.DistributedDict(data)

    # add data
    distributed_dict.add(key=5, value=1)  # add data somewhere
    assert set(distributed_dict.keys()) == set(['a', 'b', 'c', 5])
    raises(ValueError, distributed_dict.add, key=5, value=1)  # key exists already
    distributed_dict.add(key=24, value=1, rank=3)  # add data on a specific rank
    assert set(distributed_dict.keys(rank=3)) == set(['a', 'b', 24])
    raises(ValueError, distributed_dict.add, key=24, value=1, rank=3)
    raises(ValueError, distributed_dict.add, key=25, value=1, rank=non_present_rank)

    # delete data
    distributed_dict.delete(key=5)
    assert set(distributed_dict.keys()) == set(['a', 'b', 'c', 24])
    raises(ValueError, distributed_dict.delete, key=non_present_key)

    # get data
    element = distributed_dict.data(key='a')
    assert element == 7
    raises(ValueError, distributed_dict.data, key=non_present_key)

    # get local data
    local_data = distributed_dict.local_data()
    element_inside = [value == local_data[key] for key, value in data.items()]
    assert np.array(element_inside).all()

    # get local keys
    keys = distributed_dict.local_keys()
    if rank == 3:
        assert set(keys) == set(['a', 'b', 24])
    if rank == 2:
        assert set(keys) == set(['c'])

    # get keys
    keys = distributed_dict.keys()  # all keys
    assert isinstance(keys, list)
    assert set(keys) == set(['a', 'b', 'c', 24])
    keys = distributed_dict.keys(rank=3)  # keys on specific ranks
    assert isinstance(keys, list)
    assert set(keys) == set(['a', 'b', 24])
    keys = distributed_dict.keys(rank=2)
    assert isinstance(keys, list)
    assert set(keys) == set(['c'])
    raises(AssertionError, distributed_dict.keys, rank=non_present_rank)

    # get size
    dict_size = distributed_dict.size()  # size on all ranks
    assert isinstance(dict_size, np.ndarray)
    assert (dict_size == [0, 0, 1, 3]).all()
    assert distributed_dict.size(rank=0) == 0  # size on a specific rank
    assert distributed_dict.size(rank=1) == 0
    assert distributed_dict.size(rank=2) == 1
    assert distributed_dict.size(rank=3) == 3
    raises(AssertionError, distributed_dict.size, rank=non_present_rank)

    # move data
    distributed_dict.move_data(key='b', to_rank=2)  # move from rank 3 -> rank 2
    assert set(distributed_dict.keys(rank=3)) == set(['a', 24])
    assert set(distributed_dict.keys(rank=2)) == set(['b', 'c'])
    # distributed_dict.move_data(key='b', to_rank=2)  # move from rank 2 -> rank 2
    # TODO: does not work

    raises(ValueError, distributed_dict.move_data, key=non_present_key, to_rank=2)
    # raises(AssertionError, distributed_dict.move_data, key='a', to_rank=non_present_rank)
    # TODO: get error from mpi4py

    # get rank number
    assert distributed_dict.rank_from_key(key='a') == 3
    assert distributed_dict.rank_from_key(key=24) == 3
    assert distributed_dict.rank_from_key(key='b') == 2
    assert distributed_dict.rank_from_key(key='c') == 2
    raises(ValueError, distributed_dict.rank_from_key, key=non_present_key)

    # check if key is present
    for key in ['a', 'b', 'c', 24]:
        assert distributed_dict.key_is_present(key=key)
    assert not distributed_dict.key_is_present(key='bla')

    # check if keys are unique
    assert distributed_dict.keys_are_unique()
    if rank == 1:
        distributed_dict._data = {'c': 7}  # add data already present on rank 2
    assert not distributed_dict.keys_are_unique()

    # wrong input with dublicated data
    if rank == 3:
        dublicated_data = {'a': 7, 'b': 3.14}
    elif rank == 2:
        dublicated_data = {'b': 3.14}
    else:
        dublicated_data = {}

    raises(ValueError, mpi.DistributedDict, data=dublicated_data)


@mpi_testdriver.wrap(num_processes)
def test_manybody_wavefunction():

    def test_wavefunction(number_energy_points):

        time = 5
        energies = np.linspace(2.1, 3, number_energy_points)

        params = {'v': 0.0001}

        # ------------- test evolve and evaluate --------------------------

        # compute in a non-mpi fashion the manybody density by hand
        # we take a weight for each onebody contribution to be 1 for simplicity
        psis_ref = [onebody.ScatteringStates(syst, energy=energy, lead=0, tmax=50,
                                             params=params)[0]
                    for energy in energies]

        for psi in psis_ref:
            psi.evolve(time)

        density_ref = sum([psi.evaluate(density_operator)
                           for psi in psis_ref])

        # compute the same density with a MPI distributed wavefunction
        class MyTask:
            weight = np.array([1])

        psi_init = {}
        for i, energy in enumerate(energies):
            if rank == i % size:
                psi_init[i] = onebody.ScatteringStates(syst, energy=energy,
                                                       lead=0, tmax=50, params=params)[0]
        tasks = {i: MyTask() for i in range(len(energies))}

        # compare the densities for consistency
        wavefunction = manybody.WaveFunction(psi_init, tasks)
        wavefunction.evolve(time)
        density = wavefunction.evaluate(density_operator)
        if rank == 0:  # evaluate returns only on rank 0
            assert_array_almost_equal(density, density_ref)

        # --------------------- test _calc_expectation_value --------------
        # over all keys
        density = wavefunction._calc_expectation_value(density_operator)
        if rank == 0:  # _calc_expectation_value returns only on rank 0
            assert_array_almost_equal(density, density_ref)
        # partial evaluate over a subset of keys
        keys = np.array(list(tasks.keys()))[1::2]
        if len(keys) > 0:
            density = wavefunction._calc_expectation_value(density_operator, keys=keys)
            density_ref = sum([psis_ref[key].evaluate(density_operator) for key in keys])
            if rank == 0:  # _calc_expectation_value returns only on rank 0
                assert_array_almost_equal(density, density_ref)

        # --------------------- test get onebody state-----------------------
        for key in range(len(energies)):
            psi = wavefunction.get_onebody_state(key)
            psi_ref = psis_ref[key]
            assert np.allclose(psi.psi(), psi_ref.psi())

        # --------------------- test to add onebody state---------------------
        new_energy = 2.37423  # some arbitray number where one open mode exists
        new_state = onebody.ScatteringStates(syst, energy=new_energy, lead=0, tmax=50, params=params)[0]

        psis_ref.append(new_state)
        time += 5
        for psi in psis_ref:
            psi.evolve(time)
        density_ref = sum([psi.evaluate(density_operator) for psi in psis_ref])

        new_key = wavefunction.add_onebody_state(state=new_state, task=MyTask)
        new_state = None  # delete in order to make sure that we have not created any hidden reference
        wavefunction.evolve(time)
        density = wavefunction.evaluate(density_operator)
        if rank == 0:  # evaluate returns only on rank 0
            assert_array_almost_equal(density, density_ref)

        assert isinstance(new_key, int)
        assert new_key == number_energy_points

        new_state = onebody.ScatteringStates(syst, energy=new_energy, lead=0, tmax=50, params=params)[0]
        new_key = wavefunction.add_onebody_state(state=new_state, task=MyTask, key='bla')
        assert new_key == 'bla'

        raises(ValueError, wavefunction.add_onebody_state,
               state=new_state, task=MyTask, key='bla')  # key exists already

        # ----------------- test to delete onebody state--------------------
        wavefunction.delete_onebody_state(key='bla')
        raises(ValueError, wavefunction.delete_onebody_state, key='bla')  # already deleted

        # -------------------- get all keys----------------------------
        keys = wavefunction.get_keys()
        assert isinstance(keys, list)
        assert set(keys) == set(range(number_energy_points + 1))  # we have added one state above

        # --------------------  get a free key--------------------
        assert wavefunction.get_free_key() == number_energy_points + 1
        wavefunction.add_onebody_state(state=new_state, task=MyTask, key='bla')
        assert wavefunction.get_free_key() == number_energy_points + 1
        wavefunction.add_onebody_state(state=new_state, task=MyTask, key=number_energy_points + 5)
        assert wavefunction.get_free_key() == number_energy_points + 6

        # --------------------  test weight shape--------------------
        assert wavefunction.weight_shape() == (1, )

        # --------------------  test consistency--------------------
        assert wavefunction._check_consistency()
        del wavefunction.tasks[0]
        assert not wavefunction._check_consistency()

    comm = mpi.get_communicator()
    rank = comm.rank
    size = comm.size
    assert size > 1

    syst = make_system().finalized()
    density_operator = kwant.operator.Density(syst)

    # test for consistency in the case that we have less, equal, or more
    # modes that MPI ranks
    test_wavefunction(number_energy_points=size // 2)
    test_wavefunction(number_energy_points=size)
    test_wavefunction(number_energy_points=size + size // 2)


@mpi_testdriver.wrap(num_processes)
def test_manybody_state():

    comm = mpi.get_communicator()
    rank = comm.rank
    assert comm.size > 1

    syst = make_system().finalized()
    density_operator = kwant.operator.Density(syst)

    tmax = 50
    time = 5
    params = {'v': 0.0001}

    occupation = manybody.lead_occupation(chemical_potential=3)

    # manybody solver
    state = manybody.State(syst, tmax, occupation, params=params, refine=False)

    # check that result is similar to reference result
    state.evolve(time)

    # -- test refine_intervals
    error_before = state.estimate_error()
    state.refine_intervals(atol=1E-3, rtol=1E-3)
    error_after = state.estimate_error()
    assert error_after < error_before

    density = state.evaluate(density_operator)

    # get the tasks and recalculate non-mpi the same
    tasks = [task for _, task in state.manybody_wavefunction.tasks.items()]
    psis_ref = [onebody.ScatteringStates(syst, energy=task.energy,
                                         lead=task.lead, tmax=tmax, params=params)[task.mode]
                for task in tasks]

    for psi in psis_ref:
        psi.evolve(time)

    density_ref = sum([task.weight[-1] * psi.evaluate(density_operator)
                       for task, psi in zip(tasks, psis_ref)])

    if rank == 0:  # evaluate returns only on rank 0
        assert_array_almost_equal(density, density_ref)


@mpi_testdriver.wrap(num_processes)
def test_quadpack_error_estimate():

    comm = mpi.get_communicator()
    assert comm.size > 1

    syst = make_system().finalized()

    element = 10  # the site where do we want to compare the error

    def site_pos(site):
        return site.pos[0] == element

    density_operator = kwant.operator.Density(syst, where=site_pos)  # operator with only one element
    density_operator_array = kwant.operator.Density(syst)  # operator with array output

    time = 5
    tmax = time
    params = {'v': 0.0001}
    occupation = manybody.lead_occupation(chemical_potential=3)

    state = manybody.State(syst, tmax, occupation, params=params, refine=False)

    # estimate the error at a given time in the first interval for a given element
    intervals = state.get_intervals()
    interval = intervals[0]

    state.evolve(time)

    # compare if array valued operator and single-valued operator give the same result
    error = state._error_estimate_quadpack(interval=interval, error_op=density_operator)

    error_array = state._error_estimate_quadpack(interval=interval,
                                                 error_op=density_operator_array)

    assert np.allclose(error, error_array[element])

    # compare the error to the quadpack reference implementation
    integrand = ManybodyIntegrand(syst, interval=interval, time=time, params=params,
                                  operator=density_operator)

    reference_error = quadpack_error_per_interval(integrand.func, interval.order,
                                                  interval.kmin, interval.kmax)

    assert np.allclose(error, reference_error)


@mpi_testdriver.wrap(num_processes)
def test_quadpack_adaptive_refinement_of_manybody_state():

    # we test the adaptive refinement against a simple reference implementation
    # (scipy quadpack does not implement the QAG, but only the QAGS algorithm)
    # moreover, we test our routine for two different operators.
    # first, a density operator where we measure the density at only one site,
    # such that the density has a scalar value.
    # second a density operator, where the density is site dependent. to compare
    # both cases, we set the array density to the scalar density value everywhere
    # the result should both match the scalar, as well as the reference result

    comm = mpi.get_communicator()
    assert comm.size > 1

    syst = make_system().finalized()

    element = 10  # the site where do we want to compare the error

    def site_pos(site):
        return site.pos[0] == element

    density_operator = kwant.operator.Density(syst, where=site_pos)  # operator with only one element
    density_operator_array = kwant.operator.Density(syst)  # operator with array output

    def make_operator(operator):
        """make an operator where all elements are equal **element**"""
        def homogene(*args, **kwargs):
            expectation = operator(*args, **kwargs)
            expectation.fill(expectation[element])
            return expectation
        if hasattr(operator, '_bound_onsite'):
            homogene._bound_onsite = operator._bound_onsite
        if hasattr(operator, '_bound_hamiltonian'):
            homogene._bound_hamiltonian = operator._bound_hamiltonian
        return homogene

    # this operator has an array like output, on all sites the value is similar to
    # the density operator
    density_operator_array = make_operator(density_operator_array)

    time = 5
    tmax = time
    params = {'v': 0.0001}
    occupation = manybody.lead_occupation(chemical_potential=3)

    state = manybody.State(syst, tmax, occupation, params=params, refine=False)
    state.evolve(time)

    density = state.evaluate(density_operator, root=None)
    density_array = state.evaluate(density_operator_array, root=None)
    shape_density = density.shape
    shape_density_array = density_array.shape

    # first make sure that the density matches on all points to the scalar value
    for dens in density_array:
        assert np.allclose(dens, density)

    # estimate the error at a given time in the first interval for a given element
    interval = state.get_intervals()[0]

    # ----- a simple quadpack reference implementation
    integrand = ManybodyIntegrand(syst, interval=interval, time=time, params=params,
                                  operator=density_operator)

    tmp = quadpack_qag(integrand.func, interval.kmin, interval.kmax,
                       order=interval.order, atol=1.0e-3, rtol=1.0e-3)

    result_ref, errors_ref, max_error_per_interval_ref, intervals_ref = tmp

    # ----- test for an operator with an array output
    tmp = state.refine_intervals(error_op=density_operator_array, intervals=interval,
                                 atol=1.0e-3, rtol=1.0e-3)
    error_sum, intervals, errors = tmp

    # check the return types
    assert isinstance(error_sum, np.float)
    assert isinstance(intervals, list)
    assert isinstance(errors, np.ndarray)
    assert len(intervals) == len(errors)
    for inter in intervals:
        assert isinstance(inter, manybody.Interval)
    assert errors.shape == (len(intervals), ) + shape_density_array
    max_error = 0
    for error in errors:
        max_error += error
    assert np.allclose(error_sum, np.max(max_error))

    # check that the intervals match
    assert len(intervals) == len(intervals_ref)
    for inte, inte_ref in zip(intervals, intervals_ref):
        assert np.allclose(inte.kmin, inte_ref[0])
        assert np.allclose(inte.kmax, inte_ref[1])

    # check that the errors match
    assert len(errors) == len(errors_ref)
    for err, err_ref in zip(errors, errors_ref):
        assert np.allclose(err[0], err_ref, atol=1e-6)

    # ----- test for an operator with a single scalar output

    # set up a new state, as the old one has refined intervals
    state = manybody.State(syst, tmax, occupation, params=params, refine=False)
    tmp = state.refine_intervals(error_op=density_operator, intervals=interval,
                                 atol=1.0e-3, rtol=1.0e-3)
    error_sum, intervals, errors = tmp

    # check the return types
    assert isinstance(error_sum, np.float)
    assert isinstance(intervals, list)
    assert isinstance(errors, np.ndarray)
    assert len(intervals) == len(errors)
    for inter in intervals:
        assert isinstance(inter, manybody.Interval)
    assert errors.shape == (len(intervals), ) + shape_density
    assert np.allclose(error_sum, np.sum(errors))

    # check that the intervals match
    assert len(intervals) == len(intervals_ref)
    for inte, inte_ref in zip(intervals, intervals_ref):
        assert np.allclose(inte.kmin, inte_ref[0])
        assert np.allclose(inte.kmax, inte_ref[1])

    # check that the errors match
    assert len(errors) == len(errors_ref)
    for err, err_ref in zip(errors, errors_ref):
        assert np.allclose(err, err_ref, atol=1e-6)


@mpi_testdriver.wrap(num_processes)
def test_add_boundstates_to_manybody_state():

    comm = mpi.get_communicator()
    assert comm.size > 1

    syst = make_system().finalized()
    density_operator = kwant.operator.Density(syst)

    tmax = 50
    time = 5
    params = {'v': 0.0001}

    occupation = manybody.lead_occupation(chemical_potential=3)

    # manybody solver
    state = manybody.State(syst, tmax, occupation, params=params, refine=False)

    def make_psi(energy):
        return onebody.ScatteringStates(syst, lead=0, energy=energy,
                                        tmax=tmax, params=params)[0]

    boundstate_tasks = {100: onebody.Task(weight=0.2, energy=2.1, lead=None, mode=None),
                        101: onebody.Task(weight=0.3, energy=2.3, lead=None, mode=None)}

    boundstate_tasks_distributed = mpi.distribute_dict(boundstate_tasks,
                                                       mpi.round_robin,
                                                       comm)

    boundstate_psi = {key: make_psi(task.energy) for key, task
                      in boundstate_tasks_distributed.items()}

    # test simply that we can evolve and evaluate the state
    state.add_boundstates(boundstate_psi, boundstate_tasks)
    state.evolve(time)
    state.evaluate(density_operator)

    # test for error if key are alread occupied
    with pytest.raises(KeyError) as exc:
        state.add_boundstates(boundstate_psi, boundstate_tasks)
    error_string = str(exc.value)
    message = 'boundstate key=100 already present in solver.'
    assert message in error_string

    # test if the input dict is not distributed
    boundstate_tasks = {102: onebody.Task(weight=0.2, energy=2.1, lead=None, mode=None),
                        103: onebody.Task(weight=0.3, energy=2.3, lead=None, mode=None)}
    boundstate_psi = {key: make_psi(task.energy) for key, task
                      in boundstate_tasks.items()}
    raises(AssertionError, state.add_boundstates, boundstate_psi, boundstate_tasks)

    # test if the keys do not match in both input dicts
    boundstate_tasks_distributed = mpi.distribute_dict(boundstate_tasks,
                                                       mpi.round_robin,
                                                       comm)
    boundstate_psi = {key: make_psi(task.energy) for key, task
                      in boundstate_tasks_distributed.items()}
    del boundstate_tasks[103]
    raises(AssertionError, state.add_boundstates, boundstate_psi, boundstate_tasks)


@mpi_testdriver.wrap(num_processes)
def test_get_rank():

    rank = mpi.get_rank()
    comm = mpi.get_communicator()

    assert isinstance(rank, dict)
    assert rank['rank'] == comm.rank
