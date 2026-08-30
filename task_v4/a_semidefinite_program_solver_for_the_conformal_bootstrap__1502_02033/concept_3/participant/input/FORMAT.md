# JSON interface

`instances.json` contains `instances`, each with `id`, `dimension`,
`coefficients`, `a_rows`, `b_rows`, `a_degree`, and `b_degree`.
`coefficients[k][row][column]` is the coefficient of x**k in P(x).

Every rational number is a JSON string, either an integer (such as `"-3"`)
or a fraction with a positive denominator (such as `"5/17"`). Floating JSON
numbers, decimal strings, scientific notation, NaN and infinities are not
accepted. Coefficients are in ascending power order.

The certificate is `{"certificates": [{"id": "...", "A": [...], "B": [...]}]}`.
The IDs must match all input IDs exactly once. `A[k][row][column]` is a
coefficient of A(x), and likewise B. Supply exactly `a_degree+1` and
`b_degree+1` coefficient matrices, with exactly `a_rows` and `b_rows` rows,
respectively, and `dimension` columns. Zero-padding is allowed. This means
the actual degree and row rank may be lower than their limits. The row
bases and certificates are not unique; any rational identity is accepted.

For example, P(x) = [[1+x,0],[0,1+x]] allows A(x)=B(x)=I_2. Its certificate
has `A` and `B` each equal to `[[["1","0"],["0","1"]]]`.

The public checker validates exact coefficient convolution over the rational
numbers, not sampled positivity or agreement with a private factorization.
