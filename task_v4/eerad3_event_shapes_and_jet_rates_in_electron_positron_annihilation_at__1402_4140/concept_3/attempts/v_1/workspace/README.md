# Stable five-to-three antenna kernel

Build with the supplied `make` target. The external binary64 ABI and common
blocks are unchanged; no additional build inputs are required.

The null-vector product uses the received spatial components. For nearby
directions it evaluates the squared cross product divided by
`|a||b| + a.b`, with compensated two-product differences for small angles.
Power-of-two scaling avoids overflow without perturbing those directions.
`fillinv` reuses each particle's scaled vector and norm across its pairs.

The ordinary map is an algebraic reconstruction of the same positive-root
DAK2 solution, not a different clustering rule. Let `K` be the antenna sum,
`W = r1*u + r2*v` with the original DAK2 weights, and

```
h = (a/(K.a) - b/(K.b)) / sqrt(2*a.b / ((K.a)*(K.b)))
F = W + (K.K/2 - K.W)*b/(K.b)
C = F + (F.h)*h
A = C + sqrt(C.C)*h
B = K - A
```

Products in these equations are Minkowski products. Since `K.h = 0` and
`h.h = -1`, this imposes both null shells and conservation without subtracting
large radiator coefficients. Extended precision and reorthonormalization
handle nearly coincident radiator directions. For very light antennae,
binary128 evaluation of the original invariant formula avoids cancellation
in timelike norms. Its invariants are recomputed geometrically and normalized
by the antenna mass before evaluating the coefficients.

The spectator is copied verbatim. Mapped invariants are recomputed in output
slot order, and the three output momenta are copied to `p3`. Rotations use
scaled norms and preserve the upstream convention away from the poles.
