# -*- coding: utf-8 -*-
#
# This file is part of the project tkwant. It contains code taken out of
# the quadpy and the orthopy libraries from Nico Schlömer. 
# Both libraries are licensed under the MIT License given below.
#
# The MIT License (MIT)
#
# Copyright (c) 2016-2018 Nico Schlömer
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import division

import math
import numpy
import scipy.special
import sympy

# The mpmath package is not needed for GaussKronrod
# from mpmath import mp
# from mpmath.matrices.eigen_symmetric import tridiag_eigen
from scipy.linalg import eig_banded
from scipy.linalg.lapack import get_lapack_funcs

__all__ = ['GaussKronrod']


class GaussLegendre(object):
    """
    Gauss-Legendre quadrature.
    """

    def __init__(self, n, mode="numpy", decimal_places=None):

        self.degree = 2 * n - 1

        if mode == "numpy":
            self.points, self.weights = numpy.polynomial.legendre.leggauss(n)
        else:
            _, _, alpha, beta = legendre(
                n, "monic", symbolic=True
            )
            self.points, self.weights = scheme_from_rc(
                alpha, beta, mode=mode, decimal_places=decimal_places
            )
        return


class GaussKronrod(object):
    """
    Gauss-Kronrod quadrature; see
    <https://en.wikipedia.org/wiki/Gauss%E2%80%93Kronrod_quadrature_formula>.

    Besides points and weights, this class provides the weights of the
    corresponding Gauss-Legendre scheme in self.gauss_weights.

    Code adapted from
    <https://www.cs.purdue.edu/archives/2002/wxg/codes/r_kronrod.m>,
    <https://www.cs.purdue.edu/archives/2002/wxg/codes/kronrod.m>.
    See

    Calculation of Gauss-Kronrod quadrature rules,
    Dirk P. Laurie,
    Math. Comp. 66 (1997), 1133-1145,
    <https://doi.org/10.1090/S0025-5718-97-00861-2>

    Abstract:
    The Jacobi matrix of the $(2n+1)$-point Gauss-Kronrod quadrature rule for a
    given measure is calculated efficiently by a five-term recurrence relation.
    The algorithm uses only rational operations and is therefore also useful
    for obtaining the Jacobi-Kronrod matrix analytically. The nodes and weights
    can then be computed directly by standard software for Gaussian quadrature
    formulas.
    """

    def __init__(self, n, a=0.0, b=0.0):
        # The general scheme is:
        # Get the Jacobi recurrence coefficients, get the Kronrod vectors alpha
        # and beta, and hand those off to scheme_from_rc. There, the
        # eigenproblem for a tridiagonal matrix with alpha and beta is solved
        # to retrieve the points and weights.
        # TODO replace math.ceil by -(-k//n)
        length = int(math.ceil(3 * n / 2.0)) + 1
        self.degree = 2 * length + 1
        _, _, alpha, beta = jacobi(
            length, a, b, "monic"
        )
        flt = numpy.vectorize(float)
        alpha = flt(alpha)
        beta = flt(beta)
        a, b = self.r_kronrod(n, alpha, beta)
        x, w = scheme_from_rc(a, b, mode="numpy")
        # sort by x
        i = numpy.argsort(x)
        self.points = x[i]
        self.weights = w[i]
        return

    def r_kronrod(self, n, a0, b0):
        assert len(a0) == int(math.ceil(3 * n / 2.0)) + 1
        assert len(b0) == int(math.ceil(3 * n / 2.0)) + 1

        a = numpy.zeros(2 * n + 1)
        b = numpy.zeros(2 * n + 1)

        k = int(math.floor(3 * n / 2.0)) + 1
        a[:k] = a0[:k]
        k = int(math.ceil(3 * n / 2.0)) + 1
        b[:k] = b0[:k]
        s = numpy.zeros(int(math.floor(n / 2.0)) + 2)
        t = numpy.zeros(int(math.floor(n / 2.0)) + 2)
        t[1] = b[n + 1]
        for m in range(n - 1):
            k0 = int(math.floor((m + 1) / 2.0))
            k = numpy.arange(k0, -1, -1)
            L = m - k
            s[k + 1] = numpy.cumsum(
                (a[k + n + 1] - a[L]) * t[k + 1] + b[k + n + 1] * s[k] - b[L] * s[k + 1]
            )
            s, t = t, s

        j = int(math.floor(n / 2.0)) + 1
        s[1: j + 1] = s[:j]
        for m in range(n - 1, 2 * n - 2):
            k0 = m + 1 - n
            k1 = int(math.floor((m - 1) / 2.0))
            k = numpy.arange(k0, k1 + 1)
            L = m - k
            j = n - 1 - L
            s[j + 1] = numpy.cumsum(
                -(a[k + n + 1] - a[L]) * t[j + 1]
                - b[k + n + 1] * s[j + 1]
                + b[L] * s[j + 2]
            )
            j = j[-1]
            k = int(math.floor((m + 1) / 2.0))
            if m % 2 == 0:
                a[k + n + 1] = a[k] + (s[j + 1] - b[k + n + 1] * s[j + 2]) / t[j + 2]
            else:
                b[k + n + 1] = s[j + 1] / s[j + 2]
            s, t = t, s

        a[2 * n] = a[n - 1] - b[2 * n] * s[1] / t[1]
        return a, b


def _gauss_kronrod_integrate(k, f, interval, dot=numpy.dot):
    def _scale_points(points, interval):
        alpha = 0.5 * (interval[1] - interval[0])
        beta = 0.5 * (interval[0] + interval[1])
        return (numpy.multiply.outer(points, alpha) + beta).T

    def _integrate(values, weights, interval_length, dot):
        """Integration with point values explicitly specified.
        """
        return 0.5 * interval_length * dot(values, weights)

    # Compute the integral estimations according to Gauss and Gauss-Kronrod,
    # sharing the function evaluations
    scheme = GaussKronrod(k)
    gauss_weights = GaussLegendre(k).weights
    sp = _scale_points(scheme.points, interval)
    point_vals_gk = f(sp)
    assert point_vals_gk.shape[-len(sp.shape):] == sp.shape, (
        "Function evaluation returned numpy array of wrong shape. "
        "(Input shape: {}, expected output shape: (..., {}), got: {})".format(
            sp.shape, ", ".join(str(k) for k in sp.shape), point_vals_gk.shape
        )
    )
    point_vals_g = point_vals_gk[..., 1::2]
    alpha = abs(interval[1] - interval[0])
    val_gauss_kronrod = _integrate(point_vals_gk, scheme.weights, alpha, dot=dot)
    val_gauss = _integrate(point_vals_g, gauss_weights, alpha, dot=dot)

    # Get an error estimate. According to
    #
    #   A Review of Error Estimation in Adaptive Quadrature
    #   Pedro Gonnet,
    #   ACM Computing Surveys (CSUR) Surveys,
    #   Volume 44, Issue 4, August 2012
    #   <https://doi.org/10.1145/2333112.2333117>,
    #   <https://arxiv.org/pdf/1003.4629.pdf>
    #
    # the classicial QUADPACK still compares favorably with other approaches.
    average = val_gauss_kronrod / alpha
    point_vals_abs = abs(point_vals_gk - average[..., None])
    I_tilde = _integrate(point_vals_abs, scheme.weights, alpha, dot=dot)
    # The exponent 1.5 is chosen such that (200*x)**1.5 is approximately x at
    # 1.0e-6, the machine precision on IEEE 754 32-bit floating point
    # arithmentic. This could be adapted to
    #
    #   eps = numpy.finfo(float).eps
    #   exponent = numpy.log(eps) / numpy.log(200*eps)
    #
    error_estimate = I_tilde * numpy.minimum(
        numpy.ones(I_tilde.shape),
        (200 * abs(val_gauss_kronrod - val_gauss) / I_tilde) ** 1.5,
    )
    return val_gauss_kronrod, val_gauss, error_estimate

# from tools

"""
[1] Gene H. Golub and John H. Welsch,
    Calculation of Gauss Quadrature Rules,
    Mathematics of Computation,
    Vol. 23, No. 106 (Apr., 1969), pp. 221-230+s1-s10,
    <https://dx.doi.org/10.2307/2004418>,
    <https://pdfs.semanticscholar.org/c715/119d5464f614fd8ec590b732ccfea53e72c4.pdf>.

[2] W. Gautschi,
    Algorithm 726: ORTHPOL–a package of routines for generating orthogonal
    polynomials and Gauss-type quadrature rules,
    ACM Transactions on Mathematical Software (TOMS),
    Volume 20, Issue 1, March 1994,
    Pages 21-62,
    <http://doi.org/10.1145/174603.174605>,
    <http://www.cs.purdue.edu/archives/2002/wxg/codes/gauss.m>,

[3] W. Gautschi,
    How and how not to check Gaussian quadrature formulae,
    BIT Numerical Mathematics,
    June 1983, Volume 23, Issue 2, pp 209–216,
    <https://doi.org/10.1007/BF02218441>.

[4] D. Boley and G.H. Golub,
    A survey of matrix inverse eigenvalue problems,
    Inverse Problems, 1987, Volume 3, Number 4,
    <https://doi.org/10.1088/0266-5611/3/4/010>.
"""


def golub_welsch(moments):
    """Given moments

    mu_k = int_a^b omega(x) x^k dx,  k = {0, 1,...,2N}

    (with omega being a nonnegative weight function), this method creates the
    recurrence coefficients of the corresponding orthogonal polynomials, see
    section 4 ("Determining the Three Term Relationship from the Moments") in
    Golub-Welsch [1]. Numerically unstable, see [2].
    """
    assert len(moments) % 2 == 1
    n = (len(moments) - 1) // 2

    M = numpy.array([[moments[i + j] for j in range(n + 1)] for i in range(n + 1)])
    R = numpy.linalg.cholesky(M).T

    # (upper) diagonal
    Rd = R.diagonal()
    q = R.diagonal(1) / Rd[:-1]

    alpha = q.copy()
    alpha[+1:] -= q[:-1]

    # TODO don't square here, but adapt _gauss to accept square-rooted values
    #      as input
    beta = numpy.hstack([Rd[0], Rd[1:-1] / Rd[:-2]]) ** 2
    return alpha, beta


def stieltjes(w, a, b, n):
    t = sympy.Symbol("t")

    alpha = n * [None]
    beta = n * [None]
    mu = n * [None]
    pi = n * [None]

    k = 0
    pi[k] = 1
    mu[k] = sympy.integrate(pi[k] ** 2 * w(t), (t, a, b))
    alpha[k] = sympy.integrate(t * pi[k] ** 2 * w(t), (t, a, b)) / mu[k]
    beta[k] = mu[0]  # not used, by convection mu[0]

    k = 1
    pi[k] = (t - alpha[k - 1]) * pi[k - 1]
    mu[k] = sympy.integrate(pi[k] ** 2 * w(t), (t, a, b))
    alpha[k] = sympy.integrate(t * pi[k] ** 2 * w(t), (t, a, b)) / mu[k]
    beta[k] = mu[k] / mu[k - 1]

    for k in range(2, n):
        pi[k] = (t - alpha[k - 1]) * pi[k - 1] - beta[k - 1] * pi[k - 2]
        mu[k] = sympy.integrate(pi[k] ** 2 * w(t), (t, a, b))
        alpha[k] = sympy.integrate(t * pi[k] ** 2 * w(t), (t, a, b)) / mu[k]
        beta[k] = mu[k] / mu[k - 1]

    return alpha, beta


def chebyshev(moments):
    """Given the first 2n moments `int t^k dt`, this method uses the Chebyshev
    algorithm (see, e.g., [2]) for computing the associated recurrence
    coefficients.

    WARNING: Ill-conditioned, see [2].
    """
    m = len(moments)
    assert m % 2 == 0
    if isinstance(moments[0], tuple(sympy.core.all_classes)):
        dtype = sympy.Rational
    else:
        dtype = moments.dtype
    zeros = numpy.zeros(m, dtype=dtype)
    return chebyshev_modified(moments, zeros, zeros)


def chebyshev_modified(nu, a, b):
    """Given the first 2n modified moments `nu_k = int p_k(t) dt`, where the
    p_k are orthogonal polynomials with recurrence coefficients a, b, this
    method implements the modified Chebyshev algorithm (see, e.g., [2]) for
    computing the associated recurrence coefficients.
    """
    m = len(nu)
    assert m % 2 == 0

    n = m // 2

    alpha = numpy.empty(n, dtype=a.dtype)
    beta = numpy.empty(n, dtype=a.dtype)
    # Actually overkill. One could alternatively make sigma a list, and store
    # the shrinking rows there, only ever keeping the last two.
    sigma = numpy.empty((n, 2 * n), dtype=a.dtype)

    if n > 0:
        k = 0
        sigma[k, k: 2 * n - k] = nu
        alpha[0] = a[0] + nu[1] / nu[0]
        beta[0] = nu[0]

    if n > 1:
        k = 1
        L = numpy.arange(k, 2 * n - k)
        sigma[k, L] = (
            sigma[k - 1, L + 1]
            - (alpha[k - 1] - a[L]) * sigma[k - 1, L]
            + b[L] * sigma[k - 1, L - 1]
        )
        alpha[k] = (
            a[k] + sigma[k, k + 1] / sigma[k, k] - sigma[k - 1, k] / sigma[k - 1, k - 1]
        )
        beta[k] = sigma[k, k] / sigma[k - 1, k - 1]

    for k in range(2, n):
        L = numpy.arange(k, 2 * n - k)
        sigma[k, L] = (
            sigma[k - 1, L + 1]
            - (alpha[k - 1] - a[L]) * sigma[k - 1, L]
            - beta[k - 1] * sigma[k - 2, L]
            + b[L] * sigma[k - 1, L - 1]
        )
        alpha[k] = (
            a[k] + sigma[k, k + 1] / sigma[k, k] - sigma[k - 1, k] / sigma[k - 1, k - 1]
        )
        beta[k] = sigma[k, k] / sigma[k - 1, k - 1]

    return alpha, beta


def integrate(f, a, b):
    """Symbolically calculate the integrals

      int_a^b f_k(x) dx.

    Useful for computing the moments `w(x) * P_k(x)`, e.g.,

    moments = quadpy.tools.integrate(
            lambda x: [x**k for k in range(5)],
            -1, +1
            )
    """
    x = sympy.Symbol("x")
    return numpy.array([sympy.integrate(fun, (x, a, b)) for fun in f(x)])


def coefficients_from_gauss(points, weights):
    """Given the points and weights of a Gaussian quadrature rule, this method
    reconstructs the recurrence coefficients alpha, beta as appearing in the
    tridiagonal Jacobi matrix tri(b, a, b).
    This is using "Method 2--orthogonal reduction" from (section 3.2 in [4]).
    The complexity is O(n^3); a faster method is suggested in 3.3 in [4].
    """
    n = len(points)
    assert n == len(weights)

    flt = numpy.vectorize(float)
    points = flt(points)
    weights = flt(weights)

    A = numpy.zeros((n + 1, n + 1))

    # In sytrd, the _last_ row/column of Q are e, so put the values there.
    a00 = 1.0
    A[n, n] = a00
    k = numpy.arange(n)
    A[k, k] = points
    A[n, :-1] = numpy.sqrt(weights)
    A[:-1, n] = numpy.sqrt(weights)

    # Implemented in
    # <https://github.com/scipy/scipy/issues/7775>
    sytrd, sytrd_lwork = get_lapack_funcs(("sytrd", "sytrd_lwork"))

    # query lwork (optional)
    lwork, info = sytrd_lwork(n + 1)
    assert info == 0

    _, d, e, _, info = sytrd(A, lwork=lwork)
    assert info == 0

    return d[:-1][::-1], e[::-1] ** 2


def check_coefficients(moments, alpha, beta):
    """In his article [3], Walter Gautschi suggests a method for checking if a
    Gauss quadrature rule is sane. This method implements test #3 for the
    article.
    """
    n = len(alpha)
    assert len(beta) == n

    D = numpy.empty(n + 1)
    Dp = numpy.empty(n + 1)
    D[0] = 1.0
    D[1] = moments[0]
    Dp[0] = 0.0
    Dp[1] = moments[1]
    for k in range(2, n + 1):
        A = numpy.array([moments[i: i + k] for i in range(k)])
        D[k] = numpy.linalg.det(A)
        #
        A[:, -1] = moments[k: 2 * k]
        Dp[k] = numpy.linalg.det(A)

    errors_alpha = numpy.zeros(n)
    errors_beta = numpy.zeros(n)

    errors_alpha[0] = abs(alpha[0] - (Dp[1] / D[1] - Dp[0] / D[0]))
    errors_beta[0] = abs(beta[0] - D[1])
    for k in range(1, n):
        errors_alpha[k] = abs(alpha[k] - (Dp[k + 1] / D[k + 1] - Dp[k] / D[k]))
        errors_beta[k] = abs(beta[k] - D[k + 1] * D[k - 1] / D[k] ** 2)

    return errors_alpha, errors_beta


def scheme_from_rc(alpha, beta, mode="mpmath", decimal_places=32):
    """Compute the Gauss nodes and weights from the recurrence coefficients
    associated with a set of orthogonal polynomials. See [2] and
    <http://www.scientificpython.net/pyblog/radau-quadrature>.
    """
    return {
        "sympy": lambda: _gauss_from_coefficients_sympy(alpha, beta),
        "mpmath": lambda: _gauss_from_coefficients_mpmath(alpha, beta, decimal_places),
        "numpy": lambda: _gauss_from_coefficients_numpy(alpha, beta),
    }[mode]()


def _sympy_tridiag(a, b):
    """Creates the tridiagonal sympy matrix tridiag(b, a, b).
    """
    n = len(a)
    assert n == len(b)
    A = [[0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        A[i][i] = a[i]
    for i in range(n - 1):
        A[i][i + 1] = b[i + 1]
        A[i + 1][i] = b[i + 1]
    return sympy.Matrix(A)


def _gauss_from_coefficients_sympy(alpha, beta):
    # Construct the triadiagonal matrix [sqrt(beta), alpha, sqrt(beta)]
    A = _sympy_tridiag(alpha, [sympy.sqrt(bta) for bta in beta])

    # Extract points and weights from eigenproblem
    x = []
    w = []
    for item in A.eigenvects():
        val, multiplicity, vec = item
        assert multiplicity == 1
        assert len(vec) == 1
        vec = vec[0]
        x.append(val)
        norm2 = sum([v ** 2 for v in vec])
        # simplifiction takes really long
        # w.append(sympy.simplify(beta[0] * vec[0]**2 / norm2))
        w.append(beta[0] * vec[0] ** 2 / norm2)
    # sort by x
    order = sorted(range(len(x)), key=lambda i: x[i])
    x = [x[i] for i in order]
    w = [w[i] for i in order]
    return x, w


def _gauss_from_coefficients_mpmath(alpha, beta, decimal_places):
    mp.dps = decimal_places

    # Create vector cut of the first value of beta
    n = len(alpha)
    b = mp.zeros(n, 1)
    for i in range(n - 1):
        # work around <https://github.com/fredrik-johansson/mpmath/issues/382>
        x = beta[i + 1]
        if isinstance(x, numpy.int64):
            x = int(x)
        b[i] = mp.sqrt(x)

    z = mp.zeros(1, n)
    z[0, 0] = 1
    d = mp.matrix(alpha)
    tridiag_eigen(mp, d, b, z)

    # nx1 matrix -> list of mpf
    x = numpy.array([mp.mpf(sympy.N(xx, decimal_places)) for xx in d])
    w = numpy.array(
        [mp.mpf(sympy.N(beta[0], decimal_places)) * mp.power(ww, 2) for ww in z]
    )
    return x, w


def _gauss_from_coefficients_numpy(alpha, beta):
    # assert isinstance(alpha, numpy.ndarray)
    # assert isinstance(beta, numpy.ndarray)
    alpha = alpha.astype(numpy.float64)
    beta = beta.astype(numpy.float64)

    x, V = eig_banded(numpy.vstack((numpy.sqrt(beta), alpha)), lower=False)
    w = beta[0] * numpy.real(numpy.lib.scimath.power(V[0, :], 2))
    # eigh_tridiagonal is only available from scipy 1.0.0, and has problems
    # with precision. TODO find out how/why/what
    # try:
    #     from scipy.linalg import eigh_tridiagonal
    # except ImportError:
    #     # Use eig_banded
    #     x, V = \
    #         eig_banded(numpy.vstack((numpy.sqrt(beta), alpha)), lower=False)
    #     w = beta[0]*scipy.real(scipy.power(V[0, :], 2))
    # else:
    #     x, V = eigh_tridiagonal(alpha, numpy.sqrt(beta[1:]))
    #     w = beta[0] * V[0, :]**2

    return x, w


# from orthopy

def legendre(n, standardization, symbolic=False):
    return jacobi(n, 0, 0, standardization, symbolic=symbolic)


def jacobi(n, alpha, beta, standardization, symbolic=False):
    """Generate the recurrence coefficients a_k, b_k, c_k in

    P_{k+1}(x) = (a_k x - b_k)*P_{k}(x) - c_k P_{k-1}(x)

    for the Jacobi polynomials which are orthogonal on [-1, 1]
    with respect to the weight w(x)=[(1-x)^alpha]*[(1+x)^beta]; see
    <https://en.wikipedia.org/wiki/Jacobi_polynomials#Recurrence_relations>.
    """
    gamma = sympy.gamma if symbolic else lambda x: scipy.special.gamma(float(x))

    def rational(x, y):
        # <https://github.com/sympy/sympy/pull/13670>
        return (
            sympy.Rational(x, y)
            if all([isinstance(val, int) for val in [x, y]])
            else x / y
        )

    frac = rational if symbolic else lambda x, y: x / y
    sqrt = sympy.sqrt if symbolic else numpy.sqrt

    int_1 = (
        2 ** (alpha + beta + 1)
        * gamma(alpha + 1)
        * gamma(beta + 1)
        / gamma(alpha + beta + 2)
    )

    if standardization == "monic":
        p0 = 1

        a = numpy.ones(n, dtype=int)

        # work around bug <https://github.com/sympy/sympy/issues/13618>
        if isinstance(alpha, numpy.int64):
            alpha = int(alpha)
        if isinstance(beta, numpy.int64):
            beta = int(beta)

        b = [
            frac(beta - alpha, alpha + beta + 2)
            if N == 0
            else frac(
                beta ** 2 - alpha ** 2,
                (2 * N + alpha + beta) * (2 * N + alpha + beta + 2),
            )
            for N in range(n)
        ]

        # c[0] is not used in the actual recurrence, but is often defined
        # as the integral of the weight function of the domain, i.e.,
        # ```
        # int_{-1}^{+1} (1-x)^a * (1+x)^b dx =
        #     2^(a+b+1) * Gamma(a+1) * Gamma(b+1) / Gamma(a+b+2).
        # ```
        # Note also that we have the treat the case N==1 separately to avoid
        # division by 0 for alpha=beta=-1/2.
        c = [
            int_1
            if N == 0
            else frac(
                4 * (1 + alpha) * (1 + beta),
                (2 + alpha + beta) ** 2 * (3 + alpha + beta),
            )
            if N == 1
            else frac(
                4 * (N + alpha) * (N + beta) * N * (N + alpha + beta),
                (2 * N + alpha + beta) ** 2
                * (2 * N + alpha + beta + 1)
                * (2 * N + alpha + beta - 1),
            )
            for N in range(n)
        ]

    elif standardization == "p(1)=(n+alpha over n)" or (
        alpha == 0 and standardization == "p(1)=1"
    ):
        p0 = 1

        # work around bug <https://github.com/sympy/sympy/issues/13618>
        if isinstance(alpha, numpy.int64):
            alpha = int(alpha)
        if isinstance(beta, numpy.int64):
            beta = int(beta)

        # Treat N==0 separately to avoid division by 0 for alpha=beta=-1/2.
        a = [
            frac(alpha + beta + 2, 2)
            if N == 0
            else frac(
                (2 * N + alpha + beta + 1) * (2 * N + alpha + beta + 2),
                2 * (N + 1) * (N + alpha + beta + 1),
            )
            for N in range(n)
        ]

        b = [
            frac(beta - alpha, 2)
            if N == 0
            else frac(
                (beta ** 2 - alpha ** 2) * (2 * N + alpha + beta + 1),
                2 * (N + 1) * (N + alpha + beta + 1) * (2 * N + alpha + beta),
            )
            for N in range(n)
        ]

        c = [
            int_1
            if N == 0
            else frac(
                (N + alpha) * (N + beta) * (2 * N + alpha + beta + 2),
                (N + 1) * (N + alpha + beta + 1) * (2 * N + alpha + beta),
            )
            for N in range(n)
        ]

    else:
        assert standardization == "normal", "Unknown standardization '{}'.".format(
            standardization
        )

        p0 = sqrt(1 / int_1)

        # Treat N==0 separately to avoid division by 0 for alpha=beta=-1/2.
        a = [
            frac(alpha + beta + 2, 2)
            * sqrt(frac(alpha + beta + 3, (alpha + 1) * (beta + 1)))
            if N == 0
            else frac(2 * N + alpha + beta + 2, 2)
            * sqrt(
                frac(
                    (2 * N + alpha + beta + 1) * (2 * N + alpha + beta + 3),
                    (N + 1) * (N + alpha + 1) * (N + beta + 1) * (N + alpha + beta + 1),
                )
            )
            for N in range(n)
        ]

        b = [
            (
                frac(beta - alpha, 2)
                if N == 0
                else frac(beta ** 2 - alpha ** 2, 2 * (2 * N + alpha + beta))
            )
            * sqrt(
                frac(
                    (2 * N + alpha + beta + 3) * (2 * N + alpha + beta + 1),
                    (N + 1) * (N + alpha + 1) * (N + beta + 1) * (N + alpha + beta + 1),
                )
            )
            for N in range(n)
        ]

        c = [
            int_1
            if N == 0
            else frac(4 + alpha + beta, 2 + alpha + beta)
            * sqrt(
                frac(
                    (1 + alpha) * (1 + beta) * (5 + alpha + beta),
                    2 * (2 + alpha) * (2 + beta) * (2 + alpha + beta),
                )
            )
            if N == 1
            else frac(2 * N + alpha + beta + 2, 2 * N + alpha + beta)
            * sqrt(
                frac(
                    N
                    * (N + alpha)
                    * (N + beta)
                    * (N + alpha + beta)
                    * (2 * N + alpha + beta + 3),
                    (N + 1)
                    * (N + alpha + 1)
                    * (N + beta + 1)
                    * (N + alpha + beta + 1)
                    * (2 * N + alpha + beta - 1),
                )
            )
            for N in range(n)
        ]

    return p0, numpy.array(a), numpy.array(b), numpy.array(c)
