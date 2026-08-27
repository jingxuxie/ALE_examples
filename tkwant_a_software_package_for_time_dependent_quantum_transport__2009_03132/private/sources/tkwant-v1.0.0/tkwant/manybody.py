# -*- coding: utf-8 -*-
# Copyright 2016-2020 tkwant authors.
#
# This file is part of tkwant.  It is subject to the license terms in the file
# LICENSE.rst found in the top-level directory of this distribution and at
# http://kwant-project.org/license.  A list of tkwant authors can be found in
# the file AUTHORS.rst at the top-level directory of this distribution and at
# http://kwant-project.org/authors.
"""Tools for calculating time-dependent, manybody quantities."""

import collections.abc
import functools as ft
import itertools
import copy
import numpy as np

import kwant
import kwantspectrum


from . import onebody, leads, integration, mpi, _common, _logging
from .system import add_time_to_params


__all__ = ['Occupation', 'Interval', 'lead_occupation',
           'calc_intervals', 'split_intervals', 'combine_intervals',
           'calc_tasks', 'calc_initial_state', 'calc_energy_cutoffs',
           'WaveFunction', 'State', 'make_boundstates_time_dependent',
           'add_boundstates', 'ManybodyIntegrand']


# set module logger
logger = _logging.make_logger(name=__name__)
log_func = _logging.log_func(logger)

# TODO: reintroduce dataclasses at some point when python 3.7 is stable


class Occupation:
    """Data format for the lead occupation, see `tkwant.manybody.lead_occupation`.

    Attributes
    ----------
    distribution : callable
        distribution function
    energy_range : sequence, optional
        Energy cutoffs.
    bands : sequence, optional
        Selected bands.
    """
    def __init__(self, distribution, energy_range=None, bands=None):
        self.distribution = distribution
        self.energy_range = energy_range
        self.bands = bands

    def __str__(self):
        string = "lead occupation: " \
                 "distribution={distribution}, energy_range={energy_range} , " \
                 "bands={bands}".format(**self.__dict__)
        return string


class Interval:
    """Data format for a quadrature interval, see `tkwant.manybody.calc_intervals`.

    Attributes
    ----------
    lead : int
        lead index
    band : int
        band index (*n*)
    kmin : float
        lower momentum (:math:`k`) bound
    kmax : float
        upper momentum (:math:`k`) bound
    order : int, optional
        Integration rule order to be applied on the interval.
        See `tkwant.integration.calc_abscissas_and_weights`.
    quadrature : string, optional
        Integration quadrature to be applied on the interval.
        See `tkwant.integration.calc_abscissas_and_weights`.
    integration_variable : string, optional
        The variable of integration (in general energy or momentum).
        See `tkwant.manybody.calc_tasks`.
    """
    def __init__(self, lead: int, band: int, kmin: float, kmax: float, order: int = 10,
                 quadrature: str = "kronrod", integration_variable: str = "momentum"):
        self.lead = lead
        self.band = band
        self.kmin = kmin
        self.kmax = kmax
        self.order = order
        self.quadrature = quadrature
        self.integration_variable = integration_variable

    def __eq__(self, other) -> bool:
        if not isinstance(other, Interval):
            return NotImplemented
        return (
            (self.lead, self.band, self.kmin, self.kmax, self.order,
             self.quadrature, self.integration_variable) ==
            (other.lead, other.band, other.kmin, other.kmax, other.order,
             other.quadrature, other.integration_variable))

    def __hash__(self) -> int:
        return hash((self.lead, self.band, self.kmin, self.kmax, self.order,
                     self.quadrature, self.integration_variable))

    def __str__(self):
        string = "quadrature interval: " \
                 "lead={lead}, band={band}, kmin={kmin:.6f}, kmax={kmax:.6f}, " \
                 "order={order}, quadrature={quadrature}, "\
                 "integration_variable={integration_variable}".format(**self.__dict__)
        return string


# occupation

def _fermi_function_below_epsilon(temperature, epsilon=1E-10):
    """Return the energy *E* above which 1/(1 + exp(E/T)) < epsilon"""
    assert _common.is_type(temperature, 'real_number')
    assert _common.is_type(epsilon, 'real_number')
    assert temperature > 0
    assert 0 < epsilon < 1
    return temperature * np.log((1 - epsilon) / epsilon)


@log_func
def lead_occupation(chemical_potential=0, temperature=0, energy_range=None,
                    bands=None, distribution=None, occupation_type=Occupation):
    r"""Set the occupation (:math:`T, \mu, f(E)`) for one lead.

    The main purpose of this routine is to obtain upper energy cutoffs, in order
    to calculate integrals of the form :math:`I = \int d E \, f(E) \ldots`.
    Energy cutoffs are estimated from the distribution function *f(E)* only,
    without knowledge of the band structure. Three cases can be distinguished:

    * Fermi dirac distribution :math:`f(E) = (1 + \exp((E - \mu)/T))^{-1}`

        For *T = 0*: :math:`f(E) = \theta(\mu - E)` the chemical
        potential (Fermi energy) is a sharp upper cutoff,
        :math:`I = \int_{-\infty}^\mu d E \, \ldots`.

        For *T > 0* we estimate an effective upper cutoff *Eeff*, such that
        :math:`f(E) \leq \varepsilon` for :math:`E \geq Eeff`,
        :math:`I = \int_{-\infty}^{Eeff} d E \, f(E) \ldots`.

    * Arbitrary distribution function:
        No cutoff is estimated,
        :math:`I = \int_{-\infty}^{\infty} d E \, f(E) \ldots`.

    It is possible to overwrite all cutoffs by user given values,
    except the upper energy cutoff `emax` at *T = 0*, which is
    always set to min(:math:`\mu`, `emax`).

    Parameters
    ----------
    chemical_potential : float, optional
        chemical potential :math:`\mu`, zero by default
    temperature : float, optional
        temperature :math:`T`, default: zero temperature
    energy_range : sequence, optional
        Sequence of energy intervals, to overwrite the upper and lower cutoff
        chosen by the routine. Each interval has the form `(emin, emax)`, with
        `emin` and `emax` being real numbers or None.
        It is required that ``emin`` :math:`\leq` ``emax`` in each interval, but
        the intervals are not required to be sorted in the sequence.
        Moreover, no check is performed if the intervals overlap.
        Setting ``emin`` and/or ``emax`` to `None`, means the absence of a
        lower (respect. upper) energy bound. ``energy_range = None`` is
        interpreted as ``energy_range = [(None, None)]``, meaning no
        energy bounds, which is the default behavior.
    bands : int or list of int, optional
        If present, only bands with band indices (*n*) present in the list
        are taken into account. (`emin` and `emax` still limit the energy range
        of these bands.). By default, all bands are considered.
    distribution : callable, optional
        Distribution function *f(E)*, over which the thermal average is taken.
        Calling signature must be `(chemical_potential, temperature, energy)`.
        Default: non-interacting Fermi dirac distribution.
    occupation_type : `~dataclasses.dataclass`, optional
        Data format of the returnded ``occupation`` object
        to store the lead occupation. Default: `tkwant.manybody.Occupation`.

    Returns
    -------
    occupation : ``occupation_type`` or `None`
        Lead occupation.
        Attributes of ``occupation`` that are modified by this routine:

            - `distribution` : callable, distribution function *f(E)*,
              calling signature `(energy)`
            - `energy_range` : sequence, energy cutoffs
            - `bands` : list of int, bands to be considered

        If the lead is found to be not occupied (e.g.\ by setting ``emin`` >
        ``chemical_potential`` at zero temperature),  the routine returns None.
    """
    def _fermi_dirac_distribution(energy):
        """Fermi diract distribution function"""
        return 1. / (1 + np.exp((energy - chemical_potential) / temperature))

    def _zero_temperature_fermi_dirac_distribution(energy):
        """Fermi diract distribution function"""
        return np.where(energy <= chemical_potential, 1, 0)

    def _check_energies(emin, emax):
        if emin is not None and not _common.is_type(emin, 'real_number'):
            raise TypeError('emin={} in energy_range not a real number.'
                            .format(emin))
        if emax is not None and not _common.is_type(emax, 'real_number'):
            raise TypeError('emax={} in energy_range not a real number.'
                            .format(emax))
        if emin is not None and emax is not None:
            if emax < emin:
                raise ValueError('emin={} > emax={}'.format(emin, emax))

    if not _common.is_type(chemical_potential, 'real_number'):
        raise TypeError('chemical potential must be a real number.')

    if not _common.is_type(temperature, 'real_number'):
        raise TypeError('temperature must be a real number.')

    if temperature < 0:
        raise ValueError('temperature={} is negative.'.format(temperature))

    if distribution is None:  # use fermi dirac distribution
        if np.isclose(temperature, 0):
            logger.info('distribution function: zero-temperature fermi-dirac')
            distribution = _zero_temperature_fermi_dirac_distribution
            # chemical potential is upper energy cutoff for zero-temp. fermi dirac
            if energy_range is not None:
                _energy_range = []
                for (emin, emax) in energy_range:
                    _check_energies(emin, emax)
                    if emax is None:
                        emax = chemical_potential
                    else:
                        emax = min(chemical_potential, emax)
                    if emin is None or (emin is not None and emin < emax):
                        _energy_range.append((emin, emax))
            else:
                _energy_range = [(None, chemical_potential)]
        else:
            logger.info('distribution function: finite-temperature fermi-dirac')
            distribution = _fermi_dirac_distribution
            effective_emax = chemical_potential + _fermi_function_below_epsilon(temperature)
            # give the possibility to overwrite calculated energy cutoff
            if energy_range is not None:
                _energy_range = []
                for i, (emin, emax) in enumerate(energy_range):
                    _check_energies(emin, emax)
                    if emax is None:
                        emax = effective_emax
                    if emin is None or (emin is not None and emin < emax):
                        _energy_range.append((emin, emax))
            else:
                _energy_range = [(None, effective_emax)]
    else:
        logger.info('distribution function: provided by user')
        # no upper energy cutoff for arbitrary distribution
        distribution = ft.partial(distribution, chemical_potential, temperature)
        if energy_range is None:
            _energy_range = [(None, None)]
        else:
            _energy_range = copy.deepcopy(energy_range)

    _bands = copy.deepcopy(bands)
    if _bands is not None:
        try:
            _bands = sorted(set(list(_bands)))
        except TypeError:  # if bands is just a single integer
            _bands = [_bands]
    if _energy_range:
        return occupation_type(distribution, _energy_range, _bands)


# selection of the energy/momentum integration region

def _calc_momentum_intervals(spectrum, emin=None, emax=None, bands=None):
    r"""Get the momentum intervals for one lead.

    Parameters
    ----------
    spectrum : `~kwantspectrum.spectrum`
        Energy dispersion :math:`E_n(k)` of one lead.
    emin : int or float, optional
        Minimum band energy.
        If present, select intervals such that :math:`E_n(k) \geq` `emin`.
        Default: no lower energy cutoff.
    emax : int or float, optional
        Maximum band energy.
        If present, select intervals such that :math:`E_n(k) \leq` `emax`.
        Default: no upper energy cutoff, only `chemical_potential`
        will serve as a cutoff for the default fermi dirac distribution.
    bands : list of int, optional
        If present, only bands with band indices (*n*) present in the list
        are taken into account. (`emin` and `emax` still limit the energy range
        of these bands.)

    Returns
    -------
    intervals : list
        List of all momentum intervals in the form `(band, (kmin, kmax))`
        where `band` is the band index (*n*), and `kmin` respectively `kmax` are
        the minimum, respectively maximum values of the momentum (*k*) interval.
        The length of the list depends on the lead spectrum and is not known
        a priori.
    """

    def positive_velocity_intervals(band):
        """Momentum intervals with emin < energy < emax and positive velocity"""
        intervals_valid_energy = spectrum.intervals(band, lower=emin, upper=emax)
        intervals_positve_velocity = spectrum.intervals(band, lower=0,
                                                        derivative_order=1)
        return kwantspectrum.intersect_intervals(
            intervals_valid_energy, intervals_positve_velocity)

    if bands is None:
        bands = range(spectrum.nbands)
    assert _common.is_type_array(bands, 'integer').all()

    return [(band, interval) for band in bands
            for interval in positive_velocity_intervals(band)
            if _common.is_not_empty(interval)]


@log_func
def calc_intervals(spectra, occupations, interval_type=Interval):
    r"""Return a list of momentum intervals to perform the manybody integration.

    Parameters
    ----------
    spectra : `kwantspectrum.spectrum` or sequence thereof
        Energy dispersion :math:`E_n(k)` of one lead or sequence thereof
        in case of several leads.
    occupations : `tkwant.manybody.Occupation` or sequence thereof
        Each sequence element represents the occupation of a lead.
        If ``occupations`` consistst of only one element or if the
        sequence has only one element, the occupation is assumed to be
        identical in each lead. If ``occupations`` is a sequence with more than
        one element, such that the occupation for each lead is different,
        ``occupations`` must have the same length as ``spectra``.
        If a lead is occupied, the corresponding ``occupations`` element
        must have the following two attributes:

            - `energy_range` : sequence of energy bounds in form `(emin, emax)`
              (`emin` :math:`\leq E_n(k) \leq` `emax`), no bound if
              `emin` and/or `emax` is set to `None`.
            - `bands` : list of int, bands to be considered,
              all bands considered if `None`

        If a lead is not occupied, the corresponding element of ``occupations``
        must be `None` or `False`.
    interval_type : `~dataclasses.dataclass`, optional
        Data format to store an interval in the returned ``intervals`` list.
        Default: `tkwant.manybody.Interval`

    Returns
    -------
    intervals :  list of ``interval_type``
        All momentum intervals to perform the statistical average.
        Attributes of each ``intervals`` element that are modified by this routine:

            - `lead` : int, lead index
            - `band` : int, band index (*n*)
            - `kmin` : float, lower momentum (:math:`k`) bound
            - `kmax` : float, upper momentum (:math:`k`) bound
    """

    def calc_intervals_per_lead(lead, occupation, spectrum):
        """Intervals and quadrature rule for a single lead."""
        bands = occupation.bands
        if occupation.energy_range is None:
            emin = None
            emax = None
            lead_intervals = [interval_type(lead, band, kmin, kmax)
                              for band, (kmin, kmax) in
                              _calc_momentum_intervals(spectrum, emin, emax, bands)]
        else:
            lead_intervals = []
            for (emin, emax) in occupation.energy_range:
                lead_intervals += [interval_type(lead, band, kmin, kmax)
                                   for band, (kmin, kmax) in
                                   _calc_momentum_intervals(spectrum,
                                                            emin, emax, bands)]
        return lead_intervals

    if not isinstance(spectra, collections.abc.Iterable):
        spectra = [spectra]
    if not isinstance(occupations, collections.abc.Iterable):
        occupations = [occupations]

    uniform_occupation = False
    if len(occupations) == 1:
        logger.debug('occupation in all leads assumed identical for interval calculation')
        uniform_occupation = True
    if not uniform_occupation and len(occupations) != len(spectra):
        raise ValueError('Occupation and spectra must have the same length.')

    intervals = []
    for lead, spectrum in enumerate(spectra):
        if uniform_occupation:
            occupation = occupations[0]
        else:
            occupation = occupations[lead]
        if occupation:
            intervals_per_lead = calc_intervals_per_lead(lead, occupation, spectrum)
            if _common.is_not_empty(intervals_per_lead):
                intervals += intervals_per_lead
    return intervals


def _split_interval(interval, number_subintervals):
    """Divide an interval into `number_subintervals` equidistant intervals.

    Parameters
    ----------
    interval : `tkwant.manybody.Interval`
        A momentum interval.
        An ``interval`` must have at least the following two attributes:

            - `kmin` : float, lower momentum bound
            - `kmax` : float, upper momentum bound
    number_subintervals : int
        number of subintervals in which ``interval`` will be divided.
        `number_subintervals` must be larger zero.

    Returns
    -------
    intervals : list
        List of `tkwant.manybody.Interval`. All attributes are copied,
        only the values for the `kmin` and `kmax` attribute are changed.
        The number of list elements is `number_subintervals`.
    """

    if number_subintervals <= 0:
        raise ValueError("split number={} must be positive and larger zero."
                         .format(number_subintervals))
    assert _common.is_type(number_subintervals, 'integer')

    interval = copy.deepcopy(interval)

    if number_subintervals == 1:
        return [interval]

    dkint = (interval.kmax - interval.kmin) / number_subintervals
    interval.kmax = interval.kmin + dkint

    def make_new_interval(dk):
        new_interval = copy.deepcopy(interval)
        new_interval.kmin += dk
        new_interval.kmax += dk
        return new_interval

    return [make_new_interval(i * dkint) for i in range(number_subintervals)]


def split_intervals(intervals, number_subintervals):
    """Divide each interval in `number_subintervals` equidistant intervals.

    Parameters
    ----------
    intervals : sequence of `tkwant.manybody.Interval`
        Momentum intervals to perform the statistical average.
        Each ``intervals`` sequence element must have at least
        the following two attributes:

            - `kmin` : float, lower momentum bound
            - `kmax` : float, upper momentum bound

    number_subintervals : int
        number of subintervals in which each element of ``intervals`` in will
        be divided

    Returns
    -------
    splitted_intervals : list
        List of subdivided momentum intervals to perform the statistical average.
        All attributes are copied, only the values for the `kmin` and `kmax`
        attribute are changed.
        Number of list elements is ``len(intervals) * number_subintervals``.
    """
    splitted_intervals = []
    for interval in copy.deepcopy(intervals):
        splitted_intervals += _split_interval(interval, number_subintervals)
    return splitted_intervals


def _attributes_similar(obj0, obj1, attributes, atol=1E-10, rtol=1E-10):
    """Return True if attributes are either equal or numerically close

    Parameters
    ----------
    obj0 : obj
        Some object.
    obj1 : obj
        Some object.
    attributes : sequence of str
        Attributes which are used to check similarity.
    atol : float, optional
        Absolute accuracy.
    rtol : float, optional
        Relative accuracy.

    Returns
    -------
    similar : bool
        Returns True if ``obj0`` and ``obj1`` are similar.
        Let us define `a = obj0.attribute` and `b = obj1.attribute` where
        attribute is an element of the ``attributes`` list.
        If `a` and `b` are numerical values (float or numpy arrays) we require
        that they are approximatly similar: `abs(a - b) < (atol + rtol * abs(b))`.
        For all other attributes `a == b` is required stricly.
        If either `a` of `b` is None, we return False.
    """
    assert _common.is_type(atol, 'real_number')
    assert atol >= 0
    assert _common.is_type(rtol, 'real_number')
    assert rtol >= 0
    for attrib in attributes:
        a = getattr(obj0, attrib, None)
        b = getattr(obj1, attrib, None)
        if isinstance(a, float) or isinstance(b, float):
            try:
                similar = abs(a - b) < (atol + rtol * abs(b))
            except Exception:
                similar = False
            if not similar:
                return False
        elif isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
            try:
                similar = np.allclose(a, b, atol, rtol)
            except Exception:
                similar = False
            if not similar:
                return False
        else:
            try:
                similar = a == b
            except Exception:
                similar = False
            if not similar:
                return False
    return True


@log_func
def combine_intervals(intervals, atol=1E-10, rtol=1E-10):
    """Group leads for similar intervals together.

    As an example
    ``int_1 = (lead=0, kmin=0, kmax=1..)``
    ``int_2 = (lead=1, kmin=0, kmax=1..)``
    are two intervals, which are similar except the lead index.
    If the sequence ``intervals = [int_1, int_2]`` is passed to this routine
    the lead indices are combined and the returnd result is
    ``[(lead=(0, 1), kmin=0, kmax=1...)]``.
    To test for similarity between the intervals, we compare the attributes,
    (exept the ones with two leading underscores).
    For attributes with numerical values `a` and `b`, we require
    `abs(a - b) < (atol + rtol * abs(b))` for similarity. Other attributes
    must match exactly: `a == b if a, b != lead`.

    Parameters
    ----------
    intervals : sequence of `tkwant.manybody.Interval`
        Quadrature intervals.
    atol : float, optional
        Absolute accuracy.
    rtol : float, optional
        Relative accuracy.

    Returns
    -------
    new_intervals : list of `tkwant.manybody.Interval`
        Combined intervals. Lead indices in the combined intervals are grouped
        in a tuple.
    """
    intervals_ = copy.deepcopy(intervals)
    new_intervals = []

    while True:
        try:
            i0 = intervals_.pop(0)
        except:
            break
        new_intervals.append(i0)

        attributes = [a for a in dir(i0) if not a.startswith('__')]
        try:
            attributes.remove('lead')
        except Exception:
            raise AttributeError('attribute "lead" missing in interval={}'.format(i0))
        leads = set()
        tmp = []
        for i1 in intervals_:
            if _attributes_similar(i0, i1, attributes, atol, rtol):
                if isinstance(i0.lead, int):
                    leads.add(i0.lead)
                else:
                    leads.update(list(i0.lead))
                if isinstance(i1.lead, int):
                    leads.add(i1.lead)
                else:
                    leads.update(list(i1.lead))
            else:
                tmp.append(i1)
        intervals_ = tmp
        if leads:
            new_intervals[-1].lead = tuple(leads)
    return new_intervals


@log_func
def calc_tasks(intervals, spectra, occupations, keys=None,
               task_type=onebody.Task, tol=1E-10):
    r"""Return all tasks (set of quantum numbers that uniquely identify
    a onebody state) that will form the manybody state.

    Parameters
    ----------
    intervals : `tkwant.manybody.Interval` or sequence thereof
        Momentum intervals with quadrature rules for each interval.
        Each element of ``intervals`` must have at least the following
        attributes:

            - `lead` : int or tuple of int, lead index
            - `band` : int, band index (*n*)
            - `kmin` : float, lower momentum bound
            - `kmax` : float, upper momentum bound, must be larger than `kmin`
            - `order` : int, quadrature order.
              See `tkwant.integration.calc_abscissas_and_weights`
            - `quadrature` : string, quadrature rule to use.
              See `tkwant.integration.calc_abscissas_and_weights`
            - `integration_variable` : string, variable of integration.
              Possible values: `"energy"` : integrate over energy,
              `"momentum"`: integrate over momentum

    spectra : `kwantspectrum.spectrum` or sequence thereof
        Energy dispersion :math:`E_n(k)` of one lead or list thereof in case of
        several leads.
    occupations : `tkwant.manybody.Occupation` or sequence thereof
        Each sequence element represents the occupation of a lead.
        If ``occupations`` consistst of only one element or if the
        sequence has only one element, the occupation is assumed to be
        identical in each lead. If ``occupations`` is a sequence with more than
        one element, such that the occupation for each lead is different,
        ``occupations`` must have the same length as ``spectra``.
        Each element of ``occupations`` must have at least the following
        attribute:

            - `distribution` : callable, thermal distribution function with
              calling signature `(energy)`

        If a lead is not occupied, the corresponding element of ``occupations``
        must be `None` or `False`.
    keys : iterable, optional
        Iterable to generate keys for the ``tasks`` dict.
        Default: Ascending integer sequence (0, 1, 2..), starting at zero.
    task_type : `~dataclasses.dataclass`, optional
        Data format to store a task in the returned ``tasks`` dict.
        Default: `tkwant.onebody.Task`
    tol : float, optional
        Numerical tolerance to remove tasks when their weights are almost zero.
        Condition to remove a task is \|weights| < tol.

    Returns
    -------
    tasks : dict of ``task_type``
        Dict of all tasks (set of quantum numbers that uniquely identify
        a onebody state) to set up the manybody wavefunction.
        Attributes of each ``tasks`` element that are modified by this routine:

            - `lead` : int, lead index
            - `mode` : int, scattering mode index
            - `energy` : float, energy of the onebody state
            - `momentum` : float, momentum of the onebody state; None if unknown
            - `weight` : float, weighting factor of the one-body state
              in the manybody sum (weight = math_weight * phys_weight)
            - `math_weight` : float, mathematical weighting factor
            - `phys_weight` : float, physical weighting factor

        Tasks are ordered as ``intervals`` and for each interval by increasing
        energy.

    Notes
    -----
    Momentum values in ``tasks`` are only present if integration is performed
    over momentum (``intervals.integration_variable`` == 'momentum').
    """

    if not isinstance(intervals, collections.abc.Iterable):
        intervals = [intervals]
    if not isinstance(spectra, collections.abc.Iterable):
        spectra = [spectra]
    if not isinstance(occupations, collections.abc.Iterable):
        occupations = [occupations]
    if keys is None:
        keys = itertools.count()

    uniform_occupation = False
    if len(occupations) == 1:
        logger.debug('occupation in all leads assumed identical for task calculation')
        uniform_occupation = True
    if not uniform_occupation and len(occupations) != len(spectra):
        raise ValueError('Occupation and spectra must have the same length.')

    assert _common.is_type(tol, 'real_number')
    assert tol > 0

    tasks = {}
    for interval in intervals:
        if not isinstance(interval.lead, collections.abc.Iterable):
            leads = [interval.lead]
        else:
            leads = interval.lead
        for lead in leads:
            assert _common.is_type(lead, 'integer')
            spectrum = spectra[lead]
            if uniform_occupation:
                occupation = occupations[0]
            else:
                occupation = occupations[lead]
            if occupation:
                logger.debug('calc quadrature weights for lead={}'.format(lead))
                modes_and_weights = _calc_modes_and_weights(interval,
                                                            occupation.distribution,
                                                            spectrum)
                for (mode, energy, momentum, weight, math_weight, phys_weight) in zip(*modes_and_weights):
                    weight_zero = _common.is_zero(weight, tol).all()
                    mode_not_open = (mode == -1)
                    if mode_not_open and not weight_zero:
                        msg = ('no open modes were found for energy={}, lead={}, '
                               'but the modes weight is {}, '
                               'which is larger than numerical tolerance={}.'
                               .format(energy, lead, weight, tol))
                        logger.warning(msg)
                    if not (weight_zero or mode_not_open):
                        tasks[next(keys)] = task_type(lead=lead, mode=mode,
                                                      energy=energy,
                                                      momentum=momentum,
                                                      weight=weight,
                                                      math_weight=math_weight,
                                                      phys_weight=phys_weight)

    logger.debug('number of tasks={}'.format(len(tasks)))
    for task in tasks.items():
        logger.debug('key={}, {}'.format(*task))
    return tasks


def absolute_error(result):
    r"""Absolute error for the solver result with `quadrature="kronrod"`

    Parameters
    ----------
    result : `~numpy.ndarray`
        Output from the manybody solver with Gauss-Kronrod quadrature

    Returns
    -------
    error : float
        error estimate
        :math:`\delta = |I_n - I_{2 n+1}|`, where :math:`I_n`
        is the integral estimate with order *n*.
    """
    low_order, high_order = result
    return np.abs(low_order - high_order)


def _calc_modes_and_weights(interval, distribution, spectrum):
    """Return mode indices, energies and weights on an integration interval.

    Parameters
    ----------
    interval : `tkwant.manybody.Interval`
        momentum interval and quadrature rule on that interval.
        Each ``interval`` must have at least the following attributes:

            - `band` : int, band index (*n*)
            - `kmin` : float, lower momentum bound
            - `kmax` : float, upper momentum bound, must be larger `kmin`
            - `order` : int, quadrature order
            - `quadrature` : string, quadrature rule to use.
            - `integration_variable` : string, energy vs. momentum integration

    distribution : callable
        distribution function of one lead. Calling signature: `(energy)`.
    spectrum : `kwantspectrum.spectrum`
        energy dispersion :math:`E_n(k)` of one lead.

    Returns
    -------
    modes : `~numpy.ndarray` of int, shape `(n, )`
        mode number (kwant convention)
    energies : `~numpy.ndarray` of float, shape `(n, )`
        mode energies
    momenta : `~numpy.ndarray` of float or `None`, shape `(n, )`
        momenta of the nodes. only present if `integration_variable`
         is 'momentum', otherwise all values are `None`.
    weights : `~numpy.ndarray` of float
        shape `(n, )` for simple quadratures or shape `(n, 2)` for
        Gauss-Kronrod quadrature
        weight of the corresponding onebody-state in the manybody average
        ``weights`` = ``math_weights`` * ``phys_weights``
    math_weights : `~numpy.ndarray` of float
        mathematical quadrature weights
        shape `(n, )` for simple quadratures or shape `(n, 2)` for
        Gauss-Kronrod quadrature
    phys_weights : `~numpy.ndarray` of float, shape `(n, )`
        physical weighting factor (fermi function, pi factors..)

    Notes
    -----
    The size `n` in above arrays depends on the quadrature:
    For Gauss-Legendre: n = interval.order.
    For Gauss-Kronrod: n = 2 * interval.order + 1.
    """
    if interval.integration_variable == "momentum":
        logger.debug('momentum integration: kmin={0.kmin}, kmax={0.kmax}, '
                     'band={0.band}, order={0.order}, quadrature={0.quadrature}'
                     .format(interval))
        momenta, math_weights = integration.calc_abscissas_and_weights(
            a=interval.kmin, b=interval.kmax, n=interval.order,
            quadrature=interval.quadrature)
        energies = spectrum(momenta, band=interval.band)
        velocities = spectrum(momenta, band=interval.band, derivative_order=1)
        modes = np.array([spectrum.momentum_to_scattering_mode(k, interval.band)
                          for k in momenta])
        jacobian = velocities
    elif interval.integration_variable == "energy":
        emin = spectrum(interval.kmin, band=interval.band)
        emax = spectrum(interval.kmax, band=interval.band)
        logger.debug('energy integration: emin={0}, emax={1}, kmin={2.kmin},'
                     'kmax={2.kmax}, band={2.band}, order={2.order}, '
                     'quadrature={2.quadrature}'.format(emin, emax, interval))
        energies, math_weights = integration.calc_abscissas_and_weights(
            a=emin, b=emax, n=interval.order, quadrature=interval.quadrature)
        modes = np.array([spectrum.energy_to_scattering_mode(energy, interval.band,
                                                             interval.kmin,
                                                             interval.kmax)
                          for energy in energies])
        jacobian = 1
        momenta = [None] * len(energies)
    else:
        raise NotImplementedError('integration_variable= {} not implemented'.
                                  format(interval.integration_variable))
    try:
        phys_weights = jacobian * distribution(energies) / (2 * np.pi)
    except TypeError:
        distribution_ = np.array([distribution(energy) for energy in energies])
        phys_weights = jacobian * distribution_ / (2 * np.pi)

    weights = math_weights * phys_weights
    assert _common.is_type_array(modes, 'integer').all()
    assert _common.is_type_array(energies, 'real_number').all()
    assert _common.is_type_array(weights, 'real_number').all()
    assert _common.is_type_array(math_weights, 'real_number').all()
    assert _common.is_type_array(phys_weights, 'real_number').all()
    return modes, energies, momenta, weights.T, math_weights.T, phys_weights


# manybody solvers

@log_func
def calc_initial_state(syst, tasks, boundaries, params=None,
                       scattering_state_type=onebody.ScatteringStates,
                       mpi_distribute=mpi.round_robin, comm=None):
    """Calculate the initial manybody scattering wave function using MPI.

    Parameters
    ----------
    syst : `kwant.builder.FiniteSystem`
        The low level system for which the wave functions are to be
        calculated.
    boundaries : sequence of `~tkwant.leads.BoundaryBase`
        The boundary conditions for each lead attached to ``syst``.
    tasks : sequence of `tkwant.onebody.Task`
        Each element in the sequence represents a one-body state
        that composes the manybody state.
        An element of ``tasks`` must have at least the following three attributes:

            - `lead` : int, lead index
            - `mode` : int, scattering mode index
            - `energy` : float, energy
    params : dict, optional
        Extra arguments to pass to the Hamiltonian of ``syst``,
        excluding time.
    scattering_state_type : `tkwant.onebody.ScatteringStates`, optional
        Class to calculate time-dependent onebody wavefunctions starting in an
        equilibrium scattering state.
    mpi_distribute : callable, optional
        Function to distribute the tasks dict keys over all MPI ranks.
        By default, keys must be integer and are distributed round-robin like.
    comm : `mpi4py.MPI.Intracomm`, optional
        The MPI communicator over which to parallelize the computation.
        By default, use the tkwant global MPI communicator.

    Returns
    -------
    psi_init : dict of `tkwant.onebody.WaveFunction`
        Ensemble of all one-body scattering states that form the initial
        manybody state. Each one-body state stored in the ``psi_init`` dictionary
        corresponds to an element in the ``tasks`` list.
        The list index of ``tasks`` serves as dict key.
    """
    def scattering_state(energy, lead):
        """Calculate a one-body scattering state that can be evolved in time"""
        logger.debug('calc scattering state: energy={}, lead={}'.format(energy, lead))
        try:
            return scattering_state_type(syst, energy, lead, params=params,
                                         boundaries=boundaries)
        except Exception:
            raise RuntimeError('scattering state calculation failed for '
                               'energy={}, lead={}'.format(energy, lead))

    if not isinstance(syst, kwant.system.System):
        raise TypeError('"syst" must be a finalized kwant system')
    comm = mpi.get_communicator(comm)
    tasks_per_rank = mpi.distribute_dict(tasks, mpi_distribute, comm)
    return {key: scattering_state(task.energy, task.lead)[task.mode]
            for key, task in tasks_per_rank.items()}


class WaveFunction:
    """Evolve a many-particle wavefunction in time."""

    def __init__(self, psi_init, tasks, comm=None):
        """
        Initialize the manybody state.

        Parameters
        ----------
        psi_init : dict of `tkwant.onebody.WaveFunction`
            Dictionary with all initial one-body states.
            For load balancing the dictionary should be distributed over
            all MPI ranks.
        tasks : dict of `tkwant.onebody.Task`
            Dictionary containing the weighting factor for each one-body state.
            Each item must have at least the following attribute:

                - `weight` : `~numpy.ndarray`, weighting factor

            ``tasks`` must include all one-body states stored in `psi_init`
            and must be the same on all MPI ranks.
        comm : `~mpi4py.MPI.Intracomm`, optional
            The MPI communicator over which to parallelize the computation.
            By default, use the tkwant global MPI communicator.
        """
        comm = mpi.get_communicator(comm)
        self.psi = mpi.DistributedDict(psi_init, comm)
        self.tasks = tasks
        self.comm = comm
        self.time = 0

    def evolve(self, time):
        """
        Evolve all wavefunctions up to ``time``.

        Parameters
        ----------
        time : int or float
            time argument up to which the solver should be evolved
        """
        for onebody_psi in self.psi.local_data().values():
            onebody_psi.evolve(time)
        self.time = time

    def evaluate(self, observable, root=0):
        """Evaluate the expectation value of an operator at the current time.

        Parameters
        ----------
        observable : callable or `kwant.operator`
            An operator to evaluate the expectation value.
            Must have the calling signature of `kwant.operator`.
        root : int or None, optional
            MPI return rank on which to return the result. If ``root`` is an
            integer, it must be in the range of valid MPI ranks
            ``0 <= root < self.comm.size``.
            In that case, the calculated result is returned
            only on that specific MPI rank where ``rank == root``, whereas the
            result is `None` on all other MPI ranks with ``rank != root``.
            Alternatively, if ``root`` is `None`,
            the calculated result is returned on all MPI ranks.
            By default, the result is returned on MPI rank zero only.

        Returns
        -------
        result : `~numpy.ndarray`
            The expectation value of ``observable``, integrated over all
            occupied bands. The result might not be returned on all MPI ranks;
            note the explanation above for input parameter ``root``.

        Notes
        -----
        Returning the result on all MPI ranks (by setting ``root=None``),
        might be slower, as an additional broadcast step is needed.
        """
        return self._calc_expectation_value(observable, root=root)

    def get_onebody_state(self, key):
        """ Get the onebody wavefunction corresponding to its key.

        Parameters
        ----------
        key : dict key
            Idendentifier key of the state.

        Returns
        -------
        state : `tkwant.onebody.WaveFunction`
            onebody wavefunction
        """
        return self.psi.data(key)

    def add_onebody_state(self, state, task, key=None, rank=None):
        """Add a onebody wavefunction to the manybody state.

        Parameters
        ----------
        state : `tkwant.onebody.WaveFunction`
            onebody wavefunction
        task : `tkwant.onebody.Task`
            Task info of the state. ``task`` must contain at least
            the weight factors of the onebody states in the manybody average
            as attribute:

            - `weight` : `~numpy.ndarray`, weighting factor
        key : dict key, optional
            Idendentifier of the state. A free key is attributed if not present.
        rank : int, optional
            MPI rank where the state should be added.

        Returns
        -------
        key : dict key
            Idendentifier of the added onebody state.

        Notes
        -----
        The state must be present on all MPI ranks.
        """
        if key is None:
            key = self.get_free_key()
        self.psi.add(key, state, rank)
        self.tasks[key] = task
        return key

    def add_distributed_onebody_states(self, states, tasks):
        """Add several onebody wavefunctions to the manybody state.

        Parameters
        ----------
        state : dict of `tkwant.onebody.WaveFunction`
            Dictionary of onebody wavefunctions to be added
        task : dict of `tkwant.onebody.Task`
            Task info of the states. Each ``tasks`` item must contain at
            least the weight factors of the onebody states in the manybody
            average as attribute:

                - `weight` : `~numpy.ndarray`, weighting factor

        Notes
        -----
        The states present in the states dictionary can be distributed
        over all MPI ranks. Each single onebody state must be unique and
        not dublicated on any other MPI rank.
        """
        for key, psi in states.items():
            self.psi.add(key, psi, rank=self.comm.rank, check=False)
        assert self.psi.keys_are_unique()
        self.tasks.update(tasks)

    def delete_onebody_state(self, key):
        """Delete a onebody wavefunction corresponding to its key.

        Parameters
        ----------
        key : dict key
            Idendentifier of the onebody state that should be deleted.
        """
        self.psi.delete(key)
        del self.tasks[key]

    def get_keys(self):
        """Get the keys of all onebody wavefunctions forming the manybody state.

        Returns
        -------
        keys : list
            List of all state identifier keys present in the solver.
        """
        return list(self.tasks.keys())

    def get_free_key(self):
        """Get a new free key.

        Returns
        -------
        key : int
            New unused key. All numbers larger then the returned
            key are also valid empty keys.
        """
        try:
            next_key = max((i for i in self.get_keys() if _common.is_type(i, 'integer'))) + 1
        except ValueError:
            next_key = 0
        return next_key

    def weight_shape(self):
        """Get the shape of the weighting factor.

        Returns
        -------
        shape : tuple
            Shape of the weight factor array.
        """
        key = self.get_keys()[0]
        weight = self.tasks[key].weight
        return weight.shape

    def _check_consistency(self):
        """Check if keys for the wave functions consistent in itself and with the tasks.

        Returns
        -------
        consistent : bool
            Returns `True` if all keys are unique and if the keys in task list
            are also present in the state dictionary.
        """
        keys_unique = self.psi.keys_are_unique()
        keys_from_psi = list(self.psi.keys())
        keys_from_tasks = list(self.tasks.keys())
        return keys_unique and set(keys_from_psi) == set(keys_from_tasks)

    def _calc_expectation_value(self, observable, keys=None, root=0, return_integrand=False):
        """Calculate the expectation value of an observable at a given time.

        Parameters
        ----------
        observable : callable or `kwant.operator`
            An operator to evaluate the expectation value.
            Must have the calling signature of `kwant.operator`.
        keys : list of dict keys, optional
            If present, the manybody sum is calculated only over these states.
        root : int or None, optional
            MPI return rank on which to return ``result``. If ``root`` is an
            integer, it must be in the range of valid MPI ranks
             ``0 <= root < self.comm.size``.
            In that case, the calculated ``result`` is returned
            only on that specific MPI rank where ``rank == root``, whereas the
            ``result`` is `None` on all other MPI ranks with ``rank != root``.
            Alternatively, if ``root`` is `None`,
            the calculated result is returned on all MPI ranks.
            By default, ``result`` is returned on MPI rank zero only.
        return_integrand : bool, optional
            If `True` return ``integrand`` in addition.

        Returns
        -------
        result : `~numpy.ndarray`
            The expectation value of ``observable``.
        integrand : dict, optional
            The integrand of ``result``. Similar keys as the states.
            The integrand is distributed over
            all MPI ranks, ordering similar to the corresponding states.
            Only returned if ``return_integrand`` is `True`.

        Notes
        -----
        Returning the result on all MPI ranks (by setting ``root=None``),
        might be slower, as an additional broadcast step is needed.
        """

        if keys is None:
            keys = self.psi.local_keys()
        else:  # intersection between given keys and keys on MPI rank
            keys = list(set(keys) & set(self.psi.local_keys()))

        integral = 0  # local integral part on mpi process

        # calculate weighted sum (partly on every rank)
        if return_integrand:
            integrand = {}
            for key in keys:
                expect = self.psi.local_data()[key].evaluate(observable)
                weight = self.tasks[key].weight
                phys_weight = self.tasks[key].phys_weight
                integral += np.outer(weight, expect)
                integrand[key] = phys_weight * expect
        else:
            for key in keys:
                expect = self.psi.local_data()[key].evaluate(observable)
                weight = self.tasks[key].weight
                integral += np.outer(weight, expect)

        if root is None:
            result = self.comm.allreduce(integral)
        else:
            result = self.comm.reduce(integral, root=root)
        result = np.squeeze(result)

        if return_integrand:
            return result, integrand
        return result


def _find_min_max_range(x):
    """Obtain min/max from a sequence of ranges.

    Each range is a tuple (x0, x1), with x0 <= x1, a value of
    None for x0 is interpreted as -inf, for x1 as +inf.
    """
    lower, upper = zip(*x)
    if None in lower:
        lower = None
    else:
        lower = min(lower)
    if None in upper:
        upper = None
    else:
        upper = max(upper)
    return lower, upper


@log_func
def calc_energy_cutoffs(occupations):
    """Extract upper and lower energy cutoffs from the lead occupations.

    We give an example how this routine works:
    Let be `energy_range` = [(None, 1), (2, 3)] for one lead, where each
    tuple has a meaning of an energy interval. For this lead, the largest
    energy interval, including all these intervals is (None, 3). Note that None
    as the first tuple elements is interpreted as - infinity. The same is done
    now for all elements of the ``occupations`` sequence, which represent the leads.
    The ``(emin, emax)`` values returned by this routine is the largest interval,
    that contain all energy intervals of the leads. If a lead is not present,
    the corresponding element of the ``occupations`` sequence must be None, such
    that it does contribute. Pay attention that None has double meaning:
    As an energy interval (None, 0) or (0, None) it is interpreted as
    - infinity, respectively + infinity. For the ``occupations`` sequence, None
    means absence, such that emin/emax are not changed by the corresponding lead.
    If all lead elements are None, ``(None, None)`` is returned.

    Parameters
    ----------
    occupation : `tkwant.manybody.Occupation` or sequence thereof
        Lead occupation, see `lead_occupation` for details.
        If a lead is not occupied, the corresponding element must be set to None.
        Otherwise, each element of the ``occupations`` sequence must have
        at least the following attribute:

            - `energy_range` : energy integration range (see `lead_occupation`)

    Returns
    -------
    emin : float or None
        Lower energy cutoff, None means a cutoff of - infinity.
    emin : float or None
        Upper energy cutoff, None means a cutoff of + infinity.
    """

    lower_energy_cutoff_lead = []
    upper_energy_cutoff_lead = []

    if not isinstance(occupations, collections.abc.Iterable):
        occupations = [occupations]
    for occup in occupations:  # loop over all occupied leads
        if occup is not None:
            lower, upper = _find_min_max_range(occup.energy_range)
            lower_energy_cutoff_lead.append(lower)
            upper_energy_cutoff_lead.append(upper)

    # only occupied leads contribute to the cutoff
    if None in lower_energy_cutoff_lead or not lower_energy_cutoff_lead:
        lower = None
    else:
        lower = min(lower_energy_cutoff_lead)
    if None in upper_energy_cutoff_lead or not upper_energy_cutoff_lead:
        upper = None
    else:
        upper = max(upper_energy_cutoff_lead)
    return lower, upper


class State:
    """Solve the time-dependent many-particle Schrödinger equation."""

    def __init__(self, syst, tmax=None, occupations=None, params=None,
                 spectra=None, boundaries=None, intervals=Interval,
                 refine=True, combine=False, error_op=None,
                 scattering_state_type=onebody.ScatteringStates,
                 manybody_wavefunction_type=WaveFunction,
                 mpi_distribute=mpi.round_robin, comm=None):
        r"""
        Parameters
        ----------
        syst : `kwant.builder.FiniteSystem`
            The low level system for which the wave functions are to be
            calculated.
        tmax : float, optional
            The maximum time up to which to simulate. Sets the boundary
            conditions such that they are accurate up to ``tmax``.
            Must be set if ``boundaries`` are not provided.
            Mutually exclusive with `boundaries`.
        occupations : `tkwant.manybody.Occupation` or sequence thereof, optional
            Lead occupation. By default (or if ``occupations`` is set to `False`),
            all leads are taken into account and are
            considered as equally occupied with:
            chemical potential :math:`\mu = 0`, temperature :math:`T = 0`
            and the non-interacting Fermi-Dirac distribution as
            distribution function :math:`f(E)`.
            To change the default values (:math:`\mu, T, f(E)`),
            a `tkwant.manybody.Occupation` instance
            is precalculated with `tkwant.manybody.lead_occupation`
            and passed as ``occupations`` argument. If ``occupations`` is
            only one element, respectively a sequence with only one element,
            (:math:`\mu, T, f(E)`) will be identical in each lead.
            In the most general case, if (:math:`\mu, T, f(E)`)
            is different for each lead, ``occupations`` must be
            a sequence of `tkwant.manybody.Occupation` instances
            with an ordering similar to ``syst.leads``.
            In that case, ``occupations`` must have the same
            length as ``syst.leads``, respectively ``spectra``.
            A lead is not considered, if the corresponding ``occupations``
            element is set to `False`. Otherwise, for a lead to be
            considered, an element of the ``occupations`` sequence must have
            at least the following attributes:

            - `energy_range` : energy integration range
            - `bands` : int or list of int, bands (*n*) to be considered,
              all bands considered if `None`
            - `distribution` : callable, distribution function.
              Calling signature: `(energy)`.

        params : dict, optional
            Extra arguments to pass to the Hamiltonian of ``syst``,
            excluding time.
        spectra : sequence of `~kwantspectrum.spectrum`, optional
            Energy dispersion :math:`E_n(k)` for the leads. Must have
            the same length as ``syst.leads``. If needed but not present,
            it will be calculated on the fly from `syst.leads`.
        boundaries : sequence of `~tkwant.leads.BoundaryBase`, optional
            The boundary conditions for each lead attached to ``syst``.
            Must have the same length as ``syst.leads``.
            Mutually exclusive with ``tmax``.
        intervals : `tkwant.manybody.Interval` sequence or class, optional
            Momentum intervals and quadrature rules on these intervals.
            If ``intervals`` is a sequence, it represents
            the momentum intervals.
            In that case, initial integration intervals are not calculated
            from ``occupations`` but ``intervals`` is used instead.
            Each element of the ``intervals`` sequence must have at least
            the following attributes:

                - `lead` : int, lead index
                - `band` : int, band index (*n*)
                - `kmin` : float, lower momentum bound
                - `kmax` : float, upper momentum bound, must be larger `kmin`
                - `integration_variable` : string, energy vs. momentum integration
                - `order` : int, quadrature order
                - `quadrature` : string, quadrature rule to use.
                  See `tkwant.integration.calc_abscissas_and_weights`

            If ``intervals`` is a (data) class, it is passed to the
            `tkwant.manybody.calc_intervals` routine as ``Interval`` argument.
            By default, intervals are calculated from
            `tkwant.manybody.calc_intervals` and `tkwant.manybody.Interval`.
        refine : bool, optional
            If `True`, intervals are refined at the initial time.
        combine : bool, optional
            If `True`, intervals are grouped by lead indices.
        error_op : callable or `kwant.operator`, optional
            Observable used for the quadrature error estimate.
            Must have the calling signature of `kwant.operator`.
            Default: Error estimate with density expectation value.
        scattering_state_type : `tkwant.onebody.ScatteringStates`, optional
            Class to calculate time-dependent onebody wavefunctions starting in
            an equilibrium scattering state. Name of the time argument and
            initial time are taken from this class. If this is not possible,
            default values are used as a fallback.
        manybody_wavefunction_type : `tkwant.manybody.WaveFunction`, optional
            Class to evolve a many-particle wavefunction in time.
        mpi_distribute : callable, optional
                Function to distribute the tasks dict keys over all
                MPI ranks. By default, keys must be integer and are
                distributed round-robin like.
        comm : `mpi4py.MPI.Intracomm`, optional
            The MPI communicator over which to parallelize the computation.


        Notes
        -----
        The name of the time argument (`time_name`) and the initial time
        of the evolution (`time_start`) are taken from the default
        values of the `scattering_state_type.__init__` method. Changing the
        default values by partial prebind (e.g. via functools) is possible.
        """

        logger.info('initialize manybody.State')

        if not isinstance(syst, kwant.system.System):
            raise TypeError('"syst" must be a finalized kwant system')
        if tmax is None and boundaries is None:
            raise ValueError("'boundaries' or 'tmax' must be provided ")
        if tmax is not None and boundaries is not None:
            raise ValueError("'boundaries' and 'tmax' are mutually exclusive.")

        # get initial time and time argument name from the onebody wavefunction
        try:
            default_arg = _common.get_default_function_argument
            onebody_wavefunction_type = default_arg(scattering_state_type,
                                                    'wavefunction_type')
            time_name = default_arg(onebody_wavefunction_type, 'time_name')
            time_start = default_arg(onebody_wavefunction_type, 'time_start')
        except Exception:
            time_name = _common.time_name
            time_start = _common.time_start
            onebody_wavefunction_type = None
            logger.warning('retrieving initial time and time argument name from',
                           'the onebody wavefunction failed, use default values: ',
                           '"time_name"={}, "time_start"={}'.format(time_name,
                                                                    time_start))

        # add initial time to the params dict
        tparams = add_time_to_params(params, time_name=time_name,
                                     time=time_start, check_numeric_type=True)

        if spectra is None:
            spectra = kwantspectrum.spectra(syst.leads, params=tparams)
        if occupations is None:
            occupations = [lead_occupation()]
        if not isinstance(occupations, collections.abc.Iterable):
            logger.debug('occupation in all leads is {}'.format(occupations))
            occupations = [occupations]
        else:
            for i, occ in enumerate(occupations):
                logger.debug('occupation in lead={} is {}'.format(i, occ))
        if intervals is None:
            intervals = calc_intervals(spectra, occupations)
            if combine:
                intervals = combine_intervals(intervals)
        else:
            if not (isinstance(intervals, collections.abc.Iterable) or
                    isinstance(intervals, Interval)):
                intervals = calc_intervals(spectra, occupations, interval_type=intervals)
            if combine:
                intervals = combine_intervals(intervals)
        try:
            len_int = len(intervals)
        except TypeError:
            len_int = 0
        if len_int == 0:
            logger.warning('no occupied states found, the chemical potential '
                           'is probably wrong.')
        else:
            logger.info('initial number of intervals={}'.format(len_int))
        for interval in intervals:
            logger.debug(interval)
        if boundaries is None:
            emin, emax = calc_energy_cutoffs(occupations)
            boundaries = leads.automatic_boundary(spectra, tmax,
                                                  emin=emin, emax=emax)

        self.time = time_start
        self.syst = syst
        self.spectra = spectra
        self.boundaries = boundaries
        self.occupations = occupations
        self.mpi_distribute = mpi_distribute
        self.onebody_wavefunction_type = onebody_wavefunction_type
        self.scattering_state_type = scattering_state_type

        # no public params attribute exists for the manybody state.
        # each individual one-body state holds its own parameters
        # the private params should be only used to create new inital
        # onebody states.
        self._params = params

        self._tasks_from_interval = {}
        tasks = self._calc_tasks(intervals)

        self.comm = mpi.get_communicator(comm)

        psi_init = self._calc_initial_state(tasks, self.comm)

        self.manybody_wavefunction = manybody_wavefunction_type(psi_init,
                                                                tasks, self.comm)

        # by default, return the result of the higher-order rule, which in
        # our convention has to be the last element of the weight array
        self.return_element = -1

        if error_op is None:
            logger.info('set default error estimate based on density')
            error_op = kwant.operator.Density(syst)
        else:
            logger.info('set error estimate based on user given operator')
        self.error_op = error_op

        if refine:
            self.refine_intervals()

        logger.info('manybody.State initialization done')

    def _calc_tasks(self, interval, offset=0, tol=1E-10):
        """Evaluate all tasks corresponding to an interval and store them.

        Parameters
        ----------
        interval : `tkwant.manybody.Interval`
            Interval
        offset : int, optional
            First key value of the dict.
        tol : float, optional
            Numerical tolerance to remove tasks.

        Returns
        -------
        tasks : dict
            Dict with all tasks (states) for the interval.
            Dict keys are incremented by one starting at `offset`.
        """
        if not isinstance(interval, list):
            interval = [interval]
        tasks = {}
        for _interval in interval:
            _tasks = calc_tasks(_interval, self.spectra, self.occupations,
                                keys=itertools.count(offset), tol=tol)
            if _tasks:
                self._tasks_from_interval.update({_interval: _tasks})
                tasks.update(_tasks)
                offset += len(_tasks)
        if len(tasks) == 0:
            logger.warning('tasks dict has length zero')
        return tasks

    def _calc_initial_state(self, tasks, comm):
        """Calculate the initial manybody state for all tasks.

        Parameters
        ----------
        tasks : dict
            Dict with all tasks. Each item represents
            a one-body state that composes the manybody state.
        comm : `mpi4py.MPI.Intracomm`

        Returns
        -------
        psi_init : dict
            Ensemble of all one-body scattering states that form the
            initial manybody state.
        """
        return calc_initial_state(self.syst, tasks, self.boundaries,
                                  self._params, self.scattering_state_type,
                                  mpi_distribute=self.mpi_distribute, comm=comm)

    def _get_keys_from_interval(self, interval):
        """Return a list of all keys corresponding to an interval.

        Parameters
        ----------
        interval : `tkwant.manybody.Interval`
            Interval

        Returns
        -------
        keys : list
            List of all keys representing the states of the interval
        """
        tasks = self._tasks_from_interval[interval]
        return list(tasks.keys())

    def _add_interval(self, interval, tol=1E-10):
        """Add all one-body states and tasks corresponding to an interval.

        Parameters
        ----------
        interval : `tkwant.manybody.Interval`
            Integration interval that should be added to the solver
        tol : float, optional
            Numerical tolerance to remove tasks.
        """
        next_free_key = self.manybody_wavefunction.get_free_key()
        tasks = self._calc_tasks(interval, offset=next_free_key, tol=tol)
        psi_init = self._calc_initial_state(tasks, comm=self.comm)
        self.manybody_wavefunction.add_distributed_onebody_states(psi_init, tasks)

    def _remove_interval(self, interval):
        """Remove all one-body states and tasks corresponding to an interval.

        Parameters
        ----------
        interval : `tkwant.manybody.Interval`
            Interval that should be removed from the solver
        """
        for key in self._get_keys_from_interval(interval):
            self.manybody_wavefunction.delete_onebody_state(key)
        del self._tasks_from_interval[interval]

    def _evaluate_interval(self, interval, operator, root=None, return_integrand=False):
        """Evaluate the statistical average over the given interval.

        Parameters
        ----------
        interval : `tkwant.manybody.Interval`
            Interval over which the manybody sum should be calculated.
        operator : callable or `kwant.operator`
            Observable to be calculated
        root : int or None, optional
            root receive the result, other rank receive None.
            If root is None all ranks receive the result.
        return_integrand : bool, optional
            If true, return also the integrand of the integral.

        Returns
        -------
        result : `~numpy.ndarray`
            The expectation value of ``operator``, integrated over
            the interval.
        integrand : dict, optional
            The integrand to the integral. Only returned if ``return_integrand``
            it true.
        """
        keys = self._get_keys_from_interval(interval)
        return self.manybody_wavefunction._calc_expectation_value(operator,
                                                                  keys=keys, root=root,
                                                                  return_integrand=return_integrand)

    def _calc_integrand(self, interval, operator, root=None):
        """Return the integrand and the corresponding abscissa values.

        This routine is only for debugging purpose.

        Parameters
        ----------
        interval : `tkwant.manybody.Interval`
            Interval over which the manybody sum should be calculated.
            Must be present in the solver.
        operator : callable or `kwant.operator`
            Observable to be calculated
        root : int or None, optional
            root receive the result, other rank receive None.
            If root is None all ranks receive the result.

        Returns
        -------
        abscissa : `~numpy.ndarray`
            The integration points (abcissa) of the quadrature.
            Corresponds to energy values if integration is performed over
            energy (``interval.integration_variable`` == 'energy')
            or momentum (if ``interval.integration_variable`` == 'momentum').
        integrand : `~numpy.ndarray`
            The expectation value of ``operator`` on all abcissa points.
        """
        self.evolve(time=self.time)  # make sure interval is at current time
        keys = self._get_keys_from_interval(interval)
        tasks = self._tasks_from_interval[interval]
        abscissa = np.array([getattr(tasks[key], interval.integration_variable)
                             for key in keys])
        _, integrand = self._evaluate_interval(interval, operator, root=root,
                                               return_integrand=True)
        integrand = np.array([integrand[key] for key in keys])
        return abscissa, integrand

    def get_intervals(self):
        """Return a list of all intervals stored in the solver.

        Returns
        -------
        intervals : list
            List of all momentum intervals stored in the solver.
        """
        # without copy we may modify the state of the saved intervals
        intervals = copy.deepcopy(list(self._tasks_from_interval.keys()))
        return sorted(intervals, key=lambda x: (x.lead, x.band, x.kmin))

    def refine_intervals(self, atol=1E-5, rtol=1E-5, limit=2000,
                         error_op=None, intervals=None):
        r"""Refine intervals until the quadrature error is below tolerance.

        Parameters
        ----------
        atol : float, optional
            Absolute accuracy requested.
        rtol : float, optional
            Relative accuracy requested.
        limit : integer, optional
            Maximum number of intervals stored in the solver. A warning is
            raised and the refinement stops if limit is reached.
        error_op : callable or `kwant.operator`, optional
            Observable used for the quadrature error estimate.
            Must have the calling signature of `kwant.operator`.
            Default: ``error_op`` from initialization.
        intervals : sequence of `tkwant.manybody.Interval`, optional
            Apply the refinement process only to the (Gauss-Kronrod) intervals
            given in the sequence. Note that in this case, all intervals
            must be present in the solver already. By default,
            the refinement is done on all Gauss-Kronrod intervals
            stored in the solver.

        Returns
        -------
        abserr : float
            Estimate of the modulus of the absolute error,
            which should equal or exceed abs(i-result), where i is the exact
            integral value. If ``error_op`` has an array-like output,
            we report the maximal value of the error.
            (sum ``errors`` over all intervals and take the maximum element).
        intervals : list of `tkwant.manybody.Interval`
            All subintervals *J* taken into accound. Intervals are ordered
            according to `errors`.
        errors : `~numpy.ndarray` of floats
            Error estimates *E(J)* on the intervals in descending order.
            If ``error_op`` has an array-like output, the error is
            returned on all array points.
            The shape of ``errors`` is like ``error_op`` (its expectation value)
            with an additional first dimension for the interval index.

        Notes
        -----
        This routine implements a globally adaptive strategy based
        on quadpacks QAG algorithm [1]_.
        It attemps to reduce the absolute error *abserr*
        by subdividing (bisecting) the interval with the largest error estimate.

        *result* corresponds to the quadrature estimate of the integral
        :math:`\int_a^b f(x) dx`:

        :math:`result = \sum_{J \in \mathcal{P}[a, b]} Q_f(J)`.

        Here *J* is a subinterval of the *[a, b]* interval and :math:`Q_f(J)`
        is a quadrature rule applied on function *f(x)* on interval *J*.
        In this algorithm, a *(2*n + 1)* Kronrod estimate is used to calculate
        *Q*.

        *abserr* corresponds to the sum of errors:

        :math:`abserr = \sum_{J \in \mathcal{P}[a, b]} E_f(J)`.

        We use the quadpack error estimate, described in method
        `_error_estimate_quadpack`, for :math:`E_f(J)`. If the refinement
        procedure is successful, the following inequality holds:

        :math:`abserr \leq \max \left\{ atol, rtol \cdot result \right\}`

        In the physical sense, the integral we estimate is the manybody integral

        :math:`\langle \hat{A}_{ij}(t) \rangle = \sum_{\alpha} \int_{- \pi}^{\pi}
        \frac{dk}{2 \pi} v_{\alpha}(k) \theta(v_{\alpha}(k)) f_\alpha(k)
        [\psi_{\alpha, k}(t)]_i \hat{A} [\psi^\dagger_{\alpha, k}(t)]_j`

        where :math:`\hat{A}` corresponds to the ``error_op``
        and the error is estimated for the expectation value
        :math:`\langle \hat{A}_{ij}(t) \rangle`.
        Note that above inequality condition must be fulfilled on each site *i*
        and *j* individually. This is the case if ``error_op`` generates an
        array-like output. However, the inequality condition must be fulfilled
        only at the current time *t* of the solver.

        Moreover, note that only intervals stored in the solver are refined.
        One-body states, that are not part of an interval,
        are not altered by this method.

        .. [1] Piessens, R., de Doncker-Kapenga, E., Ueberhuber,
              C. W., and Kahaner, D. K.,
              QUADPACK A Subroutine Package for Automatic Integration,
              Springer-Verlag, Berlin, (1983).
        """

        assert _common.is_type(atol, 'real_number')
        if atol < 0:
            raise ValueError('atol={} is negative.'.format(atol))
        assert _common.is_type(rtol, 'real_number')
        if rtol < 0:
            raise ValueError('rtol={} is negative.'.format(rtol))
        assert _common.is_type(limit, 'integer')
        if limit <= 1:
            raise ValueError('limit={} must be > 1.'.format(limit))
        tol = min(1E-14, 0.5 * (atol + rtol))

        if error_op is None:
            error_op = self.error_op

        def observable_with_error(_intervals):
            observable = []
            errors = []
            for interval in _intervals:
                error, kronrod = self._error_estimate_quadpack(interval,
                                                               error_op,
                                                               return_estimate=True)
                observable.append(kronrod)
                errors.append(error)
            return np.array(observable), np.array(errors)

        if intervals is None:
            intervals = self.get_intervals()
        else:
            intervals = copy.deepcopy(intervals)
            if not isinstance(intervals, collections.abc.Iterable):
                intervals = [intervals]

        # refine only intervals with Gauss-Kronrod quadrature
        intervals[:] = [interval for interval in intervals
                        if interval.quadrature == 'kronrod']

        results, errors = observable_with_error(intervals)

        result = np.sum(results, axis=0)  # sum of the integrals over the subintervals
        errsum = np.sum(errors, axis=0)  # sum of the errors over the subintervals

        i = 0
        while True:  # loop until converged

            errbnd = np.maximum(atol, rtol * np.abs(result))  # requested accuracy

            # order all intervals by error, decreasing order
            try:
                max_error_per_interval = np.max(errors - errbnd[np.newaxis, :], axis=1)
            except:
                max_error_per_interval = errors - errbnd

            error_idx = np.argsort(max_error_per_interval)[::-1]

            intervals = [intervals[i] for i in error_idx]
            results = results[error_idx]
            errors = errors[error_idx]
            max_error_per_interval = max_error_per_interval[error_idx]

            errmax = errors[0]
            resultmax = results[0]

            logger.info('refinement step={}, max errsum={}, min errbnd={}, '
                        'nb intervals={}'.
                        format(i, np.max(errsum), np.min(errbnd), len(intervals)))
            for inte, err in zip(intervals, errors):
                logger.debug("{}, max error={}".format(inte, np.max(err)))

            if (errsum <= errbnd).all():  # converged
                logger.info('refinement converged')
                break

            if len(intervals) >= limit:
                logger.warning('maximum number of intervals reached')
                break

            # bisect the interval with the largest error
            interval_largest_error = intervals.pop(0)
            new_intervals = _split_interval(interval_largest_error, 2)
            intervals += new_intervals

            # update the intervals stored in the solver, evolve to current time
            self._remove_interval(interval_largest_error)
            for interval in new_intervals:
                self._add_interval(interval, tol=tol)
            self.evolve(time=self.time)

            # recalculate the error and observable estimate
            new_results, new_errors = observable_with_error(new_intervals)

            results = np.append(results, new_results, axis=0)
            errors = np.append(errors, new_errors, axis=0)

            results = np.delete(results, 0, axis=0)
            errors = np.delete(errors, 0, axis=0)

            result = result + new_results[0] + new_results[1] - resultmax
            errsum = errsum + new_errors[0] + new_errors[1] - errmax
            i += 1

        return np.max(errsum), intervals, errors

    def refine_intervals_local(self, atol=1E-5, rtol=1E-5, limit=200,
                               error_op=None):
        r"""Refine intervals until the quadrature error is below tolerance.

        Parameters
        ----------
        atol : float, optional
            Absolute tolarance value.
        rtol : float, optional
            Relative tolarance value.
        limit : integer, optional
            Maximum number of intervals stored in the solver. A warning is
            raised and the refinement stops if limit is reached.
        error_op : callable or `kwant.operator`, optional
            Observable used for the quadrature error estimate.
            Must have the calling signature of `kwant.operator`.
            Default: ``error_op`` from initialization.


        Notes
        -----
        This routine implements a local adaptive strategy.
        For each interval stored in the solver, this routine subdivides
        the interval until each interval fulfills
        :math:`|I_n - I_{2 n+1}| <= atol + rtol |I_{ges}|`, where
        :math:`I_n` is the integral estimate over an interval with order *n*.
        Moreover, :math:`I_{ges} = \sum{I_{2 n +1}}` and the sum runs over
        all stored intervals. Note that if `error_op` has a site dependent
        array output, the criterion must be fulfilled at each site
        individually. One-body states that are not part of an interval
        are not altered by this method.
        """
        assert _common.is_type(atol, 'real_number')
        if atol < 0:
            raise ValueError('atol={} is negative.'.format(atol))
        assert _common.is_type(rtol, 'real_number')
        if rtol < 0:
            raise ValueError('rtol={} is negative.'.format(rtol))

        if error_op is None:
            error_op = self.error_op

        # loop until converged
        i = 0
        while True:

            i += 1
            tol = atol + rtol * np.abs(self.evaluate(error_op, root=None))

            intervals_to_refine = []
            intervals = self.get_intervals()
            for interval in intervals:

                error = self._error_estimate_gauss_kronrod(interval, error_op)

                if np.where(error > tol, True, False).any():
                    logger.info("refine step={}, max error={}, interval={}".
                                format(i, np.max(error), interval))
                    intervals_to_refine.append(interval)

            if not intervals_to_refine:  # converged
                break
            if len(intervals) >= limit:
                logger.warning('maximum number of intervals reached')
                break

            logger.info('refinement step={}, intervals to refine={}, total={}'.
                        format(i, len(intervals_to_refine), len(intervals)))

            new_intervals = []
            for interval in intervals_to_refine:
                self._remove_interval(interval)
                assert self.manybody_wavefunction._check_consistency()
                for new_interval in split_intervals([interval], 2):
                    new_intervals.append(new_interval)
            self._add_interval(new_intervals)
            assert self.manybody_wavefunction._check_consistency()
            self.evolve(time=self.time)

    def _error_estimate_quadpack(self, interval, error_op, return_estimate=False):
        r"""Error estimate for an integration quadrature.

        Parameters
        ----------
        interval : `tkwant.manybody.Interval`
            Integration interval with momentum boundaries *[a,b]*.
            The attribute `interval.quadrature` attribute must be "kronrod".
        error_op : callable or `kwant.operator`
            Observable used for the quadrature error estimate.
            Must have the calling signature of `kwant.operator`.
        return_estimate :bool, optional
            If true, return also the expectation value calculated with
            ``error_op``. It corresponds to the Kronrod :math:`K_{2n + 1}`
            estimate of the integral.

        Returns
        -------
        error : `~numpy.ndarray` of floats
            The quadrature error :math:`\varepsilon` estimated
            for the expectation value of the error_op.
            The output array has the same shape as evaluating ``error_op``.
        kronrod : `~numpy.ndarray` of floats, optional
            The expectation value of the error operator. Only returned
            if ``return_estimate`` is true.

        Notes
        -----
        An interval that is passed as argument via ``intervals``
        must already be present in the solver, othewise a ``KeyError``
        is raised.


        The error estimate is based on Quadpacks algorithm QAG. It is

        :math:`\varepsilon = \tilde{I} \text{min} \bigl\{1, (200
        \frac{G_n[a, b] - K_{2n + 1}[a, b]}{\tilde{I}})^{3/2} \bigr\}`,
        with
        :math:`\tilde{I} = \int_a^b |f(x) - \frac{K_{2n + 1}[a, b]}{b - a} |dx`

        where :math:`G_n[a, b]` is the Gauss and :math:`K_{2n + 1}[a, b]`
        the corresponding Kronrod estimate of the integral of *f(x)* over
        interval *[a, b]*. In our case, *f(x)* corresponds to the expectation
        value of the ``error_op`` at the current time of the solver.
        If the expectation value is an array,
        above expression for the error is evaluated point-wise on that array.

        .. [1] Piessens, R., de Doncker-Kapenga, E., Ueberhuber,
              C. W., and Kahaner, D. K.,
              QUADPACK A Subroutine Package for Automatic Integration,
              Springer-Verlag, Berlin, (1983).

        .. [2] Gonnet, P., A Review of Error Estimation in Adaptive Quadrature,
               ACM Computing Surveys, Vol. 44, No. 4, Article 22, (2012).
        """
        if not interval.quadrature == 'kronrod':
            raise ValueError('quadpack error estimate works only on '
                             'Gauss-Kronrod quadrature intervals')

        (gauss, kronrod), func = self._evaluate_interval(interval, error_op,
                                                         return_integrand=True)

        dk = interval.kmax - interval.kmin
        assert dk > 0
        kronrod_scaled = kronrod / dk

        integral = 0
        for key, f in func.items():
            kronrod_weight = self.manybody_wavefunction.tasks[key].math_weight[1]
            integral += kronrod_weight * np.abs(f - kronrod_scaled)
        ik = self.comm.allreduce(integral)

        assert (ik > 0).all()
        tmp = 200 * np.abs(gauss - kronrod) / ik
        error = np.squeeze(ik * np.minimum(1, tmp * np.sqrt(tmp)))
        if return_estimate:
            return error, kronrod
        return error

    def _error_estimate_gauss_kronrod(self, interval, error_op):
        r"""Maximal absolute error for the solver result with `quadrature="kronrod"`

        Parameters
        ----------
        intervals : `tkwant.manybody.Interval`
            Integration interval with momentum boundaries *[a,b]*.
        error_op : callable or `kwant.error_op`
            Observable used for the quadrature error estimate.
            Must have the calling signature of `kwant.error_op`.

        Returns
        -------
        error : float
            error estimate
            :math:`\delta = |G_n - K_{2 n+1}|`, where :math:`G_n`
            *n* point Gauss and :math:`K_{2 n+1}` the corresponding
            *2*n +1* Kronrod estimate.
        """
        gauss, kronrod = self._evaluate_interval(interval, error_op)
        return np.abs(gauss - kronrod)

    def estimate_error(self, intervals=None, error_op=None, estimate=None,
                       full_output=False):
        r"""Estimate the numerical error of the integration quadrature.

        Parameters
        ----------
        intervals : `tkwant.manybody.Interval` or sequence thereof, optional
            If present, the error is estimated on given intervals :math:`I_n`,
            otherwise the total error over all integrals is evaluated.
        error_op : callable or `kwant.operator`, optional
            Observable used for the quadrature error estimate.
            Must have the calling signature of `kwant.operator`.
            Default: ``error_op`` from initialization.
        estimate : callable, optional
            Function to estimate an error on an interval :math:`I_n`.
            Default: `_error_estimate_quadpack`, which estimates *abserr*
            of QUADPACK (see ``refine_intervals()``)
        full_output : bool, optional
            If the expectation value of ``error_op`` is an array and
            if ``full_output`` is true, then the error is estimated on each
            point of the array.
            By default, we only return the maximum value of the array error.

        Returns
        -------
        error : `~numpy.ndarray` of floats
            Error estimate of the momentum (energy) quadrature.

            - Evaluating this function without an argument for ``interval``
              is a measure of the total error and evaluates
              ``error`` = :math:`max(\sum_n^N I_n)`,
              where the sum runs over all *N*
              interval errors :math:`I_n` stored in the solver.
            - Evaluating this function on a sequence of intervals passed as
              argument via ``interval``, ``error`` is a sequence
              and the elements are :math:`max(I_n)`. (first index for intervals)
              The individual interval errors do NOT sum up to
              the total error mentioned above.
              This is due to the triangle inequality
              :math:`max(\sum_n^N I_n) \leq \sum_n^N max(I_n)`.
            - If ``full_output`` is true, no *max()* element is taken
              but the full array-like error of the observable is returned.
            - By default, the error :math:`I_n` is identical to *abserr* of
              QUADPACK, see ``refine_intervals()``.

        Notes
        -----
            An interval that is passed as argument via ``intervals``
            must already be present in the solver, othewise a ``KeyError``
            is raised.
        """
        if estimate is None:
            estimate = self._error_estimate_quadpack
        if error_op is None:
            error_op = self.error_op
        sum_up = False
        if intervals is None:
            intervals = self.get_intervals()
            sum_up = True
        if isinstance(intervals, collections.abc.Iterable):
            errors_per_interval = np.array([estimate(interval, error_op)
                                            for interval in intervals])
            if sum_up:
                errors = np.sum(errors_per_interval, axis=0)
                if not full_output:
                    errors = np.max(errors)
            else:
                if full_output:
                    errors = errors_per_interval
                else:
                    errors = np.array([np.max(err) for err in errors_per_interval])
        else:
            if full_output:
                errors = estimate(intervals, error_op)
            else:
                errors = np.max(estimate(intervals, error_op))
        return errors

    def evaluate(self, observable, root=0):
        """Evaluate the expectation value of an operator at the current time.

        Parameters
        ----------
        observable : callable or `kwant.operator`
            An operator to evaluate the expectation value.
            Must have the calling signature of `kwant.operator`.
        root : int or None, optional
            MPI return rank on which to return the result. If ``root`` is an
            integer, it must be in the range of valid MPI ranks
            ``0 <= root < self.comm.size``.
            In that case, the calculated result is returned
            only on that specific MPI rank where ``rank == root``, whereas the
            result is `None` on all other MPI ranks with ``rank != root``.
            Alternatively, if ``root`` is `None`,
            the calculated result is returned on all MPI ranks.
            Setting ``root`` to `None` is generally slower.
            By default, the result is returned on MPI rank zero only.

        Returns
        -------
        result : `~numpy.ndarray`
            The expectation value of ``observable``, integrated over all
            occupied bands. For Kronrod-like quadratures, the expectation
            value corresponding to the higher order rule is returned by
            default. Set the instance variable `return_element` to `None`
            or call the `evaluate` method of the base class directly, in
            order to get both, the higher and the lower order result.
            The result might not be returned on all MPI ranks;
            note the explanation above for input parameter ``root``.

        Notes
        -----
        Returning the result on all MPI ranks (by setting ``root=None``),
        might be slower, as an additional broadcast step is needed.
        """
        result = self.manybody_wavefunction.evaluate(observable, root)
        if self.return_element is None:
            return result
        try:
            return result[self.return_element]
        except Exception:  # catch `None` result on all non-MPI root ranks
            return result

    def evolve(self, time):
        """
        Evolve all wavefunctions up to ``time``.

        Parameters
        ----------
        time : int or float
            time argument up to which the solver should be evolved
        """
        self.manybody_wavefunction.evolve(time)
        self.time = time

    def add_boundstates(self, boundstate_psi, boundstate_tasks):
        """Add boundstates to the manybody solver

        Parameters
        ----------
        boundstate_psi : dict
            Dictionary with all boundstate wavefunctions.
            If a wavefunction is of type `tkwant.onebody.WaveFunction`
            and has an `evolve()` method, it is not changed.
            Otherwise, the wavefunction must be a `~numpy.ndarray` array
            and is taken as the initial value to
            construct a time dependent boundstate wave function from it.
            A dict key must be unique and present only on one MPI rank.
            For load balancing the dictionary should be
            distributed over all MPI ranks.
        boundstate_tasks : dict of `tkwant.onebody.Task`
            Each element in the dict represents a single boundstate state.
            An element must have at least the following attribute:

                - `weight` : float, weighting factor
                - `energy` : float, the energy of the bound state.

            ``boundstate_tasks`` must include all boundstates stored in
            ``boundstate_psi`` (all keys must be identical)
            and must be the same on all MPI ranks.
        """
        # if onebody_wavefunction_type cannot be extracted from
        # scattering_state_type, this routine fails, do at least some warning
        if self.onebody_wavefunction_type is None:
            logger.warning("wavefunction type is None, ",
                           "provided boundstates must be time dependent")
        make_boundstates_time_dependent(boundstate_psi, boundstate_tasks,
                                        self.syst, self.boundaries,
                                        self._params,
                                        self.onebody_wavefunction_type)
        add_boundstates(self.manybody_wavefunction, boundstate_psi, boundstate_tasks)


@log_func
def make_boundstates_time_dependent(boundstate_psi, boundstate_tasks,
                                    syst, boundaries, params=None,
                                    onebody_wavefunction=onebody.WaveFunction):
    """Make boundstates time dependent, such that they can evolve in time.

    Parameters
    ----------
    boundstate_psi : dict
        Dictionary with all boundstate wavefunctions.
        If a wavefunction is of type `tkwant.onebody.WaveFunction`
        and has an `evolve()` method, it is not changed.
        Otherwise, the wavefunction must be a `~numpy.ndarray` array
        and is taken as the initial value to
        construct a time dependent boundstate wave function from it. The
        the original wavefunction is then replaced by the time dependent
        one in place. For load balancing the dictionary should be
        distributed over all MPI ranks.
    boundstate_tasks : dict of `tkwant.onebody.Task`
        Each element in the dict represents a single boundstate state.
        An element must have at least the following attribute:

            - `weight` : float, weighting factor
            - `energy` : float, the energy of the bound state.

        ``boundstate_tasks`` must include all boundstates stored in
        ``boundstate_psi`` (all keys must be identical)
        and must be the same on all MPI ranks.
    syst : `kwant.builder.FiniteSystem`
        The low level system.
    boundaries : sequence of `~tkwant.leads.BoundaryBase`
        The boundary conditions for each lead attached to ``syst``.
        Must have the same length as ``syst.leads``.
    params : dict, optional
        Extra arguments to pass to the Hamiltonian of ``syst``,
        excluding time.
    onebody_wavefunction : `tkwant.onebody.WaveFunction`, optional
        Class to evolve a single-particle wavefunction in time.

    Notes
    -----
    This routine changes ``boundstate_psi`` in place.
    """
    for key, psi in boundstate_psi.items():
        if not hasattr(psi, 'evolve'):
            energy = boundstate_tasks[key].energy
            boundstate_psi[key] = onebody_wavefunction(psi_init=psi, syst=syst,
                                                       boundaries=boundaries,
                                                       energy=energy,
                                                       params=params)


@log_func
def add_boundstates(solver, boundstate_psi, boundstate_tasks):
    """Add a sequence of boundstates to the manybody solver

    Parameters
    ----------
    solver : `tkwant.manybody.WaveFunction`
        Manybody solver to which the boundstates should be added.
    boundstate_psi : dict of `tkwant.onebody.WaveFunction`
        Dictionary with all boundstate wavefunctions.
        A dict key must be unique and present only on one MPI rank.
        For load balancing the dictionary should be distributed over
        all MPI ranks.
    boundstate_tasks : dict of `tkwant.onebody.Task`
        Each element in the dict represents a single boundstate state.
        An element must have at least the following attribute:

            - `weight` : float, weighting factor

        ``boundstate_tasks`` must include all boundstates stored in
        ``boundstate_psi`` (all keys must be identical)
        and must be the same on all MPI ranks.
        Moreover, the keys of the boundstates dicts (``boundstate_tasks`` and
        ``boundstate_psi``) must not be present in ``solver``.

    Notes
    -----
    ``solver`` is modified in place. Only when the error
    "boundstate key=.. already present in solver" occurs, ``solver`` has not
    been modified. If any other exception is raised in this function however,
    there is no guarantee that the ``solver`` has not been modified.
    """
    solver_keys = solver.get_keys()
    for b_key in boundstate_tasks.keys():
        if b_key in solver_keys:
            raise KeyError('boundstate key={} already present in solver.'
                           .format(b_key))

    weight_shape = np.ones(shape=solver.weight_shape())
    tasks = copy.deepcopy(boundstate_tasks)
    for key, task in tasks.items():
        tasks[key].weight = task.weight * weight_shape
    solver.add_distributed_onebody_states(boundstate_psi, tasks)


class ManybodyIntegrand:

    def __init__(self, syst, interval, operator, time=0, params=None, element=None):
        """Diagnostic routine to evaluate the integrand in the manybody integral

        For simplicity, this routine evaluates the integrand only on
        a single lead and band

        Parameters
        ----------

        syst : `kwant.builder.FiniteSystem`
            The low level system for which the wave functions are to be
            calculated.
        interval : `tkwant.manybody.Interval`
            the interval specifying integration region, lead and band
        operator : callable or `kwant.operator`, optional
            operator representing the physical observable
        time : float, optional
            The time at which the integrand will be calculated.
        params : dict, optional
            Extra arguments to pass to the Hamiltonian of ``syst``,
            excluding time.
        element: int, optional
            if the operator has a vector like output, elemnt can be set
            to select only a specific element.
        """

        tparams = add_time_to_params(params, time_name='time',
                                     time=0, check_numeric_type=True)

        spectra = kwantspectrum.spectra(syst.leads, params=tparams)
        self.boundaries = leads.automatic_boundary(spectra, tmax=time + 1)

        self.syst = syst
        self.band = interval.band
        self.lead = interval.lead
        self.kmin = interval.kmin
        self.kmax = interval.kmax
        self.integration_variable = interval.integration_variable
        self.time = time
        self.operator = operator
        self.params = params
        self.spectrum = spectra[self.lead]
        self.element = element
        self.neval = 0

    def func(self, x):
        """integrand for the manybody expectation value at zero temperature

        Parameters
        ----------

        x : float
            integration varable, if ``interval.integration_variable`` == 'energy'
            x corresponds to the energy, else if
            ``interval.integration_variable`` == 'momentum' it is interpreted
            as momentum k.

        Returns
        -------
        result : `~numpy.ndarray`
            The evaluated integrand

        """
        self.neval += 1
        if self.integration_variable == 'energy':
            energy = x
            velocity = 1  # for jacoby determinant
            mode = self.spectrum.energy_to_scattering_mode(energy, self.band,
                                                           self.kmin, self.kmax)
        elif self.integration_variable == 'momentum':
            energy = self.spectrum(x, band=self.band)
            velocity = self.spectrum(x, band=self.band, derivative_order=1)
            mode = self.spectrum.momentum_to_scattering_mode(x, self.band)
        else:
            raise ValueError('integration_variable = {} not known.'
                             .format(self.integration_variable))

        if mode == - 1:  # mode is closed
            msg = ('no open mode for energy={}, lead={}, band={}, kmin={}, kmax={}'
                   .format(energy, self.lead, self.band, self.kmin, self.kmax))
            logger.warning(msg)
            return

        psi = onebody.ScatteringStates(self.syst, energy=energy,
                                       lead=self.lead, params=self.params,
                                       boundaries=self.boundaries)[mode]

        psi.evolve(self.time)

        result = velocity * psi.evaluate(self.operator) / (2 * np.pi)
        if self.element is None:
            return result
        return result[self.element]

    def vecfunc(self, k):
        """same as func, but for vector like arguments"""
        return np.array([self.func(kk) for kk in k])
