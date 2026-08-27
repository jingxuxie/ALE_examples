# -*- coding: utf-8 -*-
# Copyright 2016-2020 tkwant authors.
#
# This file is part of tkwant.  It is subject to the license terms in the file
# LICENSE.rst found in the top-level directory of this distribution and at
# http://kwant-project.org/license.  A list of tkwant authors can be found in
# the file AUTHORS.rst at the top-level directory of this distribution and at
# http://kwant-project.org/authors.

"""Test module for `tkwant.manybody`"""

import pytest
from pytest import raises
import cmath
import numpy as np
import kwant
from numpy.testing import (assert_array_almost_equal, assert_almost_equal)
from scipy.special import erf
import functools
import itertools
import copy
import tinyarray as ta
from math import cos, sin, exp


from .. import onebody, manybody, leads
# from tkwant.tests.common import (make_square, make_square_with_leads, make_simple_lead,
#                                  make_complex_lead, check_boundary_hamiltonian)

import kwantspectrum

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)


def make_simple_lead(W=3):
    lat = kwant.lattice.square(1, norbs=1)
    sym = kwant.TranslationalSymmetry((-1, 0))
    H = kwant.Builder(sym)
    H[(lat(0, y) for y in range(W))] = 0
    H[lat.neighbors()] = -1
    return H


def onsite_potential(site, time, v):
    return 4 * (1 + v * cmath.exp(- 1j * time))


def gaussian(time, t0, A, sigma):
    return A * (1 + erf((time - t0) / sigma))


# time dependent coupling with gaussian pulse
def coupling_nn(site1, site2, time, t0, A, sigma):
    return - cmath.exp(- 1j * gaussian(time, t0, A, sigma))


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


def make_td_system(lat, N, td_onsite):
    I0 = ta.identity(2)
    syst = kwant.Builder()
    square = itertools.product(range(N), range(N))
    syst[(lat(i, j) for i, j in square)] = td_onsite
    syst[lat.neighbors()] = -1 * I0
    return syst


def make_td_system_with_leads(lat, N, lead_maker, td_onsite):
    syst = make_td_system(lat, N, td_onsite)
    syst.attach_lead(lead_maker(lat, N))
    syst.attach_lead(lead_maker(lat, N).reversed())
    return syst


@pytest.fixture
def two_band_spectrum():
    lead = make_simple_lead(W=2).finalized()
    return kwantspectrum.spectrum(lead)


@pytest.fixture
def flat_band_spectrum():

    def make_lead_with_flat_band(ll=3):
        lat = kwant.lattice.square(norbs=1)
        lead = kwant.Builder(kwant.TranslationalSymmetry((-1, 1)))
        lead[[lat(0, j) for j in range(ll)]] = 0
        lead[lat.neighbors()] = -1
        return lead

    lead = make_lead_with_flat_band().finalized()
    return kwantspectrum.spectrum(lead)


@pytest.fixture
def uniform_occupation():
    def uniform_distribution(x):
        return np.ones(len(x))

    class UniformOccupation:
        def __init__(self):
            self.distribution = uniform_distribution
            self.bands = None
            self.energy_range = None
    return UniformOccupation()


@pytest.fixture
def SimpleInterval():

    class Interval:
        def __init__(self, kmin, kmax):
            self.kmin = kmin
            self.kmax = kmax
            self.checkattribute = 'check'  # dummy attribute to check if it is copied

        def __eq__(self, other):
            return (self.kmin == other.kmin and self.kmax == other.kmax and
                    self.checkattribute == other.checkattribute)

        def __ne__(self, other):
            return not self.__eq__(other)
    return Interval


@pytest.fixture
def quadrature_interval():
    return manybody.Interval(lead=0, band=0, kmin=0, kmax=np.pi / 2)


VALID_CHEMICAL_POTENTIALS = [-float("inf"), -1., -1, 0, 0., 1, 1., float("inf")]
VALID_TEMPERATURES = [0, 0., 1, 1., float("inf")]
VALID_ENERGY_CUTOFFS = [-float("inf"), -1., -1, 0, 0., 1, 1., float("inf")]

VALID_QUADRATURES = ["gausslegendre", "kronrod"]
VALID_INTEGRATION_VARIABLES = ["energy", "momentum"]


def unknown_distribution_function(chemical_potential, temperature, energy):
    """an arbitrary distribution function (here the fermi function)"""
    return 1 / (np.exp((energy - chemical_potential) / temperature) - 1)


def test_lead_occupation_default():
    occupation = manybody.lead_occupation()
    assert callable(occupation.distribution)
    assert occupation.distribution(-1) == 1
    assert occupation.distribution(1) == 0
    assert len(occupation.energy_range) == 1
    emin, emax = occupation.energy_range[0]
    assert emin is None
    assert emax == 0
    assert occupation.bands is None


def model_tasks():

    # we take a simple spectrum with only two bands.
    # it has the dispersion E_n(k), where n is the band index and k the momentum:
    # E_0(k) = - (2 cos(k) + 1)
    # E_1(k) = - (2 cos(k) - 1)

    def energy_func(momentum):
        return - (2 * np.cos(momentum) + 1)

    def velocity_func(momentum):
        return 2 * np.sin(momentum)

    def distribution_func(energy):
        return 1 / (np.exp((energy - 1) / 0.5) - 1)

    interval_1 = manybody.Interval(lead=0, band=0, kmin=0, kmax=np.pi / 2,
                                   integration_variable='momentum', order=4,
                                   quadrature='gausslegendre')

    # gauss legendre abscissas between kmin = 0 and kmax = pi/2
    momenta = [0.10906329, 0.51837768, 1.05241865, 1.46173304]
    weights_1 = [0.27320456, 0.51219361, 0.51219361, 0.27320456]

    interval_2 = manybody.Interval(lead=0, band=0, kmin=0, kmax=np.pi / 2,
                                   integration_variable='energy', order=4,
                                   quadrature='gausslegendre')

    # gauss legendre abscissas between E_0(kmin) = -3 and E_0(kmax) = -1
    energies = [-2.86113631, -2.33998104, -1.66001896, -1.13886369]
    weights_2 = [0.34785485, 0.65214515, 0.65214515, 0.34785485]

    variables = ('energy_func, velocity_func, distribution_func,'
                 'interval, weights, x, x_type')
    model = []
    model.append((energy_func, velocity_func, distribution_func,
                  interval_1, weights_1, momenta, 'momentum'))
    model.append((energy_func, velocity_func, distribution_func,
                  interval_2, weights_2, energies, 'energy'))

    return pytest.mark.parametrize(variables, model)


@pytest.mark.parametrize('chemical_potential', VALID_CHEMICAL_POTENTIALS)
def test_lead_occupation_vary_chemical_potential(chemical_potential):
    # zero temperature, fermi-dirac distribution
    occupation = manybody.lead_occupation(chemical_potential=chemical_potential)
    assert len(occupation.energy_range) == 1
    emin, emax = occupation.energy_range[0]
    assert emin is None
    assert emax is chemical_potential

    # zero temperature, unknown distribution function
    occupation = manybody.lead_occupation(chemical_potential=chemical_potential, distribution=unknown_distribution_function)
    assert len(occupation.energy_range) == 1
    emin, emax = occupation.energy_range[0]
    assert emin is None
    assert emax is None

    # finite temperature, fermi-dirac distribution
    occupation = manybody.lead_occupation(chemical_potential=chemical_potential, temperature=1)
    effective_emax = chemical_potential + manybody._fermi_function_below_epsilon(temperature=1)
    assert len(occupation.energy_range) == 1
    emin, emax = occupation.energy_range[0]
    assert emin is None
    assert emax == effective_emax


@pytest.mark.parametrize('temperature', VALID_TEMPERATURES)
def test_lead_occupation_vary_temperature(temperature):
    # TODO: no good test for prebind temperature value at the moment

    # fermi-dirac distribution
    occupation = manybody.lead_occupation(temperature=temperature)
    assert len(occupation.energy_range) == 1
    emin, emax = occupation.energy_range[0]
    if temperature > 0:
        # TODO: check
        assert emax == manybody._fermi_function_below_epsilon(temperature=temperature)
    else:
        assert emax == 0
    assert emin is None
    assert callable(occupation.distribution)

    # unknown distribution function
    occupation = manybody.lead_occupation(temperature=temperature,
                                          distribution=unknown_distribution_function)
    assert len(occupation.energy_range) == 1
    emin, emax = occupation.energy_range[0]
    assert emin is None
    assert emax is None
    assert callable(occupation.distribution)


@pytest.mark.parametrize('emax', VALID_ENERGY_CUTOFFS)
def test_lead_occupation_vary_emax(emax):

    energy_range = [(None, emax)]

    # zero temperature, fermi-dirac distribution, default emax gets not overwritten
    occupation = manybody.lead_occupation(energy_range=energy_range)
    assert len(occupation.energy_range) == 1
    _emin, _emax = occupation.energy_range[0]
    if emax <= 0:
        assert _emax == emax
    else:
        assert _emax == 0
    assert _emin is None

    # zero temperature, fermi-dirac distribution, some chemical potential, default emax gets not overwritten
    occupation = manybody.lead_occupation(energy_range=energy_range, chemical_potential=0.5)
    assert len(occupation.energy_range) == 1
    _emin, _emax = occupation.energy_range[0]
    if emax <= 0.5:
        assert _emax == emax
    else:
        assert _emax == 0.5
    assert _emin is None

    # zero temperature, unknown distribution function, default emax gets overwritten
    occupation = manybody.lead_occupation(energy_range=energy_range, distribution=unknown_distribution_function)
    assert len(occupation.energy_range) == 1
    _emin, _emax = occupation.energy_range[0]
    assert _emax == emax
    assert _emin is None

    # zero temperature, unknown distribution function, some chemical potential, default emax gets overwritten
    occupation = manybody.lead_occupation(energy_range=energy_range,
                                          distribution=unknown_distribution_function,
                                          chemical_potential=0.5)
    assert len(occupation.energy_range) == 1
    _emin, _emax = occupation.energy_range[0]
    assert _emax == emax
    assert _emin is None

    # finite temperature, fermi-dirac distribution, default emax gets overwritten
    occupation = manybody.lead_occupation(energy_range=energy_range, temperature=1)
    assert len(occupation.energy_range) == 1
    _emin, _emax = occupation.energy_range[0]
    assert _emax == emax
    assert _emin is None

    # finite temperature, fermi-dirac distribution, some chemical potential, default emax gets overwritten
    occupation = manybody.lead_occupation(energy_range=energy_range,
                                          temperature=1, chemical_potential=0.5)
    assert len(occupation.energy_range) == 1
    _emin, _emax = occupation.energy_range[0]
    assert _emax == emax
    assert _emin is None


@pytest.mark.parametrize('emin', VALID_ENERGY_CUTOFFS)
def test_lead_occupation_vary_emin(emin):

    energy_range = [(emin, None)]

    # zero temperature, fermi-dirac distribution
    occupation = manybody.lead_occupation(energy_range=energy_range)
    if emin < 0:  # the interval is (at lest partially) below zero
        assert len(occupation.energy_range) == 1
        _emin, _emax = occupation.energy_range[0]
        assert _emax == 0
        assert _emin == emin
    else:  # the whole interval is above 0, does not contribute
        assert occupation is None

    # zero temperature, fermi-dirac distribution, some chemical potential
    occupation = manybody.lead_occupation(energy_range=energy_range, chemical_potential=2)
    if emin < 2:  # the interval is (at lest partially) below zero
        assert len(occupation.energy_range) == 1
        _emin, _emax = occupation.energy_range[0]
        assert _emax == 2
        assert _emin == emin
    else:  # the whole interval is above 0, does not contribute
        assert occupation is None

    # zero temperature, unknown distribution function
    occupation = manybody.lead_occupation(energy_range=energy_range, distribution=unknown_distribution_function)
    assert len(occupation.energy_range) == 1
    _emin, _emax = occupation.energy_range[0]
    assert _emax is None
    assert _emin == emin

    # zero temperature, unknown distribution function, some chemical potential
    occupation = manybody.lead_occupation(energy_range=energy_range,
                                          distribution=unknown_distribution_function,
                                          chemical_potential=2)
    assert len(occupation.energy_range) == 1
    _emin, _emax = occupation.energy_range[0]
    assert _emax is None
    assert _emin == emin

    # finite temperature, fermi-dirac distribution
    occupation = manybody.lead_occupation(energy_range=energy_range, temperature=1)
    eeff = manybody._fermi_function_below_epsilon(temperature=1)
    if emin < eeff:
        assert len(occupation.energy_range) == 1
        _emin, _emax = occupation.energy_range[0]
        assert _emax == eeff
        assert _emin == emin
    else:
        assert occupation is None

    # finite temperature, fermi-dirac distribution, some chemical potential
    occupation = manybody.lead_occupation(energy_range=energy_range, temperature=1,
                                          chemical_potential=2)
    eeff = 2 + manybody._fermi_function_below_epsilon(temperature=1)
    if emin < eeff:
        assert len(occupation.energy_range) == 1
        _emin, _emax = occupation.energy_range[0]
        assert _emax == eeff
        assert _emin == emin
    else:
        assert occupation is None


def test_lead_occupation_energy_range():
    # zero temperature, fermi-dirac distribution
    # first interval below chemical potential (which is zero), second interval only partly below
    energy_range = [(None, -0.5), (-0.4, 2)]
    occupation = manybody.lead_occupation(energy_range=energy_range)
    assert len(occupation.energy_range) == 2
    emin, emax = occupation.energy_range[0]
    assert emin is None
    assert emax == -0.5
    emin, emax = occupation.energy_range[1]
    assert emin == -0.4
    assert emax == 0

    # first interval below chemical potential (which is zero), second interval is above
    energy_range = [(None, -0.5), (0, 2)]
    occupation = manybody.lead_occupation(energy_range=energy_range)
    assert len(occupation.energy_range) == 1
    emin, emax = occupation.energy_range[0]
    assert emin is None
    assert emax == -0.5

    # two intergrals above chemical potential
    energy_range = [(0, 2), (4, 5)]
    occupation = manybody.lead_occupation(energy_range=energy_range)
    assert occupation is None


@pytest.mark.parametrize('chemical_potential', VALID_CHEMICAL_POTENTIALS)
@pytest.mark.parametrize('emax', VALID_ENERGY_CUTOFFS)
def test_lead_occupation_vary_chemical_potential_and_emax(chemical_potential, emax):
    energy_range = [(None, emax)]
    # zero temperature, fermi-dirac distribution
    occupation = manybody.lead_occupation(chemical_potential=chemical_potential, energy_range=energy_range)
    _emin, _emax = occupation.energy_range[0]
    if chemical_potential <= emax:
        assert _emax == chemical_potential
    else:
        assert _emax == emax
    assert _emin is None

    # zero temperature, unknown distribution function
    occupation = manybody.lead_occupation(chemical_potential=chemical_potential,
                                          energy_range=energy_range, distribution=unknown_distribution_function)
    _emin, _emax = occupation.energy_range[0]
    assert _emax == emax
    assert _emin is None

    # finite temperature, fermi-dirac distribution
    occupation = manybody.lead_occupation(chemical_potential=chemical_potential,
                                          energy_range=energy_range, temperature=1)
    _emin, _emax = occupation.energy_range[0]
    assert _emax == emax
    assert _emin is None


def test_lead_occupation_fermi_diract_zero_temperature():
    # check default values, finite temperature
    mu = 2
    epsilon = 1E-6  # some small number
    occupation = manybody.lead_occupation(chemical_potential=mu)
    _emin, _emax = occupation.energy_range[0]
    assert occupation.distribution(energy=mu - epsilon) == 1
    assert occupation.distribution(energy=mu + epsilon) == 0
    assert _emin is None
    assert _emax == mu
    assert occupation.bands is None


def test_lead_occupation_fermi_diract_finite_temperature():
    # check default values, finite temperature
    def fermi_function(chemical_potential, temperature, energy):
        return 1 / (np.exp((energy - chemical_potential) / temperature) + 1)

    mu = 2
    temp = 3
    occupation = manybody.lead_occupation(chemical_potential=mu, temperature=temp)
    _emin, _emax = occupation.energy_range[0]
    assert occupation.distribution(energy=1) == fermi_function(mu, temp, energy=1)
    assert occupation.distribution(energy=3) == fermi_function(mu, temp, energy=3)
    assert _emin is None
    assert _emax == mu + manybody._fermi_function_below_epsilon(temperature=temp)
    assert occupation.bands is None


def test_lead_occupation_bose_distribution():
    # check a different distribution at finite temperature
    def bose_function(chemical_potential, temperature, energy):
        return 1 / (np.exp((energy - chemical_potential) / temperature) - 1)

    mu = 2
    temp = 3
    occupation = manybody.lead_occupation(chemical_potential=mu, temperature=temp, distribution=bose_function)
    assert occupation.distribution(1) == bose_function(chemical_potential=mu, temperature=temp, energy=1)
    assert occupation.distribution(3) == bose_function(chemical_potential=mu, temperature=temp, energy=3)
    assert len(occupation.energy_range) == 1
    emin, emax = occupation.energy_range[0]
    assert emin is None
    assert emax is None
    assert occupation.bands is None


def test_lead_occupation_band_selection():
    # check band selection
    occupation = manybody.lead_occupation(bands=3)
    assert occupation.bands == [3]
    occupation = manybody.lead_occupation(bands=[3])
    assert occupation.bands == [3]
    # bands always sorted and without dublicates
    occupation = manybody.lead_occupation(bands=[3, 2, 5, 5, -1])
    assert occupation.bands == [-1, 2, 3, 5]


def test_lead_occupation_own_datatype():
    class MyOccupation:
        def __init__(self, distribution, energy_range, bands):
            self.distribution = distribution
            self.bands = bands
            self.energy_range = energy_range
            self.somefield = 42
    occupation = manybody.lead_occupation(occupation_type=MyOccupation)
    assert callable(occupation.distribution)
    assert occupation.bands is None
    assert occupation.energy_range == [(None, 0)]
    assert occupation.somefield == 42


def test_lead_occupation_raises():
    # negative temperature
    raises(ValueError, manybody.lead_occupation, temperature=-1)
    # not real numbers
    raises(TypeError, manybody.lead_occupation, chemical_potential=1 + 1j)
    raises(TypeError, manybody.lead_occupation, temperature=1 + 1j)
    # non callable distribution
    raises(TypeError, manybody.lead_occupation, distribution='not_callable')


def test_make_intervals_default(two_band_spectrum, uniform_occupation):
    intervals = manybody.calc_intervals(two_band_spectrum, uniform_occupation)

    # check all types of the returned elements
    assert isinstance(intervals, list)
    assert len(intervals) == two_band_spectrum.nbands
    for interval in intervals:
        assert isinstance(interval, manybody.Interval)
        assert isinstance(interval.lead, int)
        assert isinstance(interval.band, int)
        assert isinstance(interval.kmin, float)
        assert isinstance(interval.kmax, float)
        assert isinstance(interval.order, int)
        assert isinstance(interval.integration_variable, str)
        assert isinstance(interval.quadrature, str)

    # check explicit returned values
    # intervals for all bands of the spectrum
    # intervals contains the momentum (k) intervals where d E_n / dk > 0
    # from above dispersion follows that this is the case for k in [0, pi]
    for i, interval in enumerate(intervals):
        assert interval.lead == 0  # only one lead
        assert interval.band == i
        assert_almost_equal(interval.kmin, 0)
        assert_almost_equal(interval.kmax, np.pi)
        assert interval.order == 10
        assert interval.integration_variable == 'momentum'
        assert interval.quadrature == 'kronrod'


def test_make_intervals_with_unoccupied_leads(two_band_spectrum, uniform_occupation):
    # check that intervals with additional unoccupied leads is similar
    intervals = manybody.calc_intervals(two_band_spectrum, uniform_occupation)

    for nb_leads in range(1, 5):
        spectra = [two_band_spectrum] * nb_leads
        occupations = [uniform_occupation] + [None] * (nb_leads - 1)
        intervals_unocc = manybody.calc_intervals(spectra, occupations)
        assert intervals_unocc == intervals


def test_make_intervals_lead_index(two_band_spectrum, uniform_occupation):
    # check that the position of the occupation determines the lead index
    total_nb_leads = 5
    for i in range(0, total_nb_leads):
        spectra = [two_band_spectrum] * total_nb_leads
        occupations = [None] * i + [uniform_occupation] + [None] * (total_nb_leads - i - 1)
        intervals = manybody.calc_intervals(spectra, occupations)
        for interval in intervals:
            assert interval.lead == i


def test_make_intervals_with_energy_constraint(two_band_spectrum, uniform_occupation):

    # select only bands in energy range emin < E_n(k) < emax
    # intervals contains the momentum (k) intervals where d E_n / dk > 0
    # with the additional constraint emin < E_n(k) < emax
    uniform_occupation.energy_range = [(-1, 1)]
    intervals = manybody.calc_intervals(two_band_spectrum, uniform_occupation)

    assert len(intervals) == two_band_spectrum.nbands
    for i, interval in enumerate(intervals):
        assert isinstance(interval, manybody.Interval)
        assert interval.lead == 0  # only one lead
        assert interval.band == i
        if interval.band == 0:
            assert_almost_equal(interval.kmin, 0.5 * np.pi)
            assert_almost_equal(interval.kmax, np.pi)
        else:
            assert_almost_equal(interval.kmin, 0)
            assert_almost_equal(interval.kmax, 0.5 * np.pi)


def test_make_intervals_with_energy_and_band_constraint(two_band_spectrum, uniform_occupation):

    # select only bands in energy range and take only lowest band with index 0
    # intervals contains the momentum (k) intervals where d E_0 / dk > 0
    # with the additional constraint emin < E_0(k) < emax
    # (note that we have set n to 0)
    uniform_occupation.energy_range = [(-1, 1)]
    uniform_occupation.bands = [0]
    intervals = manybody.calc_intervals(two_band_spectrum, uniform_occupation)

    assert len(intervals) == 1
    for i, interval in enumerate(intervals):
        assert isinstance(interval, manybody.Interval)
        assert interval.lead == 0  # only one lead
        assert interval.band == i
        assert_almost_equal(interval.kmin, 0.5 * np.pi)
        assert_almost_equal(interval.kmax, np.pi)


def test_make_intervals_which_are_empty(two_band_spectrum, uniform_occupation):
    # case where no intervals are found
    uniform_occupation.energy_range = [(5, 6)]
    intervals = manybody.calc_intervals(two_band_spectrum, uniform_occupation)
    assert isinstance(intervals, list)
    assert len(intervals) == 0


def test_make_intervals_with_two_similar_occupied_leads(two_band_spectrum, uniform_occupation):
    # two leads with equal occupation
    num_leads = 2
    intervals = manybody.calc_intervals([two_band_spectrum] * num_leads, uniform_occupation)
    assert len(intervals) == two_band_spectrum.nbands * num_leads
    for i, interval in enumerate(intervals):
        assert isinstance(interval, manybody.Interval)
        assert interval.lead in range(num_leads)
        assert_almost_equal(interval.kmin, 0)
        assert_almost_equal(interval.kmax, np.pi)


def test_make_intervals_with_two_differently_occupied_leads(two_band_spectrum, uniform_occupation):
    # two leads with different occupations
    num_leads = 2
    occupation_1 = copy.deepcopy(uniform_occupation)
    occupation_1.bands = [0]
    occupation_2 = copy.deepcopy(uniform_occupation)
    occupation_2.energy_range = [(-1, 1)]
    occupation_2.bands = [0]
    intervals = manybody.calc_intervals([two_band_spectrum] * num_leads, [occupation_1, occupation_2])
    assert len(intervals) == num_leads  # only one band per lead
    for i, interval in enumerate(intervals):
        assert isinstance(interval, manybody.Interval)
        if interval.lead == 0:
            assert_almost_equal(interval.kmin, 0)
            assert_almost_equal(interval.kmax, np.pi)
        elif interval.lead == 1:
            assert_almost_equal(interval.kmin, 0.5 * np.pi)
            assert_almost_equal(interval.kmax, np.pi)


def test_make_intervals_interface(two_band_spectrum, uniform_occupation):
    # check for robustness of interfact for sequences input
    intervals_1 = manybody.calc_intervals(two_band_spectrum, uniform_occupation)
    intervals_2 = manybody.calc_intervals([two_band_spectrum], uniform_occupation)
    intervals_3 = manybody.calc_intervals(two_band_spectrum, [uniform_occupation])
    intervals_4 = manybody.calc_intervals([two_band_spectrum], [uniform_occupation])
    assert intervals_1 == intervals_2 == intervals_3 == intervals_4
    intervals_1 = manybody.calc_intervals([two_band_spectrum] * 2, [uniform_occupation] * 2)
    intervals_2 = manybody.calc_intervals((two_band_spectrum, two_band_spectrum), uniform_occupation)
    assert intervals_1 == intervals_2  # only true in equal occupation


def test_make_intervals_band_index_out_of_range(two_band_spectrum, uniform_occupation):
    uniform_occupation.bands = [two_band_spectrum.nbands]
    raises(AssertionError, manybody.calc_intervals, two_band_spectrum, uniform_occupation)


def test_make_intervals_band_index_not_integer(two_band_spectrum, uniform_occupation):
    uniform_occupation.bands = [0.]
    raises(AssertionError, manybody.calc_intervals, two_band_spectrum, uniform_occupation)


def test_make_intervals_energies_interchanged(two_band_spectrum, uniform_occupation):
    uniform_occupation.energy_range = [(1, 0)]
    raises(AssertionError, manybody.calc_intervals, two_band_spectrum, uniform_occupation)


def test_make_intervals_emin_not_real(two_band_spectrum, uniform_occupation):
    uniform_occupation.energy_range = [(1 + 1j, None)]
    # todo
    # raises(TypeError, manybody.calc_intervals, two_band_spectrum, uniform_occupation)


def test_make_intervals_emax_not_real(two_band_spectrum, uniform_occupation):
    uniform_occupation.energy_range = [(None, 1 + 1j)]
    # todo
    # raises(TypeError, manybody.calc_intervals, two_band_spectrum, uniform_occupation)


def test_make_intervals_inconsitent_input(two_band_spectrum, uniform_occupation):
    # inhomogeneous occupation, that does not fit the number of leads
    raises(ValueError, manybody.calc_intervals, two_band_spectrum, [uniform_occupation] * 2)
    raises(ValueError, manybody.calc_intervals, [two_band_spectrum], [uniform_occupation] * 2)
    raises(ValueError, manybody.calc_intervals, [two_band_spectrum] * 3, [uniform_occupation] * 2)


def test_make_intervals_missing_energy_range_attribute(two_band_spectrum, uniform_occupation):
    del uniform_occupation.energy_range
    raises(AttributeError, manybody.calc_intervals, two_band_spectrum, uniform_occupation)


def test_make_intervals_missing_bands_attribute(two_band_spectrum, uniform_occupation):
    del uniform_occupation.bands
    raises(AttributeError, manybody.calc_intervals, two_band_spectrum, uniform_occupation)


def test_make_intervals_missing_distribution_attribute(two_band_spectrum, uniform_occupation):
    del uniform_occupation.distribution
    # todo
#    raises(AttributeError, manybody.calc_intervals, two_band_spectrum, uniform_occupation)


def test_split_interval_into_two(SimpleInterval):

    nint = 1  # number of returned intervals
    intervals = manybody._split_interval(interval=SimpleInterval(kmin=0, kmax=1),
                                         number_subintervals=nint)
    assert isinstance(intervals, list)
    assert len(intervals) == nint
    assert intervals == [SimpleInterval(kmin=0, kmax=1)]


def test_split_interval_into_three(SimpleInterval):

    nint = 2  # number of returned intervals
    intervals = manybody._split_interval(interval=SimpleInterval(kmin=0, kmax=1),
                                         number_subintervals=nint)
    assert isinstance(intervals, list)
    assert len(intervals) == nint
    assert intervals == [SimpleInterval(kmin=0, kmax=0.5),
                         SimpleInterval(kmin=0.5, kmax=1)]


def test_split_interval_wrong_input(SimpleInterval):
    raises(ValueError, manybody._split_interval, SimpleInterval(kmin=0, kmax=1), number_subintervals=0)
    raises(AssertionError, manybody._split_interval, SimpleInterval(kmin=0, kmax=1), number_subintervals=1.)


def test_split_interval_kmin_attribute_missing(SimpleInterval):
    interval = SimpleInterval(0, 1)
    del interval.kmin
    raises(AttributeError, manybody._split_interval, interval, 2)


def test_split_interval_kmax_attribute_missing(SimpleInterval):
    interval = SimpleInterval(0, 1)
    del interval.kmax
    raises(AttributeError, manybody._split_interval, interval, 2)


def test_split_intervals_no_split(SimpleInterval):
    nint = 1  # number of returned intervals per input interval
    input_intervals = [SimpleInterval(kmin=0, kmax=1), SimpleInterval(kmin=-4.0, kmax=2)]
    intervals = manybody.split_intervals(input_intervals, number_subintervals=nint)
    assert isinstance(intervals, list)
    assert len(intervals) == nint * len(input_intervals)
    assert intervals == [SimpleInterval(kmin=0, kmax=1), SimpleInterval(kmin=-4.0, kmax=2)]


def test_split_intervals_into_two(SimpleInterval):
    nint = 2  # number of returned intervals per input interval
    input_intervals = [SimpleInterval(kmin=0, kmax=1), SimpleInterval(kmin=-4.0, kmax=2)]
    intervals = manybody.split_intervals(input_intervals, number_subintervals=nint)
    assert isinstance(intervals, list)
    assert len(intervals) == nint * len(input_intervals)
    assert intervals == [SimpleInterval(kmin=0, kmax=0.5), SimpleInterval(kmin=0.5, kmax=1),
                         SimpleInterval(kmin=-4.0, kmax=-1.0), SimpleInterval(kmin=-1.0, kmax=2)]


def test_split_intervals_wrong_input(SimpleInterval):
    input_intervals = [SimpleInterval(kmin=0, kmax=1)]
    raises(ValueError, manybody.split_intervals, input_intervals, number_subintervals=0)
    raises(AssertionError, manybody.split_intervals, input_intervals, number_subintervals=1.)
    # interval not a list
    input_intervals = SimpleInterval(kmin=0, kmax=1)
    raises(TypeError, manybody.split_intervals, input_intervals, number_subintervals=2)


def test_attributes_similar():

    # use the manybody interval class to test for similarity
    int0 = manybody.Interval(lead=0, band=1, kmin=0, kmax=1.)
    int1 = manybody.Interval(lead=1, band=1, kmin=1E-12, kmax=1.)

    # check type
    res = manybody._attributes_similar(int0, int1, ['band', 'kmin', 'kmax'])
    assert isinstance(res, bool)

    # compare float attributes
    assert manybody._attributes_similar(int0, int1, ['band', 'kmin', 'kmax'])
    assert not manybody._attributes_similar(int0, int1, ['band', 'kmin', 'kmax'],
                                            rtol=0, atol=1E-15)

    # compare integer attributes
    assert not manybody._attributes_similar(int0, int1, ['lead', 'band', 'kmin', 'kmax'])

    # compare nonexisting attributes
    assert manybody._attributes_similar(int0, int1, ['bla'])

    # compare existing and nonexisting attributes
    int2 = manybody.Interval(lead=1, band=1, kmin=1E-12, kmax=1.)
    int2.bla = 42
    assert not manybody._attributes_similar(int0, int2, ['bla'])

    # compare float and numpy attributes
    int3 = manybody.Interval(lead=0, band=1, kmin=np.array([0.]), kmax=1.)
    assert manybody._attributes_similar(int1, int3, ['band', 'kmin', 'kmax'])
    assert not manybody._attributes_similar(int1, int3, ['band', 'kmin', 'kmax'],
                                            rtol=0, atol=1E-15)

    # compare numpy attributes
    int4 = manybody.Interval(lead=0, band=1, kmin=np.array([1E-12]), kmax=1.)
    assert manybody._attributes_similar(int3, int4, ['band', 'kmin', 'kmax'])
    assert not manybody._attributes_similar(int3, int4, ['band', 'kmin', 'kmax'],
                                            rtol=0, atol=1E-15)

    # compare numpy attributes with different sizes
    int5 = manybody.Interval(lead=0, band=1, kmin=np.array([0, 1E-12]), kmax=1.)
    assert manybody._attributes_similar(int4, int5, ['band', 'kmin', 'kmax'])


def test_combine_intervals():

    int0 = manybody.Interval(lead=3, band=1, kmin=0, kmax=1.)
    int1 = manybody.Interval(lead=5, band=1, kmin=1E-12, kmax=1.)
    int2 = manybody.Interval(lead=6, band=1, kmin=1E-12, kmax=1.)
    int3 = manybody.Interval(lead=7, band=1, kmin=0.1, kmax=1.)
    int4 = manybody.Interval(lead=(1, 2), band=1, kmin=0, kmax=1.)

    # combine two intervals
    combined = manybody.combine_intervals([int0, int1])
    assert isinstance(combined, list)
    assert len(combined) == 1
    assert combined[0].lead == (3, 5)
    assert combined[0].band == int0.band
    assert combined[0].kmin == int0.kmin
    assert combined[0].kmax == int0.kmax
    assert int0.lead == 3
    assert int1.lead == 5

    # do not combine intervals
    combined = manybody.combine_intervals([int0, int3])
    assert isinstance(combined, list)
    assert len(combined) == 2
    assert combined[0].lead == 3
    assert combined[1].lead == 7

    # combine an interval with lead integer and lead tuple
    combined = manybody.combine_intervals([int0, int4])
    assert len(combined) == 1
    assert combined[0].lead == (1, 2, 3)

    # combine on an empty list
    combined = manybody.combine_intervals([])
    assert isinstance(combined, list)
    assert len(combined) == 0

    # combine on a list with only one interval
    combined = manybody.combine_intervals([int0])
    assert isinstance(combined, list)
    assert len(combined) == 1
    assert combined[0].lead == 3

    # combine three intervals
    combined = manybody.combine_intervals([int0, int1, int2])
    assert isinstance(combined, list)
    assert len(combined) == 1
    assert combined[0].lead == (3, 5, 6)

    # combine two out of three intervals
    combined = manybody.combine_intervals([int0, int1, int3])
    assert len(combined) == 2
    assert combined[0].lead == (3, 5)
    assert combined[1].lead == 7

    combined = manybody.combine_intervals([int3, int1, int0])
    assert len(combined) == 2
    assert combined[0].lead == 7
    assert combined[1].lead == (3, 5)

    combined = manybody.combine_intervals([int1, int3, int0])
    assert len(combined) == 2
    assert combined[0].lead == (3, 5)
    assert combined[1].lead == 7

    # input list has some elements without lead attribute
    # if bla is the last arguement, nothing will be combined
    with pytest.raises(AttributeError) as exc:
        manybody.combine_intervals(['bla', int0])
    assert 'attribute "lead" missing in interval' in str(exc.value)

    with pytest.raises(AttributeError) as exc:
        manybody.combine_intervals([int0, 'bla', int1])
    assert 'attribute "lead" missing in interval' in str(exc.value)


def test_calc_modes_and_weights(two_band_spectrum, quadrature_interval):

    # check all types of the returned elements
    def distribution(energy):
        return np.ones(len(energy))

    quadrature_interval.quadrature = 'gausslegendre'

    tmp = manybody._calc_modes_and_weights(quadrature_interval, distribution, two_band_spectrum)
    modes, energies, momenta, weights, math_weights, phys_weights = tmp

    order = quadrature_interval.order

    # test shapes of the return elements

    assert isinstance(modes, np.ndarray)
    assert isinstance(energies, np.ndarray)
    assert isinstance(momenta, np.ndarray)
    assert isinstance(weights, np.ndarray)
    assert isinstance(math_weights, np.ndarray)
    assert isinstance(phys_weights, np.ndarray)

    assert modes.shape == (order,)
    assert energies.shape == (order,)
    assert momenta.shape == (order,)
    assert phys_weights.shape == (order,)

    assert weights.shape == (order,)
    assert math_weights.shape == (order,)

    quadrature_interval.quadrature = 'kronrod'

    tmp = manybody._calc_modes_and_weights(quadrature_interval, distribution, two_band_spectrum)
    modes, energies, momenta, weights, math_weights, phys_weights = tmp

    # test shapes of the return elements

    assert isinstance(modes, np.ndarray)
    assert isinstance(energies, np.ndarray)
    assert isinstance(momenta, np.ndarray)
    assert isinstance(weights, np.ndarray)
    assert isinstance(math_weights, np.ndarray)
    assert isinstance(phys_weights, np.ndarray)

    assert modes.shape == (2 * order + 1,)
    assert energies.shape == (2 * order + 1,)
    assert momenta.shape == (2 * order + 1,)
    assert phys_weights.shape == (2 * order + 1,)

    assert weights.shape == (2 * order + 1, 2)
    assert math_weights.shape == (2 * order + 1, 2)

    # no vector function distribution

    def fermi_dirac_distribution(energy):
        """Fermi diract distribution function"""
        return 1. / (1 + exp((energy - 0.5) / 0.1))
    distribution = fermi_dirac_distribution
    tmp = manybody._calc_modes_and_weights(quadrature_interval, distribution, two_band_spectrum)


@model_tasks()
def test_calc_tasks_values(two_band_spectrum, uniform_occupation, energy_func,
                           velocity_func, distribution_func,
                           interval, weights, x, x_type):

    uniform_occupation.distribution = distribution_func

    tasks = manybody.calc_tasks(interval, two_band_spectrum, uniform_occupation)

    if x_type == 'momentum':
        for i, k in enumerate(x):
            energy = energy_func(k)
            weight = distribution_func(energy) * velocity_func(k) * weights[i] / (2 * np.pi)
            assert_almost_equal(energy, tasks[i].energy)
            assert_almost_equal(weight, tasks[i].weight)
    elif x_type == 'energy':
        for i, energy in enumerate(x):
            weight = distribution_func(energy) * weights[i] / (2 * np.pi)
            assert_almost_equal(energy, tasks[i].energy)
            assert_almost_equal(weight, tasks[i].weight)
    else:
        raise NotImplementedError('type={} unknown'.format(x_type))


def test_calc_tasks_default(two_band_spectrum, uniform_occupation, quadrature_interval):

    # check all types of the returned elements
    tasks = manybody.calc_tasks(quadrature_interval, two_band_spectrum, uniform_occupation)

    assert isinstance(tasks, dict)
    assert len(tasks) == quadrature_interval.order * 2 + 1
    for i, (key, value) in enumerate(tasks.items()):

        assert key == i
        assert isinstance(value.lead, int)
        # assert isinstance(value.mode, int) # some numpy number, TODO
        assert isinstance(value.energy, float)
        # assert isinstance(value.weight, float) # for gausslegendre
        # assert isinstance(value.weight, np.ndarray) # for kronrod
        # TODO, make weight type similar


def test_calc_tasks_with_flat_band(flat_band_spectrum, uniform_occupation):

    # this is the interval with the flat band (velocity zero)
    interval = manybody.Interval(lead=0, band=1, kmin=-np.pi, kmax=np.pi)

    # check that no tasks are calculated as weights are zero
    tasks = manybody.calc_tasks(interval, flat_band_spectrum, uniform_occupation)

    assert len(tasks) == 0

    # check that we can tune the tolerance to get all tasks again
    tasks = manybody.calc_tasks(interval, flat_band_spectrum, uniform_occupation, tol=1E-30)

    assert len(tasks) == 2 * interval.order + 1


def test_calc_tasks_keys(two_band_spectrum, uniform_occupation, quadrature_interval):

    tasks = manybody.calc_tasks(quadrature_interval, two_band_spectrum, uniform_occupation, keys=itertools.count(5))

    for i, (key, task) in enumerate(tasks.items()):
        assert key == i + 5  # all keys shifted by offset


def test_calc_tasks_lead_index(two_band_spectrum, uniform_occupation, quadrature_interval):

    quadrature_interval.lead = 0
    tasks = manybody.calc_tasks(quadrature_interval, two_band_spectrum, uniform_occupation)

    for i, (key, task) in enumerate(tasks.items()):
        assert isinstance(task.lead, int)
        assert task.lead == 0


def test_calc_tasks_lead_index_tuple(two_band_spectrum, uniform_occupation):

    # calculate tasks with a sequence of intervals
    inter0 = manybody.Interval(lead=0, band=0, kmin=0, kmax=np.pi / 2)
    inter1 = manybody.Interval(lead=1, band=0, kmin=0, kmax=np.pi / 2)
    intervals_sep = [inter0, inter1]
    spectra = [two_band_spectrum, two_band_spectrum]

    tasks_sep = manybody.calc_tasks(intervals_sep, spectra, uniform_occupation)

    # calculate tasks with only one interval including both leads
    intervals_grp = manybody.Interval(lead=(0, 1), band=0, kmin=0, kmax=np.pi / 2)
    tasks_grp = manybody.calc_tasks(intervals_grp, spectra, uniform_occupation)

    assert len(tasks_sep) == len(tasks_grp)
    for key, value in tasks_sep.items():
        assert tasks_grp[key].lead == value.lead
        assert tasks_grp[key].mode == value.mode
        assert_almost_equal(tasks_grp[key].energy, value.energy)
        assert_almost_equal(tasks_grp[key].momentum, value.momentum)
        assert_array_almost_equal(tasks_grp[key].weight, value.weight)
        assert_array_almost_equal(tasks_grp[key].math_weight, value.math_weight)
        assert_array_almost_equal(tasks_grp[key].phys_weight, value.phys_weight)


def test_calc_tasks_band_index(two_band_spectrum, uniform_occupation, quadrature_interval):

    for band in range(two_band_spectrum.nbands):
        quadrature_interval.band = band
        tasks = manybody.calc_tasks(quadrature_interval, two_band_spectrum, uniform_occupation)
        assert isinstance(tasks, dict)
    # no specific test so far, as only numerical values change


@pytest.mark.parametrize('quadrature', VALID_QUADRATURES)
def test_calc_tasks_quadrature(two_band_spectrum, uniform_occupation, quadrature_interval, quadrature):

    quadrature_interval.quadrature = quadrature
    tasks = manybody.calc_tasks(quadrature_interval, two_band_spectrum, uniform_occupation)

    # todo: make weight type similar (numpy array)
    if quadrature == 'gausslegendre':
        assert len(tasks) == quadrature_interval.order
        for i, (key, task) in enumerate(tasks.items()):
            assert isinstance(task.lead, int)
            assert isinstance(task.weight, float)
    elif quadrature == 'kronrod':
        assert len(tasks) == 2 * quadrature_interval.order + 1
        for i, (key, task) in enumerate(tasks.items()):
            assert isinstance(task.lead, int)
            assert isinstance(task.weight, np.ndarray)
    else:
        raise NotImplementedError('quadrature={} unknown'.format(quadrature))


def test_calc_tasks_attribute_copy(two_band_spectrum, uniform_occupation, quadrature_interval):

    class MyTask:
        def __init__(self, weight, phys_weight, math_weight, energy, momentum, mode, lead):
            self.weight = weight
            self.phys_weight = phys_weight
            self.math_weight = math_weight
            self.energy = energy
            self.momentum = momentum
            self.mode = mode
            self.lead = lead
            self.checkattribute = 'check_task'  # dummy attribute to check if it is copied

    tasks = manybody.calc_tasks(quadrature_interval, two_band_spectrum, uniform_occupation, task_type=MyTask)

    for i, (key, task) in enumerate(tasks.items()):
        assert task.checkattribute == 'check_task'


@pytest.mark.parametrize('integration_variable', VALID_INTEGRATION_VARIABLES)
def test_calc_tasks_integration_variable(two_band_spectrum, uniform_occupation, quadrature_interval, integration_variable):

    quadrature_interval.integration_variable = integration_variable
    tasks = manybody.calc_tasks(quadrature_interval, two_band_spectrum, uniform_occupation)
    assert isinstance(tasks, dict)
    # no specific test so far, as only numerical values change


def test_calc_tasks_lead_index_out_of_range(quadrature_interval, two_band_spectrum,
                                            uniform_occupation):
    quadrature_interval.lead = 1
    raises(IndexError, manybody.calc_tasks, quadrature_interval, two_band_spectrum, uniform_occupation)


def test_calc_tasks_band_index_out_of_range(quadrature_interval, two_band_spectrum,
                                            uniform_occupation):
    quadrature_interval.band = 2
    raises(AssertionError, manybody.calc_tasks, quadrature_interval, two_band_spectrum, uniform_occupation)


def test_calc_tasks_kmin_kmax_interchanged(quadrature_interval, two_band_spectrum,
                                           uniform_occupation):
    quadrature_interval.kmin = 1
    quadrature_interval.kmax = 0
    raises(ValueError, manybody.calc_tasks, quadrature_interval, two_band_spectrum, uniform_occupation)


def test_calc_tasks_order_out_of_range(quadrature_interval, two_band_spectrum,
                                       uniform_occupation):
    quadrature_interval.order = 0
    raises(ValueError, manybody.calc_tasks, quadrature_interval, two_band_spectrum, uniform_occupation)


def test_calc_tasks_nonexisting_quadrature(quadrature_interval, two_band_spectrum,
                                           uniform_occupation):
    quadrature_interval.quadrature = 'bla'
    raises(NotImplementedError, manybody.calc_tasks, quadrature_interval, two_band_spectrum, uniform_occupation)


def test_calc_tasks_nonexisting_integration_variable(quadrature_interval, two_band_spectrum,
                                                     uniform_occupation):
    quadrature_interval.integration_variable = 'bla'
    raises(NotImplementedError, manybody.calc_tasks, quadrature_interval, two_band_spectrum, uniform_occupation)


def test_calc_tasks_distribution_not_callable(quadrature_interval, two_band_spectrum,
                                              uniform_occupation):
    uniform_occupation.distribution = 1
    raises(TypeError, manybody.calc_tasks, quadrature_interval, two_band_spectrum, uniform_occupation)


@pytest.mark.integtest  # marker for integration tests
def test_calc_initial_state():

    # ---- check initial state
    chemical_potential = 3
    tmax = 500
    params = {'v': 0.1, 't0': 0, 'A': 0.00157, 'sigma': 24}
    syst = make_system().finalized()
    occupation = manybody.lead_occupation(chemical_potential)
    spectrum = kwantspectrum.spectra(syst.leads)
    intervals = manybody.calc_intervals(spectrum, occupation)
    intervals[0].order = 10
    intervals[1].order = 8
    for interval in intervals:  # use simple quadrature
        interval.quadrature = 'gausslegendre'
    tasks = manybody.calc_tasks(intervals, spectrum, occupation)
    boundaries = leads.automatic_boundary(spectrum, tmax)
    psi_init = manybody.calc_initial_state(syst, tasks, boundaries,
                                           params=params)

    # check all types of the returned elements
    assert isinstance(psi_init, dict)
    assert len(psi_init) == intervals[0].order + intervals[1].order
    for i, (key, value) in enumerate(psi_init.items()):
        assert i == key
        assert isinstance(value, onebody.WaveFunction)


@pytest.mark.integtest
def test_calc_initial_state_with_kwant_failing():

    syst = make_system().finalized()
    occupation = manybody.lead_occupation(chemical_potential=3)
    spectrum = kwantspectrum.spectra(syst.leads)
    intervals = manybody.calc_intervals(spectrum, occupation)
    tasks = manybody.calc_tasks(intervals, spectrum, occupation)
    boundaries = [leads.SimpleBoundary(tmax=1)] * len(syst.leads)

    class ScatteringStatesRaise:
        """raise with a runtime error"""
        def __init__(self, *args, **kwargs):
            raise RuntimeError()

    # we just mock that state calculation fails
    with pytest.raises(RuntimeError) as exc:
        manybody.calc_initial_state(syst, tasks, boundaries,
                                    scattering_state_type=ScatteringStatesRaise)
    # we do not check for the exact energy value as this can change
    assert 'scattering state calculation failed for energy=' in str(exc.value)


@pytest.mark.integtest  # marker for integration tests
def test_manybody_wavefunction():
    syst = make_system().finalized()

    density_operator = kwant.operator.Density(syst)  # array
    sum_density_operator = kwant.operator.Density(syst, sum=True)  # only one element in array

    chemical_potential = 3
    tmax = 500
    time = 5
    params = {'v': 0.1, 't0': 0, 'A': 0.00157, 'sigma': 24}

    occupation = manybody.lead_occupation(chemical_potential)
    spectrum = kwantspectrum.spectra(syst.leads)
    intervals = manybody.calc_intervals(spectrum, occupation)
    for interval in intervals:  # use simple quadrature
        interval.quadrature = 'gausslegendre'
    tasks = manybody.calc_tasks(intervals, spectrum, occupation)
    boundaries = leads.automatic_boundary(spectrum, tmax)
    psi_init = manybody.calc_initial_state(syst, tasks, boundaries, params=params)

    state = manybody.WaveFunction(psi_init, tasks)
    state.evolve(time)
    assert state.time == time
    for _, psi in state.psi._data.items():
        assert psi.time == time
        assert psi.params == {'v': 0.1, 't0': 0, 'A': 0.00157, 'sigma': 24}

    # check return type, we expect an array running over all sites or just a single number
    density = state.evaluate(density_operator)
    sum_density = state.evaluate(sum_density_operator)
    assert isinstance(density, np.ndarray)
    assert density.shape == (len(syst.sites), )
    assert isinstance(sum_density, np.ndarray)
    assert sum_density.shape == ()

    # check that expectation value for onebody/manybody wavefunction are similar
    onebody_density = state.get_onebody_state(key=0).evaluate(density_operator)
    onebody_sum_density = state.get_onebody_state(key=0).evaluate(sum_density_operator)

    assert density.shape == onebody_density.shape
    assert sum_density.shape == onebody_sum_density.shape

    # TODO: check quadrature also for kronrod like rules

    # get all keys
    keys = state.get_keys()
    assert isinstance(keys, list)
    assert len(keys) == len(tasks)
    assert np.array([isinstance(x, int) for x in keys]).all()

    # get a new free key
    key = state.get_free_key()
    assert isinstance(key, int)
    assert key not in state.get_keys()

    # add a new onebody state
    class Task:
        weight = 0.5
    task = Task()
    psi = onebody.ScatteringStates(syst, lead=0, energy=2.4, tmax=tmax, params=params)[0]
    # print(len(tasks))
    # print(len(state.get_keys()))
    new_key = state.add_onebody_state(state=psi, task=task)
    # print(len(tasks))
    # print(len(state.get_keys())) # there is a problem with the length of tasks
    # TODO: should we make a deep copy of the tasks dict

    # add several states as a dict
    new_tasks = manybody.calc_tasks(intervals, spectrum, occupation, keys=itertools.count(50))
    new_psi = manybody.calc_initial_state(syst, new_tasks, boundaries, params=params)
    old_keys = state.get_keys()
    state.add_distributed_onebody_states(states=new_psi, tasks=new_tasks)
    assert len(state.get_keys()) == len(old_keys) + len(new_tasks)
    # TODO: maybe throw an error if keys already present, or at least with flag

    # add a state with user provided key
    my_new_key = 80
    new_key = state.add_onebody_state(state=psi, task=task, key=my_new_key)
    assert new_key == my_new_key
    # try to add twice with the same key
    raises(ValueError, state.add_onebody_state, state=psi, task=task, key=my_new_key)

    # retrieve a onebody state
    key = 1
    psi_retrieved = state.get_onebody_state(key=key)
    assert isinstance(psi_retrieved, onebody.WaveFunction)
    assert psi_retrieved.energy == tasks[key].energy
    # try to get a state that does not exist
    new_key = state.get_free_key()
    raises(ValueError, state.get_onebody_state, key=new_key)

    # delete a onebody state
    key = 4
    keys = state.get_keys()
    assert key in keys
    state.delete_onebody_state(key=key)
    assert key not in state.get_keys()
    raises(ValueError, state.delete_onebody_state, key)  # TODO: should we raise a key error here?
    assert len(state.get_keys()) == len(keys) - 1

    # evaluate an operator only on a subset of wavefunctions
    state.evolve(time=10)
    density = state.evaluate(density_operator)
    even_keys = [key for key in state.get_keys() if not key % 2]
    odd_keys = [key for key in state.get_keys() if key % 2]

    dens_even = state._calc_expectation_value(density_operator, keys=even_keys)
    dens_odd = state._calc_expectation_value(density_operator, keys=odd_keys)
    dens = state._calc_expectation_value(density_operator)
    assert_array_almost_equal(dens_even + dens_odd, dens)
    assert_array_almost_equal(dens, density)

    # get the shape of the weighting factor
    assert state.weight_shape() == tasks[0].weight.shape

    # check consistency
    assert state._check_consistency()
    del state.tasks[5]  # make state inconsistent
    assert state._check_consistency() is False

    # check wavefunction with the gauss-kronrod quadrature
    for interval in intervals:
        interval.quadrature = 'kronrod'
    tasks = manybody.calc_tasks(intervals, spectrum, occupation)
    boundaries = leads.automatic_boundary(spectrum, tmax)
    psi_init = manybody.calc_initial_state(syst, tasks, boundaries,
                                           params=params)

    state = manybody.WaveFunction(psi_init, tasks)
    state.evolve(time)

    # check return type, we expect an array running over all sites or just a single number
    density = state.evaluate(density_operator)
    sum_density = state.evaluate(sum_density_operator)

    assert isinstance(density, np.ndarray)
    assert density.shape == (2, len(syst.sites))
    assert isinstance(sum_density, np.ndarray)
    assert sum_density.shape == (2,)

    # check that if we add a state with a weight shape mismatch, that it crashes
    # TODO: this should fail, maybe one should give a clear error message and check for that case
    class Task:
        weight = 0.5  # not compatible to kronrod weight array
    task = Task()
    psi = onebody.ScatteringStates(syst, lead=0, energy=2.4, tmax=tmax, params=params)[0]
    new_key = state.add_onebody_state(state=psi, task=task)
    density = state.evaluate(density_operator)


@pytest.mark.integtest
def test_manybody_normalization():

    # integrating over all energies and leads, the density
    # should be 1 on all sites and for all times

    syst = make_system(W=3).finalized()
    density_operator = kwant.operator.Density(syst)

    chemical_potential = 100  # some value larger than any band energy
    tmax = 10
    params = {'v': 0.0001, 't0': 0, 'A': 0.00157, 'sigma': 24}

    occupation = manybody.lead_occupation(chemical_potential)

    spectrum = kwantspectrum.spectra(syst.leads)
    intervals = manybody.calc_intervals(spectrum, occupation)
    tasks = manybody.calc_tasks(intervals, spectrum, occupation)
    boundaries = leads.automatic_boundary(spectrum, tmax)
    psi_init = manybody.calc_initial_state(syst, tasks, boundaries, params=params)
    wf = manybody.WaveFunction(psi_init, tasks)

    for time in [0, 5, 10]:
        wf.evolve(time)
        density = wf.evaluate(density_operator)
        assert_array_almost_equal(density, 1, decimal=2)


@pytest.mark.integtest
def test_simple_manybody_regression():

    # a simple regression test to make sure that the result does not change
    # over the time

    syst = make_system(W=3).finalized()
    density_operator = kwant.operator.Density(syst, sum=True)

    chemical_potential = 5
    tmax = 20
    params = {'v': 0.1, 't0': 0, 'A': 0.157, 'sigma': 24}

    occupation = manybody.lead_occupation(chemical_potential)

    spectrum = kwantspectrum.spectra(syst.leads)
    intervals = manybody.calc_intervals(spectrum, occupation)
    tasks = manybody.calc_tasks(intervals, spectrum, occupation)
    boundaries = leads.automatic_boundary(spectrum, tmax)
    psi_init = manybody.calc_initial_state(syst, tasks, boundaries, params=params)
    wf = manybody.WaveFunction(psi_init, tasks)

    ref_densities = [53.320067790628464, 24.312454606515075, 81.04149821826338]
    for i, time in enumerate([0, 10, 20]):
        wf.evolve(time)
        density = wf.evaluate(density_operator)[1]
        assert_almost_equal(density, ref_densities[i], decimal=6)


# ---- check state
@pytest.mark.integtest  # marker for integration tests
def test_manybody_state():

    syst = make_system().finalized()
    density_operator = kwant.operator.Density(syst)

    chemical_potential = 3
    tmax = 500
    time = 5
    params = {'v': 0.0001, 't0': 0, 'A': 0.00157, 'sigma': 24}

    occupation = manybody.lead_occupation(chemical_potential)

    # reference result with the manybody wavefunction
    spectrum = kwantspectrum.spectra(syst.leads)
    intervals = manybody.calc_intervals(spectrum, occupation)
    tasks = manybody.calc_tasks(intervals, spectrum, occupation)
    boundaries = leads.automatic_boundary(spectrum, tmax)
    psi_init = manybody.calc_initial_state(syst, tasks, boundaries, params=params)
    wf = manybody.WaveFunction(psi_init, tasks)
    wf.evolve(time)
    density_wf = wf.evaluate(density_operator)[1]

    # manybody state
    state = manybody.State(syst, tmax, occupation, params=params, refine=False)

    state.evolve(time)
    assert state.time == time
    # the manybody state has no public params stored, only each onebody state
    # has a public params dictionary
    for _, psi in state.manybody_wavefunction.psi._data.items():
        assert psi.time == time
        assert psi.params == {'v': 0.0001, 't0': 0, 'A': 0.00157, 'sigma': 24}

    # check that result is similar to reference result
    density = state.evaluate(density_operator)
    assert_array_almost_equal(density, density_wf)

    # -- test get_intervals
    intervals = state.get_intervals()
    assert isinstance(intervals, list)
    assert np.array([isinstance(x, manybody.Interval) for x in intervals]).all()

    # -- test estimate_error
    error_per_interval = state.estimate_error(intervals=intervals)
    assert isinstance(error_per_interval, np.ndarray)
    assert len(error_per_interval) == len(intervals)
    assert np.array([isinstance(x, float) for x in error_per_interval]).all()

    err_sum = 0
    for i, interval in enumerate(intervals):
        error = state.estimate_error(intervals=interval)
        assert isinstance(error, float)
        assert error == error_per_interval[i]
        err_sum += state.estimate_error(intervals=interval, full_output=True)
        assert isinstance(err_sum, np.ndarray)

    # the total error is NOT the sum of interval errors (triangle inequality)
    total_error = state.estimate_error()
    assert np.allclose(total_error, np.max(err_sum))

    # -- unknown interval should raise an error
    interval = intervals[0]
    interval.kmin += 0.5 * (interval.kmax - interval.kmin)
    raises(KeyError, state.estimate_error, intervals=interval)

    # -- test refine_intervals
    # -- test time before refining the intervals
    for key in state.manybody_wavefunction.get_keys():
        psi = state.manybody_wavefunction.get_onebody_state(key)
        assert psi.time == state.time
    # -- refine_intervals
    error_before = state.estimate_error()
    state.refine_intervals(atol=1E-3, rtol=1E-3)
    error_after = state.estimate_error()
    assert error_after < error_before
    # -- test time after refining the intervals
    for key in state.manybody_wavefunction.get_keys():
        psi = state.manybody_wavefunction.get_onebody_state(key)
        assert psi.time == state.time

    # add boundstates.
    # emulate the boundstates by some arbitrary onebody states
    # as the boundstates have zero weight, the result must be indentical
    # to the result without boundstates
    def make_psi(energy):
        return onebody.ScatteringStates(syst, lead=0, energy=energy,
                                        tmax=tmax, params=params)[0]
    boundstate_tasks = {'b1': onebody.Task(weight=0, energy=2.1, lead=None, mode=None),
                        'b2': onebody.Task(weight=0, energy=2.3, lead=None, mode=None)}
    boundstate_psi = {key: make_psi(task.energy) for key, task in boundstate_tasks.items()}

    # -- check that adding boundstates do not change error, intervals and observable
    intervals_before = state.get_intervals()
    error_per_interval_before = state.estimate_error(intervals=intervals_before)
    total_error_before = state.estimate_error()
    density_before = state.evaluate(density_operator)
    keys_before = state.manybody_wavefunction.get_keys()

    state.add_boundstates(boundstate_psi, boundstate_tasks)

    intervals_after = state.get_intervals()
    error_per_interval_after = state.estimate_error(intervals=intervals_after)
    total_error_after = state.estimate_error()
    density_after = state.evaluate(density_operator)
    keys_after = state.manybody_wavefunction.get_keys()

    for interval_before, interval_after in zip(intervals_before, intervals_after):
        assert interval_before == interval_after
    assert total_error_before == total_error_after
    assert_array_almost_equal(error_per_interval_before, error_per_interval_after)
    assert_array_almost_equal(density_before, density_after)

    assert keys_before + list(boundstate_tasks.keys()) == keys_after

    # -- check that the state can still be evolved and gives the same result as wavefunction
    time += 5
    state.evolve(time)
    density = state.evaluate(density_operator)

    wf.evolve(time)
    density_wf = state.evaluate(density_operator)

    assert_array_almost_equal(density, density_wf)

    # -- check that refine_intervals still works
    error_before = state.estimate_error()
    state.refine_intervals(atol=1E-4, rtol=1E-4)
    error_after = state.estimate_error()
    assert error_after < error_before

    # -- check to add user given intervals, precalculate
    ModInterval = functools.partial(manybody.Interval, order=3, integration_variable='energy')
    intervals = manybody.calc_intervals(spectrum, occupation, interval_type=ModInterval)
    state = manybody.State(syst, tmax, occupation, params=params, intervals=intervals, refine=False)
    intervals = state.get_intervals()
    for interval in intervals:
        assert interval.order == 3
        assert interval.integration_variable == 'energy'

    # -- check to add user given intervals, new default
    ModInterval = functools.partial(manybody.Interval, order=3, integration_variable='energy')
    state = manybody.State(syst, tmax, occupation, params=params, intervals=ModInterval, refine=False)
    intervals = state.get_intervals()
    for interval in intervals:
        assert interval.order == 3
        assert interval.integration_variable == 'energy'

    # -- check state with default occupation
    occupation_mu_0 = manybody.lead_occupation(chemical_potential=0)
    state_mu_0 = manybody.State(syst, tmax, occupation_mu_0, params=params, refine=False)
    state_default = manybody.State(syst, tmax=tmax, params=params, refine=False)
    assert state_mu_0.occupations[0].energy_range == state_default.occupations[0].energy_range

    # test for missing input
    raises(ValueError, manybody.State, syst=syst, params=params)
    # test for system not finalized
    raises(TypeError, manybody.State, syst=make_system(), tmax=5, params=params)
    # test for mutual exclusive arguments
    raises(ValueError, manybody.State, syst, tmax, boundaries=boundaries, params=params)

    params_with_time = {'v': 0.1, 't0': 0, 'A': 0.00157, 'sigma': 24, 'time': 0}
    with pytest.raises(KeyError) as exc:
        manybody.State(syst, tmax, params=params_with_time)
    error_string = str(exc.value).strip('\"')  # remove etra quotes
    assert error_string == "'params' must not contain time"

    # TODO, check general parameter handling in manybody.State
    # no params passed at all
    # with pytest.raises(TypeError) as exc:
    # manybody.State(syst, tmax)
    # assert str(exc.value) == 'System is missing required arguments: "v"'

    # params_without_sigma = {'v': 0.1, 't0': 0, 'A':0.00157}
    # with pytest.raises(TypeError) as exc:
    #    manybody.State(syst, tmax, params=params_without_sigma)
    # assert str(exc.value) == 'System is missing required arguments: "sigma"'


@pytest.mark.integtest  # marker for integration tests
def test_manybody_state_initial_refine():

    syst = make_system().finalized()

    tmax = 500
    params = {'v': 0.0001, 't0': 0, 'A': 0.00157, 'sigma': 24}

    occupation = manybody.lead_occupation(chemical_potential=3)

    state = manybody.State(syst, tmax, occupation, params=params, refine=False)
    intervals = state.get_intervals()
    assert len(intervals) == 2

    state = manybody.State(syst, tmax, occupation, params=params)
    intervals = state.get_intervals()
    assert len(intervals) == 13


@pytest.mark.integtest  # marker for integration tests
def test_manybody_state_refine_non_kronrod():

    # test that refinement acts only on the gauss-kronrod intervals
    # and that additional other intervals (here gauss-legendre in the example)
    # are not touched by refine_intervals()

    syst = make_system().finalized()

    tmax = 500
    params = {'v': 0.0001, 't0': 0, 'A': 0.00157, 'sigma': 24}

    occupation = manybody.lead_occupation(chemical_potential=3)

    state = manybody.State(syst, tmax, occupation, params=params, refine=False)
    intervals = state.get_intervals()
    assert len(intervals) == 2

    for interval in intervals:
        interval.quadrature = 'gausslegendre'
        state._add_interval(interval)

    intervals = state.get_intervals()
    assert len(intervals) == 4  # 2 + 2 intervals

    state.refine_intervals()
    intervals = state.get_intervals()
    assert len(intervals) == 15  # 13 + 2 intervals


@pytest.mark.integtest
def test_state_estimate_error():

    syst = make_system().finalized()
    density_sum = kwant.operator.Density(syst, sum=True)
    density_operator = kwant.operator.Density(syst)
    current_operator = kwant.operator.Current(syst)

    chemical_potential = 3
    tmax = 500
    params = {'v': 0.0001, 't0': 0, 'A': 0.00157, 'sigma': 24}

    occupation = manybody.lead_occupation(chemical_potential)
    state = manybody.State(syst, tmax, occupation, params=params, refine=False)

    shape_density_sum = state.evaluate(density_sum).shape
    shape_density = state.evaluate(density_operator).shape
    shape_current = state.evaluate(current_operator).shape

    assert shape_density_sum == ()
    assert shape_density_sum != shape_density  # make sure to measure not the same
    assert shape_density_sum != shape_current  # make sure to measure not the same
    assert shape_density != shape_current  # make sure to measure not the same

    intervals = state.get_intervals()

    # --- density is the default operator to measure the error

    # maximum error, summed over all intervals
    errors = state.estimate_error()
    assert errors.shape == ()

    # error over array, summed over all intervals
    errors = state.estimate_error(full_output=True)
    assert errors.shape == shape_density

    # maximum error per interval
    errors = state.estimate_error(intervals=intervals)
    assert errors.shape == (len(intervals),)

    # error over array per interval
    errors = state.estimate_error(intervals=intervals, full_output=True)
    assert errors.shape == (len(intervals),) + shape_density

    # maximum error of a single interval
    errors = state.estimate_error(intervals=intervals[0])
    assert errors.shape == ()

    # error over array of a single interval
    errors = state.estimate_error(intervals=intervals[0], full_output=True)
    assert errors.shape == shape_density

    # --- measure the error with the current operator

    # maximum error, summed over all intervals
    errors = state.estimate_error(error_op=current_operator)
    assert errors.shape == ()

    # error over array, summed over all intervals
    errors = state.estimate_error(error_op=current_operator, full_output=True)
    assert errors.shape == shape_current

    # maximum error per interval
    errors = state.estimate_error(error_op=current_operator, intervals=intervals)
    assert errors.shape == (len(intervals),)

    # error over array per interval
    errors = state.estimate_error(error_op=current_operator, intervals=intervals, full_output=True)
    assert errors.shape == (len(intervals),) + shape_current

    # -- an operator with a scalar output

    # maximum error, summed over all intervals
    errors = state.estimate_error(error_op=density_sum)
    assert errors.shape == ()

    # error over array, summed over all intervals
    errors = state.estimate_error(error_op=density_sum, full_output=True)
    assert errors.shape == shape_density_sum

    # maximum error per interval
    errors = state.estimate_error(error_op=density_sum, intervals=intervals)
    assert errors.shape == (len(intervals),)

    # error over array per interval
    errors = state.estimate_error(error_op=density_sum, intervals=intervals, full_output=True)
    assert errors.shape == (len(intervals),) + shape_density_sum

    # --- set current operator as default from the beginning

    state = manybody.State(syst, tmax, occupation, params=params,
                           error_op=current_operator, refine=False)

    errors = state.estimate_error()
    assert errors.shape == ()

    # error over array, summed over all intervals
    errors = state.estimate_error(full_output=True)
    assert errors.shape == shape_current

    # maximum error per interval
    errors = state.estimate_error(intervals=intervals)
    assert errors.shape == (len(intervals),)

    # error over array per interval
    errors = state.estimate_error(intervals=intervals, full_output=True)
    assert errors.shape == (len(intervals),) + shape_current


@pytest.mark.integtest  # marker for integration tests
def test_manybody_state_estimate_error_non_kronrod():

    syst = make_system().finalized()

    tmax = 500
    params = {'v': 0.0001, 't0': 0, 'A': 0.00157, 'sigma': 24}

    occupation = manybody.lead_occupation(chemical_potential=3)

    state = manybody.State(syst, tmax, occupation, params=params, refine=False)
    intervals = state.get_intervals()
    gauss_interval = intervals[0]
    gauss_interval.quadrature = 'gausslegendre'

    with pytest.raises(ValueError) as exc:
        state.estimate_error(intervals=gauss_interval)
    assert str(exc.value) in "quadpack error estimate works only on Gauss-Kronrod quadrature intervals"


@pytest.mark.integtest  # marker for integration tests
def test_time_name_and_start_default_change_manybody_state():

    N = 3
    lat = kwant.lattice.square(norbs=2)
    I0 = ta.identity(2)
    SZ = ta.array([[1, 0], [0, -1]])
    uniform = kwant.digest.uniform

    tmax = 100
    params = {'salt': '1'}
    occupation = manybody.lead_occupation(chemical_potential=1)

    def make_simple_lead(lat, N):
        I0 = ta.identity(lat.norbs)
        syst = kwant.Builder(kwant.TranslationalSymmetry((-1, 0)))
        syst[(lat(0, j) for j in range(N))] = 4 * I0
        syst[lat.neighbors()] = -1 * I0
        return syst

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

    density_operator_time = kwant.operator.Density(fsyst_time)
    density_operator_zeit = kwant.operator.Density(fsyst_zeit)

    # default
    state_time = manybody.State(fsyst_time, tmax, occupation, params=params, refine=False)

    # default changed
    WaveFunction_zeit = functools.partial(onebody.WaveFunction.from_kwant, time_name='zeit',
                                          time_start=zeit_offset)
    scattering_state_zeit = functools.partial(onebody.ScatteringStates,
                                              wavefunction_type=WaveFunction_zeit)
    state_zeit = manybody.State(fsyst_zeit, tmax, occupation, params=params,
                                scattering_state_type=scattering_state_zeit, refine=False)

    for time in (0., 1., 5.):

        state_time.evolve(time)
        state_zeit.evolve(time + zeit_offset)

        for _, psi in state_time.manybody_wavefunction.psi._data.items():
            assert psi.time == time
            assert psi.time_start == 0
            assert psi.time_name == 'time'

        for _, psi in state_zeit.manybody_wavefunction.psi._data.items():
            assert psi.time == time + zeit_offset
            assert psi.time_start == zeit_offset
            assert psi.time_name == 'zeit'

        # check that result is similar to default result
        density_time = state_time.evaluate(density_operator_time)
        density_zeit = state_time.evaluate(density_operator_zeit)
        assert_array_almost_equal(density_time, density_zeit)

    for t0 in [1 + 1j, 'a', None, -float('inf'), float('inf')]:
        WaveFunction_zeit = functools.partial(onebody.WaveFunction.from_kwant, time_name='zeit',
                                              time_start=t0)
        scattering_state_zeit = functools.partial(onebody.ScatteringStates,
                                                  wavefunction_type=WaveFunction_zeit)
        with pytest.raises(TypeError) as exc:
            manybody.State(fsyst_zeit, tmax, occupation, params=params,
                           scattering_state_type=scattering_state_zeit, refine=False)
        assert str(exc.value) == "time must be a finite real number"


@pytest.mark.integtest
def test_evaluate_integrand():

    syst = make_system().finalized()
    density_operator = kwant.operator.Density(syst)

    tmax = 10
    time = 1  # timestep we like to evaluate the integrand
    params = {'v': 0.0001, 't0': 0, 'A': 0.00157, 'sigma': 24}

    occupation = manybody.lead_occupation(chemical_potential=3)
    state = manybody.State(syst, tmax, occupation, params=params, refine=False)
    state.evolve(time)

    # calculate the integrand on an integral with the state
    interval = manybody.Interval(lead=0, band=0, kmin=0.02, kmax=0.1)
    state._add_interval(interval)
    density_shape = state.evaluate(density_operator).shape
    abcissa, integrand = state._calc_integrand(interval, density_operator)

    # test type and shape
    assert isinstance(abcissa, np.ndarray)
    assert isinstance(integrand, np.ndarray)
    assert abcissa.shape == (2 * interval.order + 1,)
    assert integrand.shape == (2 * interval.order + 1,) + density_shape

    # evaluate the integrand with the separate debug routine on all abcissa point
    # and check if we obtain identical results
    manybody_integrand = manybody.ManybodyIntegrand(syst, interval, density_operator,
                                                    time=time, params=params)
    integ = np.array([manybody_integrand.func(k) for k in abcissa])

    assert manybody_integrand.func(0.05).shape == density_shape
    assert_array_almost_equal(integ, integrand)


def test_calc_energy_cutoffs():

    class Occupation:
        def __init__(self, energy_range):
            self.energy_range = energy_range

    # ----- just one lead

    occupation = Occupation(energy_range=[(-5, 1), (2, 3)])
    emin, emax = manybody.calc_energy_cutoffs(occupation)

    assert emin == -5
    assert emax == 3

    occupation = Occupation(energy_range=[(None, 1), (2, 3)])
    emin, emax = manybody.calc_energy_cutoffs(occupation)

    assert emin is None
    assert emax == 3

    occupation = Occupation(energy_range=[(-5, 1), (2, None)])
    emin, emax = manybody.calc_energy_cutoffs(occupation)

    assert emin == -5
    assert emax is None

    occupation = Occupation(energy_range=[(None, 1), (2, None)])
    emin, emax = manybody.calc_energy_cutoffs(occupation)

    assert emin is None
    assert emax is None

    # ----- several leads

    occup1 = Occupation(energy_range=[(-5, 1)])
    occup2 = Occupation(energy_range=[(-4, 1.5), (2, 3)])
    emin, emax = manybody.calc_energy_cutoffs([occup1, occup2])

    assert emin == -5
    assert emax == 3

    occup1 = Occupation(energy_range=[(-5, None)])
    occup2 = Occupation(energy_range=[(None, 1.5), (2, 3)])
    emin, emax = manybody.calc_energy_cutoffs([occup1, occup2])

    assert emin is None
    assert emax is None

    # ----- several leads, one lead not occupied

    occup1 = Occupation(energy_range=[(-5, 1)])
    occup2 = Occupation(energy_range=[(-4, 1.5), (2, 3)])

    emin, emax = manybody.calc_energy_cutoffs([occup1, occup2, None])

    assert emin == -5
    assert emax == 3

    # ----- no lead is occupied
    emin, emax = manybody.calc_energy_cutoffs(None)

    assert emin is None
    assert emax is None
