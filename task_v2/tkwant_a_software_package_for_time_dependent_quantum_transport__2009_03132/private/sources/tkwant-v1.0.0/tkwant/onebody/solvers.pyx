# -*- coding: utf-8 -*-
#
# Copyright 2016 - 2020 tkwant authors.
#
# This file is part of tkwant.  It is subject to the license terms in the file
# LICENSE.rst found in the top-level directory of this distribution and at
# http://kwant-project.org/license.  A list of tkwant authors can be found in
# the file AUTHORS.rst at the top-level directory of this distribution and at
# http://kwant-project.org/authors.
"""Classes for solving the time-dependent Schrödinger equation."""

import numpy as np
import scipy.integrate

from . cimport kernels
from . import kernels


__all__ = ['Scipy']


class Scipy:
    """Solve the time-dependent Schrödinger equation using `scipy.integrate`.

    This solver will currently only work with the 'dopri5' and 'dop853'
    integrators, as these are the only re-entrant ones.

    Parameters
    ----------
    kernel : `tkwant.onebody.kernels.Kernel`
    integrator : `scipy.integrate._ode.IntegratorBase`, default: dopri5
        The integrator to use with this solver.
    **integrator_options
        Options to pass when instantiating the integrator.

    See Also
    --------
    scipy.integrate.ode
    """

    _default_options = {'atol': 1E-9, 'rtol': 1E-9, 'nsteps': int(1E9)}

    def __init__(self, kernel, integrator=scipy.integrate._ode.dopri5, **integrator_options):
        self.kernel = kernel
        # allocate storage for kernel output
        self._rhs_out = np.empty((kernel.size,), dtype=complex)

        options = dict(self._default_options)
        options.update(integrator_options)
        self._integrator = integrator(**options)
        # Factor 2 because Scipy integrators expect real arrays
        self._integrator.reset(2 * self.kernel.size, has_jac=False)

    def _rhs(self, t, y):
        # Kernel expects complex, Scipy expects real
        self.kernel.rhs(y.view(complex), self._rhs_out, t)
        return self._rhs_out.view(float)

    def __call__(self, psi, time, next_time):
        if time == next_time:
            return psi
        # psi is complex, Scipy expects real
        next_psi, final_time = self._integrator.run(
            self._rhs, lambda: None, psi.view(float), time, next_time, (), ())
        if not self._integrator.success:
            raise RuntimeError('Integration failed between {} and {}'
                               .format(time, next_time))
        assert final_time == next_time
        return next_psi.view(complex)


default = Scipy
