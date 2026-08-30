# Validation

All computations use the provided finite Hamiltonian and installed CPU NumPy
and SciPy libraries. Synthetic checks are generated from the advertised
parameter ranges; they are not the hidden evaluation suite.

## Public examples

The supplied contractor validates all three output files, including exact
archive keys, physical dimensions, bond caps, and requested parity.

| Request | Energy | Parity | Maximum bond |
| --- | ---: | ---: | ---: |
| symmetric | 5.803594485324917 | 1 | 6 |
| odd | -10.430790240115645 | -1 | 6 |
| nonuniform | 0.966726586929012 | 0.001306618370841 | 8 |

The corresponding output artifacts are `example_symmetric.npz`,
`example_odd.npz`, and `example_nonuniform.npz`.

## Exact small-chain cross-check

`experiments/exact_check.py` independently assembles the full four-site,
four-level Hamiltonian. At an unrestricted bond cap, the optimized even, odd,
and field-perturbed unrestricted energies agree with dense diagonalization to
less than 5e-15 absolute error. The test also verifies each requested parity.

## Larger chains and deadlines

Eight synthetic chains cover symmetric, odd-sector, crossover, deep-well,
inhomogeneous, and weak-link cases, up to 22 sites, local dimension 14, and bond
cap 12. Independent cold-start processes are checked at both six- and
forty-second CPU limits with a 2 GiB address-space limit.

All sixteen outputs validate. Detailed energy, timing, and resident-memory
records are in `experiments/final_cold6.log` and
`experiments/final_cold40.log`, with an aggregate in
`experiments/final_results.json`. Maximum measured CPU times are 5.68 seconds
for short requests and 6.20 seconds for long requests. Peak resident memory is
below 60 MiB. The short and long energies differ by at most 4.78e-10 on these
eight chains. An additional deliberately shortened one-second
request returns a valid odd-sector MPS, demonstrating a safe mid-sweep exit.

Additional checks exercise odd physical dimensions and odd bond caps. A
sixteen-case randomized comparison between three and up to eight two-site
sweeps, each followed by one-site convergence, agrees within 5e-13 in energy;
see `experiments/sweep_check.json`.

## Initialization regression

A generated two-well chain separated by a positive-mass barrier and weak link
has oppositely directed fields on its two halves. Initialization using only
uniform branches becomes trapped at energy -36.416491600346. Including the
dynamic-program-selected sign domain reaches -36.593102843214 at the same bond
cap. Separate zero-field unrestricted checks verify that the solver can lower
the energy by using symmetry-broken states when a balanced cat state consumes
too much of the allowed bond dimension.

## Scope

These checks establish implementation consistency, output validity, numerical
convergence on the tested instances, and measured resource compliance. They
are not an exact-ground-state certificate for the larger chains, and they do
not determine the unavailable hidden-suite score.
