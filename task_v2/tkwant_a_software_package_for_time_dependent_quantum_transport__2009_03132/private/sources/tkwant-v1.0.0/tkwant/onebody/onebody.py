# Copyright 2016-2020 tkwant authors.
#
# This file is part of tkwant.  It is subject to the license terms in the file
# LICENSE.rst found in the top-level directory of this distribution and at
# http://kwant-project.org/license.  A list of tkwant authors can be found in
# the file AUTHORS.rst at the top-level directory of this distribution and at
# http://kwant-project.org/authors.
"""Tools for solving the one-body time-dependent Schrödinger equation."""

import collections.abc
import functools
from cmath import exp
import numpy as np
import scipy.sparse as sp

import kwant
import kwantspectrum

from .. import leads, _common, _logging
from ..system import hamiltonian_with_boundaries, add_time_to_params
from . import kernels, solvers

__all__ = ['WaveFunction', 'ScatteringStates', 'Task']


# set module logger
logger = _logging.make_logger(name=__name__)
log_func = _logging.log_func(logger)


# data formats

class Task:
    """Data format to store the set of quantum numbers that uniquely indentifies
    a onebody state and the weight of that state in the manybody sum.

    Attributes
    ----------
    lead : int
        lead index
    mode : int
        scattering mode index
    energy : float
        energy of the onebody state
    momentum : float
        momentum of the onebody state
    weight : float or numpy float array
        weighting factor of the one-body state in the manybody sum
        weigth = math_weight * phys_weight, where math_weight is the weighting
        factor from the integration quadrature
    math_weight : float or numpy float array
        mathematical weighting factor from the numerical quadrature rule
    phys_weight : float
        physical weighting factor (fermi function, pi factors..)
    """
    def __init__(self, lead: int, mode: int, energy: float, weight: float,
                 math_weight: float = None, phys_weight: float = None,
                 momentum: float = None):
        self.lead = lead
        self.mode = mode
        self.energy = energy
        self.momentum = momentum
        self.weight = weight
        self.math_weight = math_weight
        self.phys_weight = phys_weight

    def __eq__(self, other) -> bool:
        if not isinstance(other, Task):
            return NotImplemented
        return (
            (self.lead, self.mode, self.energy, self.momentum,
             self.weight, self.math_weight, self.phys_weight) ==
            (other.lead, other.mode, other.energy, other.momentum,
             other.weight, other.math_weight, other.phys_weight))

    def __str__(self):
        string = "onebody task: lead={lead}, mode={mode}, " \
                 "energy={energy}, momentum={momentum}, " \
                 "weight={weight}, math_weight={math_weight}, " \
                 "phys_weight={phys_weight}".format(**self.__dict__)
        return string


def _operator_bound(operator):
    """Return True iff operator is bound"""
    try:
        return bool(operator._bound_onsite or operator._bound_hamiltonian)
    except AttributeError:
        if hasattr(operator, '_bound_onsite'):
            return bool(operator._bound_onsite)
        if hasattr(operator, '_bound_hamiltonian'):
            return bool(operator._bound_hamiltonian)
        return False


class WaveFunction:
    r"""A class to solve the time-dependent single-particle wavefunction.

    The time-dependent single-particle Schrödinger equation is

        :math:`i \partial_t \psi = (H_0 + W(t)) \psi`,

    where the total Hamiltonian :math:`H(t) = H_0 + W(t)` has been splitted
    into a static part :math:`H_0` and a time-dependent perturbation
    :math:`W(t)`. Moreover, the initial condition is :math:`\psi(t_0)`
    and :math:`W(t)` is expected to be absent before the initial time
    :math:`t_0`:

        :math:`W(t) = 0 \,\, \text{for} \,\, t \leq t_0`.

    If an energy :math:`E` is provided, this routine expects that
    the initial condition represents the scattering state :math:`\psi_{st}`
    that solves the time-independent Schrödinger equation

        :math:`H_0 \psi_{st} = E \psi_{st}, \, \psi_{st} = \psi(t_0)`.

    For numerical reasons, the evolution is then performed in the variable

        :math:`i \partial_t \bar{\psi} = (H_0 + W(t) - E) \bar{\psi} + W(t) \psi_{st}`,

    where

        :math:`\psi = (\bar{\psi} - \psi_{st}) e^{-i E (t - t_0)}`.

    See `J. Weston and X. Waintal, Phys. Rev. B 93, 134506 (2016)
    <https://arxiv.org/abs/1510.05967>`_.
    """
    def __init__(self, H0, W, psi_init, energy=None, params=None,
                 solution_is_valid=None, time_is_valid=None,
                 time_start=_common.time_start, time_name=_common.time_name,
                 kernel_type=kernels.default, solver_type=solvers.default):
        r"""
        Parameters
        ----------
        H0 : array-like
            The static part of the Hamiltonian matrix, :math:`H_0`.
        W : callable or `None`
            Time-dependent part of the Hamiltonian matrix, :math:`W(t)`. Typically
            the object returned by `tkwant.system.extract_perturbation`.
        psi_init : array of complex
            The state :math:`\psi(t_0)` from which to start, defined over the
            central region.
        energy : float, optional
            If provided, then ``psi_init`` is assumed to be an eigenstate
            of energy :math:`E`. If the Hamiltonian represents an open
            quantum system with leads, then ``psi_init`` is
            assumed to be the projection of a scattering state at energy :math:`E`
            on to the central part of the system.
        params : dict, optional
            Extra arguments to pass to the time-dependent Hamiltonian
            function :math:`W(t)`, excluding time.
        solution_is_valid : callable, optional
            Function to detect spurious reflections for a system with leads.
            See `tkwant.leads.EvaluatedBoundary`.
        time_is_valid : callable, optional
            Function to check if boundary conditions are valid at a given time.
            See `tkwant.leads.EvaluatedBoundary`.
        time_start : float, optional
            The initial time :math:`t_0`. Default value is zero.
        time_name : str, optional
            The name of the time argument :math:`t`. Default name: *time*.
        kernel_type : `tkwant.onebody.solvers.default`, optional
            The kernel to calculate the right-hand-site of the
            Schrödinger equation.
        solver_type : `tkwant.onebody.solvers.default`, optional
            The solver used to evolve the wavefunction forward in time.
        """

        # The size of the central scattering region. The central scattering
        # region can be smaller as the total size (kernel.size) of the system
        # in case of boundary conditions.
        syst_size = psi_init.size
        hamiltonian_size = H0.shape[0]

        if syst_size > hamiltonian_size:
            raise ValueError('initial condition size={} is larger than the '
                             'Hamiltonian matrix H0 size={}'
                             .format(syst_size, hamiltonian_size))

        # The perturbation W(t) must, if present, always match the size of the
        # central scattering region. The true leads are never time dependent.
        if W is not None:
            if not W.size == syst_size:
                raise ValueError('initial condition size={} must be equal '
                                 'to the perturbation W size={}'
                                 .format(syst_size, W.size))

        # add initial time to the params dict
        tparams = add_time_to_params(params, time_name=time_name,
                                     time=time_start, check_numeric_type=True)

        if energy is None:
            # starting from an arbitrary state, so we need
            # to be solving: H0 @ psi + W(t) @ psi
            kernel = kernel_type(H0, W, params=tparams)

        else:
            # we are starting from an eigenstate, so we need to
            # be solving: (H0 - E) @ psibar + W(t) @ (psibar + psi_st)
            # and psi = (psibar + psi_st) * exp(-1j * energy * time)
            kernel = kernel_type(H0 - energy * sp.eye(hamiltonian_size),
                                 W, tparams, np.asarray(psi_init))

        # get the object that will actually do the time stepping
        self.solver = solver_type(kernel)

        # transform initial psi to psibar and psi_st
        # note that the dgl is always solved in the variable psibar
        psibar = np.zeros((kernel.size,), complex)
        if energy is not None:
            psi_st = np.array(psi_init, complex)
        else:
            psi_st = None
            psibar[:syst_size] = psi_init

        self.psibar = psibar
        self.psi_st = psi_st

        self._syst_size = syst_size
        self._solution_is_valid = solution_is_valid
        self._time_is_valid = time_is_valid

        self.time_name = time_name
        self.time_start = time_start

        self.time = time_start
        self.params = params
        self.energy = energy

    @classmethod
    def from_kwant(cls, syst, psi_init, boundaries=None, energy=None, params=None,
                   time_start=_common.time_start, time_name=_common.time_name,
                   kernel_type=kernels.default, solver_type=solvers.default,
                   perturbation_type=kernels.PerturbationInterpolator):
        """Set up a time-dependent onebody wavefunction from a kwant system.

        Parameters
        ----------
        syst : `kwant.builder.FiniteSystem`
            The low level system for which the wave functions are to be
            calculated.
        psi_init : array of complex
            The state from which to start, defined over the central region.
        boundaries : sequence of `~tkwant.leads.BoundaryBase`, optional
            The boundary conditions for each lead attached to ``syst``.
            Must be provided for a system with leads.
        energy : float, optional
            If provided, then ``psi_init`` is assumed to be an eigenstate
            of energy *E*. If ``syst`` has leads, then ``psi_init`` is
            assumed to be the projection of a scattering state at energy *E*
            on to the central part of the system.
        params : dict, optional
            Extra arguments to pass to the Hamiltonian of ``syst``, excluding time.
        time_start : float, optional
            The initial time :math:`t_0`. Default value is zero.
        time_name : str, optional
            The name of the time argument :math:`t`. Default name: *time*.
        kernel_type : `tkwant.onebody.solvers.default`, optional
            The kernel to calculate the right-hand-site of the
            Schrödinger equation.
        solver_type : `tkwant.onebody.solvers.default`, optional
            The solver used to evolve the wavefunction forward in time.
        perturbation_type : `tkwant.onebody.kernels.ExtractPerturbation`, optional
            Class to extract the time dependent perturbation :math:`W(t)`
            out of ``syst``.

        Returns
        -------
        wave_function : `tkwant.onebody.WaveFunction`
            A time-dependent onebody wavefunction at the initial time.
        """

        if not isinstance(syst, kwant.system.System):
            raise TypeError('"syst" must be a finalized kwant system')

        syst_size = syst.site_ranges[-1][2]
        if not psi_init.size == syst_size:
            raise ValueError('Size of the initial condition={} does not match '
                             'the total number of orbitals in the central '
                             'system ={}'.format(psi_init.size, syst_size))

        # add initial time to the params dict
        tparams = add_time_to_params(params, time_name=time_name,
                                     time=time_start, check_numeric_type=True)

        if syst.leads:
            # need to add boundary conditions
            if not boundaries:
                raise ValueError('Must provide boundary conditions for systems '
                                 'with leads.')
            # get static part of Hamiltonian for central system + boundary conditions
            # TODO: Make this work with arbitrary kwant.system.FiniteSystem.
            extended_system = hamiltonian_with_boundaries(syst, boundaries,
                                                          params=tparams)
            H0 = extended_system.hamiltonian
            solution_is_valid = extended_system.solution_is_valid
            time_is_valid = extended_system.time_is_valid
        else:
            # true finite systems (no leads) so no need for boundary conditions
            if boundaries is not None:
                raise ValueError('No boundary conditions must be provided '
                                 'for a system without leads.')
            H0 = syst.hamiltonian_submatrix(params=tparams, sparse=True)
            solution_is_valid = None
            time_is_valid = None

        W = perturbation_type(syst, time_name, time_start, params=params)

        return cls(H0, W, psi_init, energy, params,
                   solution_is_valid, time_is_valid,
                   time_start, time_name, kernel_type, solver_type)

    def psi(self):
        r"""Return the wavefunction :math:`\psi(t)` at the current time *t*.

        psi : `~numpy.ndarray`
            The wavefunction at ``time``. If this wavefunction is
            for a system with leads, then the wavefunction projected
            onto the central region is returned.
        """
        if self.energy is None:  # psi = psibar
            return self.psibar[:self._syst_size].copy()
        # else : psi = (psibar + psi_st) * exp(-i E (t - t0))
        return ((self.psibar[:self._syst_size] + self.psi_st) *
                exp(-1j * self.energy * (self.time - self.time_start)))

    def evolve(self, time, params=None):
        r"""
        Evolve the wavefunction :math:`\psi(t)` foreward in time up to
        :math:`t =` ``time``.

        Parameters
        ----------
        time : int or float
            time argument up to which the solver should be evolved
        """
        # `time` corresponds to the future time, to which we will evolve
        if time < self.time:
            raise ValueError('Cannot evolve backwards in time')
        if time == self.time:
            return
        if self._time_is_valid is not None:
            if not self._time_is_valid(time):
                raise RuntimeError('Cannot evolve up to {} with the given '
                                   'boundary conditions'.format(time))

        # evolve forward in time
        next_psibar = self.solver(self.psibar, self.time, time)

        if self._solution_is_valid is not None:
            if not self._solution_is_valid(next_psibar):
                raise RuntimeError('Evolving between {} and {} resulted in an '
                                   'unphysical result due to the boundary '
                                   'conditions'.format(self.time, time))
        # update internal state and return
        self.psibar, self.time = next_psibar, time

    def evaluate(self, observable):
        r"""
        Evaluate the expectation value of an operator at the current time *t*.

        For an operator :math:`\hat{O}` the expectation value is
        :math:`O(t) = \langle \psi(t) | \hat{O} |\psi(t) \rangle`.

        Parameters
        ----------
        observable : callable or `kwant.operator`
            An operator :math:`\hat{O}` to evaluate the expectation value.
            Must have the calling signature of `kwant.operator`.

        Returns
        -------
        result : numpy array
            The expectation value :math:`O(t)` of ``observable``.
        """
        if _operator_bound(observable):
            raise ValueError("Operator must not use pre-bind values")

        tparams = add_time_to_params(self.params, time_name=self.time_name,
                                     time=self.time)
        return observable(self.psi(), params=tparams)


class ScatteringStates(collections.abc.Iterable):
    """Calculate time-dependent wavefunctions starting in an equilibrium scattering state"""

    def __init__(self, syst, energy, lead, tmax=None, params=None, spectra=None,
                 boundaries=None, equilibrium_solver=kwant.wave_function,
                 wavefunction_type=WaveFunction.from_kwant):
        """
        Parameters
        ----------
        syst : `kwant.builder.FiniteSystem`
            The low level system for which the wave functions are to be
            calculated.
        energy : float
            Energy of the scattering eigenstate.
        lead : int
            Lead index to construct the scattering state.
        tmax : float, optional
            The maximum time up to which to simulate. Sets the boundary conditions
            such that they are guaranteed to be correct up to 'tmax'. Mutually
            exclusive with 'boundaries'.
        params : dict, optional
            Extra arguments to pass to the Hamiltonian of ``syst``, excluding time.
        spectra : sequence of `kwantspectrum.spectrum`, optional
            Energy dispersion :math:`E_n(k)` for the leads. Must have
            the same length as ``syst.leads``. Required only if
            no ``boundaries`` are provided. If needed but not present,
            it will be calculated on the fly from `syst.leads`.
        boundaries : sequence of `~tkwant.leads.BoundaryBase`, optional
            The boundary conditions for each lead attached to ``syst``. Mutually
            exclusive with 'tmax'.
        equilibrium_solver : `kwant.wave_function`, optional
            Solver for initial equilibrium scattering problem.
        wavefunction_type : `WaveFunction`, optional
            One-body time-dependent wave function. Name of the time argument and
            initial time are taken from this class. If this is not possible,
            default values are used as a fallback.

        Notes
        -----
        An instance of this class behaves like a sequence of `WaveFunction`
        instances. The index in the sequence corresponds to the scattering mode.
        The name of the time argument (`time_name`) and the initial time
        of the evolution (`time_start`) are taken from the default
        values of the `WaveFunction.__init__` method. Changing the default
        values by partial prebind (e.g. via functools) is possible.
        """

        if not isinstance(syst, kwant.system.System):
            raise TypeError('"syst" must be a finalized kwant system')
        if not syst.leads:
            raise AttributeError("system has no leads.")
        if tmax is not None and boundaries is not None:
            raise ValueError("'boundaries' and 'tmax' are mutually exclusive.")
        if not _common.is_type(energy, 'real_number'):
            raise TypeError('energy must be a real number')
        if not _common.is_type(lead, 'integer'):
            raise TypeError('lead index must be an integer')
        if lead >= len(syst.leads):
            raise ValueError("lead index must be smaller than {}.".format(len(syst.leads)))

        # get initial time and time argument name from the onebody wavefunction
        try:
            time_name = _common.get_default_function_argument(wavefunction_type,
                                                              'time_name')
            time_start = _common.get_default_function_argument(wavefunction_type,
                                                               'time_start')
        except Exception:
            time_name = _common.time_name
            time_start = _common.time_start
            logger.warning('retrieving initial time and time argument name from',
                           'the onebody wavefunction failed, use default values: ',
                           '"time_name"={}, "time_start"={}'.format(time_name,
                                                                    time_start))

        # add initial time to the params dict
        tparams = add_time_to_params(params, time_name=time_name,
                                     time=time_start, check_numeric_type=True)

        if boundaries is None:
            if spectra is None:
                spectra = kwantspectrum.spectra(syst.leads, params=tparams)
            boundaries = leads.automatic_boundary(spectra, tmax)

        scattering_states = equilibrium_solver(syst, energy=energy, params=tparams)
        self._psi_st = scattering_states(lead)
        self._wavefunction = functools.partial(wavefunction_type, syst=syst,
                                               boundaries=boundaries, params=params)
        self.energy = energy
        self.lead = lead

    def __getitem__(self, mode):
        """Return a time-dependent wavefunction for the corresponding scattering mode.

        Parameters
        ----------
        mode : int
            Mode index of the scattering wavefunction.

        Returns
        -------
        wave_function : `WaveFunction`
            The time-dependent wave function starting in the scattering mode.
            Two additional attributes, ``lead`` and ``mode`` are added
            to the wave function.
        """

        if not _common.is_type(mode, 'integer'):
            raise TypeError('mode index must be an integer')
        if mode >= len(self._psi_st):
            raise KeyError('no open scattering mode={}; '
                           'number of open modes={} for energy={} and lead={}'
                           .format(self.lead, mode, self.energy, len(self._psi_st)))
        psi = self._wavefunction(psi_init=self._psi_st[mode], energy=self.energy)
        psi.lead = self.lead
        psi.mode = mode
        return psi

    def __len__(self):
        """Return the number of open scattering modes."""
        return len(self._psi_st)

    def __iter__(self):
        """Return an iterable sequence of all open modes."""
        return (self[mode] for mode in range(len(self)))
