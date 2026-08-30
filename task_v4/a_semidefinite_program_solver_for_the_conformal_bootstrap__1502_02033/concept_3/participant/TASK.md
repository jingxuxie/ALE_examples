# Compact exact positivity certificates

Produce independently checkable positivity certificates for the polynomial
matrix blocks in `input/instances.json`. These blocks model the boundary and
scale disparities encountered in polynomial-matrix semidefinite programs.

For every supplied symmetric rational matrix polynomial P(x), construct
rational rectangular polynomial matrices A(x), B(x) satisfying exactly

    P(x) = A(x)^T A(x) + x B(x)^T B(x).

This identity certifies P(x) is positive semidefinite for every x >= 0. Respect
each block's supplied degree and row limits. All blocks admit certificates
within those limits; approximate identities do not count as certificates.

Write `certificate.json` into your output directory using `input/FORMAT.md`.
The supplied `baseline/solve.py INPUT_JSON OUTPUT_JSON` is runnable but is not
an exact solver. `workspace/check.py INPUT_JSON CERTIFICATE_JSON` checks your
artifact locally. You may use Python, NumPy, SciPy, SymPy, mpmath and system
compilers; network access and additional packages are unavailable.

You have one hour. The final JSON must be at most 8 MiB, and every rational
numerator and denominator must have at most 2048 bits. Success requires exact
certificates for every block. Partial scoring reports certified blocks and
coefficient residuals; there is no tolerance in the success condition.
