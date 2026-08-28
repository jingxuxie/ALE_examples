# -*- coding: utf-8 -*-
# Copyright 2016-2019 tkwant authors.
#
# This file is part of tkwant.  It is subject to the license terms in the file
# LICENSE.rst found in the top-level directory of this distribution and at
# http://kwant-project.org/license.  A list of tkwant authors can be found in
# the file AUTHORS.rst at the top-level directory of this distribution and at
# http://kwant-project.org/authors.
"""Tools for calculating numeric integrals."""

import numpy as np
from . import line_segment

__all__ = ['calc_abscissas_and_weights']


def _trapezoidal_rule(n):
    """Calculate trapezoidal abcissas and weights on an interval [-1, 1]

    Parameters
    ----------
    n : int
        Number of quadrature points. Must be >= 2.

    Returns
    -------
    x : Numpy float array
        abscissa values

    w : Numpy float array
        quadrature weights
    """

    if n < 2:
        raise ValueError('n={} must >= 2'.format(n))

    x = np.linspace(-1, 1, n)
    dx = 2 / (n - 1)

    if n == 2:
        w = np.array([0.5, 0.5])
    else:
        w = np.ones(n - 2)
        w = np.insert(w, 0, 0.5)
        w = np.append(w, 0.5)
    return x, w * dx


def calc_abscissas_and_weights(a, b, n, quadrature):
    """Abscissas and weights for fixed-order integration quadratures.

    Parameters
    ----------
    a : float
        Lower limit of integration.
    b : float
        Upper limit of integration.
    n : int
        Order of quadrature integration. Must be positive, n > 0
    quadrature : string
        Quadrature rule to use. Possible choices:\n
        * **gausslegendre**: order ``n`` Gauss-Legendre\n
        * **kronrod**: order ``n`` and ``2 n + 1`` Gauss-Kronrod\n
        * **trapezoidal**: ``n`` point trapezoidal rule\n
        * **trapezoidal-2**: ``n`` and ``2 n - 1`` point trapezoidal rule\n
    Returns
    -------
    x : Numpy float array
        abscissa values

    w : Numpy float array
        quadrature weights

    Notes
    -----
    - For the Guass-Legendre quadrature, both `x` and `w` are one-dimensional
      numpy arrays of shape `(n, )`.
      A one-dimensional integral :math:`\\int_a^b f(x) dx` can
      be approximated by an order ``n`` quadrature via ``np.sum(w * f(x))``.
    - For the Gauss-Kronrod quadrature, `x` is a one dimensional numpy array of
      shape `(2*n+1,)` and `w` is a two-dimensional array of shape
      `(2, 2*n+1)`. A one-dimensional integral :math:`\\int_a^b f(x) dx`
      can be approximated by ``result = np.sum(w * f(x), axis=1)``.
      The element `result[0]` then corresponds to the lower-order (`n`)
      and the second element `result[1]` corresponds to the higher-order
      (`2*n + 1`) approximation of the integral.
    - For general quadratures with array-like weights aka Gauss-Kronrod,
      we use the convention that the last element of the first array index
      corresponds to the higher-order rule.
    """

    if a > b:
        raise ValueError('lower bound={} is larger then upper bound={}'
                         .format(a, b))
    if n <= 0:
        raise ValueError('number of points={} must be positive'.format(n))
    if not np.issubdtype(type(n), np.integer):
        raise TypeError('number of points={} must be an integer'.format(n))

    # weights and abscissas in intervall [-1, 1]
    w2 = None
    if quadrature == 'gausslegendre':
        x, w = np.polynomial.legendre.leggauss(n)
    elif quadrature == 'kronrod':
        gausskronrod = line_segment.GaussKronrod(n)
        _, _w1 = np.polynomial.legendre.leggauss(n)
        x = gausskronrod.points
        w2 = gausskronrod.weights
        w1 = np.zeros(2 * n + 1)
        w1[1::2] = _w1
        w = np.vstack((w1, w2))
    elif quadrature == 'trapezoidal':
        x, w = _trapezoidal_rule(n)
    elif quadrature == 'trapezoidal-2':  # 2n-1 point rule for error estimate
        _, _w1 = _trapezoidal_rule(n)
        x, w2 = _trapezoidal_rule(2 * n - 1)
        w1 = np.zeros(2 * n - 1)
        w1[0::2] = _w1
        w = np.vstack((w1, w2))
    else:
        raise NotImplementedError('quadrature={} not implemented'
                                  .format(quadrature))

    # rescale weights and abscissas to interval [a, b]
    x, w = _rescale_interval(a, b, x, w)
    return x, w


def _rescale_interval(a, b, x, w):
    """rescale weights and abscissas from intervall [-1, 1] to [a, b]"""
    pp = (b + a) / 2
    mm = (b - a) / 2
    return np.array(x) * mm + pp, np.array(w) * mm
