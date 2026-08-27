# -*- coding: utf-8 -*-
# Copyright 2016-2019 tkwant authors.
#
# This file is part of tkwant.  It is subject to the license terms in the file
# LICENSE.rst found in the top-level directory of this distribution and at
# http://kwant-project.org/license.  A list of tkwant authors can be found in
# the file AUTHORS.rst at the top-level directory of this distribution and at
# http://kwant-project.org/authors.

"""Test module for `tkwant.integration`"""

import math
import numpy as np
from numpy.testing import assert_almost_equal, assert_array_almost_equal
import pytest

from .. import integration


# (function, (a, b), integral)
functions = [
    (lambda x: x**2, (-1, 1), 2 / 3),
    (lambda x: 2 * np.exp(-x**2) / math.sqrt(math.pi), (0, 1), math.erf(1)),
    (lambda x: np.sin(x), (0, math.pi), 2),
]


def test_calc_abscissas_and_weights():

    # test the numerics
    quadrature_methods = ['gausslegendre', 'kronrod']
    nb_points = [10, 15, 20]

    def test_fixed(method, function, n):
        f, (a, b), exact_result = function
        x, w = integration.calc_abscissas_and_weights(a, b, n, method)
        if w.ndim == 1:  # for weight-vector (eg. gauss-legendre)
            result = np.sum(w * f(x))
            assert_almost_equal(result, exact_result)
            assert x.shape == (n,)
            assert w.shape == (n,)
        else:  # for weight-matrix (gauss-kronrod)
            results = np.sum(w * f(x), axis=1)
            [assert_almost_equal(result, exact_result) for result in results]
            assert x.shape == (2 * n + 1,)
            assert w.shape == (2, 2 * n + 1)

    for method in quadrature_methods:
        for func in functions:
            for n in nb_points:
                test_fixed(method, func, n)

    to_test = integration.calc_abscissas_and_weights

    a, b = (-2, 2)
    n = 20
    quadrature = 'gausslegendre'

    # test error raises
    # bounds swapped
    pytest.raises(ValueError, to_test, a=b, b=a, n=n, quadrature=quadrature)
    # invalid number of points
    pytest.raises(ValueError, to_test, a, b, n=0, quadrature=quadrature)
    pytest.raises(ValueError, to_test, a, b, n=-1, quadrature=quadrature)
    # nonexisting method
    pytest.raises(NotImplementedError, to_test, a, b, n, quadrature='bla')


def test_trapezoidal_rule():

    x, w = integration._trapezoidal_rule(n=2)
    assert_array_almost_equal(x, [-1, 1])
    assert_array_almost_equal(w, [1, 1])

    x, w = integration._trapezoidal_rule(n=3)
    assert_array_almost_equal(x, [-1, 0, 1])
    assert_array_almost_equal(w, [0.5, 1, 0.5])

    x, w = integration._trapezoidal_rule(n=4)
    assert_array_almost_equal(x, [-1, - 1 / 3, 1 / 3, 1])
    assert_array_almost_equal(w, (1 / 3) * np.array([1, 2, 2, 1]))

    with pytest.raises(ValueError) as exc:
        integration._trapezoidal_rule(1)
    assert str(exc.value) == 'n=1 must >= 2'
