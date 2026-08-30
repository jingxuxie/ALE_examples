# Model and certificate

There are sixteen sites `(x,y)` with `x,y=0,1,2,3`, indexed `4*x+y`.
The kinetic matrix `K` has entry `-hopping` between distinct nearest neighbors
on this periodic square torus, zero otherwise, including on its diagonal. Each
undirected bond occurs once; the matrix is symmetric. The physical interaction
is `U*(n_up-1/2)*(n_down-1/2)` and the chemical potential is measured from half filling.

For each certification point take `beta_point = beta*beta_multiplier` and
`mu_point = chemical_potential+chemical_shift`. Set
`dt = beta_point/time_slices` and `lambda = acosh(exp(dt*interaction/2))`.
For a spin label `sigma` in `{-1,+1}` and a time slice `ell`, define

```
B_sigma[ell] = expm(-dt*K/2)
              @ diag(exp(sigma*lambda*fields[ell,:] + dt*mu_point))
              @ expm(-dt*K/2)
P_sigma = B_sigma[15] @ ... @ B_sigma[0]
W = det(I + P_plus) * det(I + P_minus)
```

All omitted Hubbard-Stratonovich prefactors are strictly positive. The question
concerns this finite-time-step weight, not the zero-step-size limit. Each slice
matrix is symmetric positive definite; that alone does not certify the sign of
the full weight. The provisional claim being audited is `W >= 0` for every
legal field at this window, not an assertion attributed to any published paper.

`witness.json` is a JSON object with exactly one key, `fields`: a list of sixteen
lists of sixteen integer entries, each exactly `-1` or `1`. It must be at most
32768 bytes. No NaNs, booleans, executable data, variable parameters, or extra keys.

At each certification point the checker computes the two determinant signs and
`log(abs(W))` independently at 65 and 95 decimal digits, using high-precision
kinetic exponentials rather than promoting double-precision factors. A point
passes if both signs of `W` are negative and the two log weights agree within
`1e-25`. All three points must pass. The fields are identical across points.

Diagnostic interface: `python workspace/physics.py witness.json`.
Baseline interface: `python baseline/search.py --output OUTPUT/witness.json`.
The provided diagnostic does not replace the arbitrary-precision certification.
