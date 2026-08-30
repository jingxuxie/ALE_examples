# Model and executable contract

## Physics

There are three doubly occupied reference orbitals and eight virtual orbitals.
The simulator treats three electron pairs in the seniority-zero sector of a real
pair-conserving electronic Hamiltonian. In the occupation basis its diagonal is
`sum(orbital_energy[p]) + sum(density[p,q] for p<q)` over occupied pair sites.
Replacing an occupied site `p` with an empty site `q` has matrix element
`hopping[p,q]`. Both matrices are real symmetric with zero diagonals. This is a
genuine interacting paired-electron model, not a claim about Coulomb integrals.
The supplied `pair_model.py` fully specifies its six sampling families.
Hidden draws use independent seeds and random orbital parameters from the same
sampler. All have squared reference overlap at least 0.94 and excitation gap at
least 0.35 hartree. They are not merely permutations of practice draws.

A mask's bit `a` includes virtual orbital `a+3`. All three occupied reference
orbitals are always retained. `E(mask)` is the lowest restricted eigenvalue
minus the reference-determinant diagonal, in hartree. `E(0)=0`. The target is
`E(255)`. Full and seven-virtual queries are forbidden. Supplied low-order
energies, queries, and labels are computed to double precision, not noisy data.
The virtual-orbital many-body expansion is the subset Möbius decomposition of
this set function; its higher-order increments need not share a sign.

## Protocol

The evaluator launches one persistent process in `/submission`, containing your
read-only submission. The supplied participant directory is `/participant`;
`/participant/workspace` is on `PYTHONPATH`. `/tmp` is private and writable.
Only standard system software, your submission, and participant assets are
mounted. Hidden labels and models are in a different process and filesystem.

Each incoming/outgoing message occupies one line. Flush standard output after
every action; diagnostics belong on standard error. No extra stdout text.

The first message for each system is:

```
{"event":"start","nvirtual":8,"npairs":3,"family":"local",
 "orbital_energy":[...],"budget":160,
 "costs":{"3":1,"4":4,"5":16,"6":64},
 "values":[[0,0.0],[1,-0.001],...]}
```

`values` contains all masks of cardinality zero, one, and two. The diagonal
orbital energies and family are public; density and hopping are not.
An action is exactly one of these objects:

```
{"query":[7,11,13]}
{"estimate":-0.01015}
```

Query response:

```
{"event":"result","remaining":157,"values":[[7,...],[11,...],[13,...]]}
```

Repeated queries from earlier batches are free. Duplicate masks in a batch,
noninteger masks, queries of cardinality above six, budget overruns, nonfinite
estimates, or more than 200 actions per system invalidate the submission.
Three/four/five/six-virtual queries cost 1/4/16/64 units respectively. These are
fixed experiment-accounting units, not wall-clock estimates. The budget resets
for each system. An estimate is followed by `{"event":"accepted"}` and then
the next start message, or `{"event":"done"}` at the end. Exit zero on done.

Accuracy is RMSE in hartree, aggregated equally over systems; there are equally
many systems from each family. `core_score=max(0,1-RMSE/0.0001)` and
`worst_family_score=max(0,1-worst_RMSE/0.00025)`. Passing requires both scores at
least 0.9, with all protocol/resource constraints satisfied. Query resource score
is `1-mean_cost/320`; no amount of cost saving compensates for missed accuracy.

## Practice

From the participant directory:

```
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 workspace/practice.py --submission baseline
```

The 36 practice models, complete subset-energy tables, and spectral diagnostics
are in `input/`. They are training assets, not secret evaluation draws. Use the
same command with your output directory to exercise the protocol. `sample_model`
and `CASOracle` can generate more model-system training experiments. The baseline
is a functional policy, not a required architecture. Pretraining is permitted;
only the final evaluation process is subject to the evaluation-time resource cap.
