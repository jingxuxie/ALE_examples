# Connected fluctuations of three interval pairs

For ordered sites `a<b<c<d<e<f`, define `Q1=X_a X_b`, `Q2=X_c X_d`,
and `Q3=X_e X_f`, with Pauli eigenvalues plus/minus one. The observable is

```
K3 = <(Q1-<Q1>)(Q2-<Q2>)(Q3-<Q3>)>
   = <Q1 Q2 Q3> - <Q1 Q2><Q3> - <Q1 Q3><Q2>
                 - <Q2 Q3><Q1> + 2<Q1><Q2><Q3>.
```

This is the third joint cumulant of three pair-composite operators, not the
fully connected cumulant of six individual X operators. Every submitted mean
and lower moment in this literal subtraction comes from the submitted tensor.
The exact target uses only exact ground-state moments. Replacing submitted
means with exact means, or matching only the raw six-spin moment, is incorrect.

All 252 sextuples are listed in `three_interval_sextuples.json`. Their three
interval lengths belong to `{16,32,64,96}`, their two intervening gaps belong
to `{32,64,96,128}`, and their total span is at most 256. Each must have relative
error at most 0.1. Every exact target exceeds `1e-6`; the list is fixed and no
small-target cases are silently dropped. All other contract criteria remain
unchanged.

## Exact infinite-chain target

For any even ordered list of X-spin sites, let `A` be the union of integer
sites from each paired left endpoint plus one through its right endpoint,
inclusive, and let `B=A-1`. The exact raw moment is the determinant with entries
`1/[pi*(A_row-B_column-1/2)]`.

A cancellation-free expression for K3 is also available. Let `mi` be the
exact XX correlation for interval `i`. For two intervals set

```
Sij = sum_{u in A_i, v in A_j} -log1p(-1/[4(v-u)^2])
hij = expm1(Sij)
K3_exact = m1*m2*m3 * (h12*h13 + h12*h23 + h13*h23 + h12*h13*h23).
```

The public helper `exact_three_interval_cumulant` evaluates this exact target.
The checker evaluates submitted raw moments with the full tensor and performs
the literal cumulant subtraction. Admissibility is checked on the submitted
tensor. Observable contractions use its actual positive left/right transfer
fixed points `L,R` and leading eigenvalue `lambda`: an n-site word has
expectation `trace(L E_O1 ... E_On(R))/(trace(L R)*lambda^n)`. Thus admitted
normalization or nonunitary-gauge defects do not masquerade as connected
fluctuations. The checker does not replace `R` by `I`, project away small
parity defects, or assume a Gaussian submitted state.
