# Model and executable contract

## Hidden domain

There are three occupied reference pair sites and eight virtual sites. Three
pairs occupy the seniority-zero sector of a real, pair-conserving effective
Hamiltonian. For a configuration of three occupied sites its diagonal is
`sum(orbital_energy[p]) + sum(density[p,q] for p<q)`. Moving one pair from occupied
site `p` to empty site `q` has matrix element `hopping[p,q]`. This specifies an
interacting model, not a claim about molecular Coulomb integrals.

All hidden models satisfy these bounds, in hartree:

| Quantity | Domain |
| --- | --- |
| Occupied site energies | `[-0.45, -0.22, 0.0]` exactly |
| Each virtual site energy | `[0.85, 2.4]` |
| Each off-diagonal hopping coefficient | `[-0.90, 0.90]` |
| Each off-diagonal density coefficient | `[-0.65, 0.65]` |
| Full ground-state squared reference overlap | at least `0.94` |
| Full first excitation gap | at least `0.35` |

Hopping and density are finite real symmetric 11-by-11 matrices with zero
diagonals. Site-energy, hopping, and density coefficients are otherwise governed
by this effective Hamiltonian; no additional Coulomb-integral constraints are
implied. These are rounded enclosing bounds, not hidden parameter values.

The fixed suite has 20 systems in each scoring stratum: `local`, `collective`,
`frustrated`, `bridge`, `density`, and `mixed`. It includes ordinary systems and
deliberately conditioned signed-cancellation systems. The suite is not IID,
and no hidden sampling probabilities or independence guarantees are promised.
Family names are scoring-stratum labels. The six-family `sample_model` routine
provides illustrative models; it is not an exhaustive hidden-domain generator
or a guarantee that hidden systems follow its sampling distribution. Practice
data are labeled examples, not a complete description of hidden coverage.

A mask's bit at position `orbital` includes virtual site `orbital+3`. All three
occupied reference sites remain present. `E(mask)` is the lowest restricted
eigenvalue minus the reference-determinant diagonal; `E(0)=0`. The target is
`E(255)`. Supplied and queried energies are in hartree and are computed in double
precision, not noisy measurements. Virtual labels have no guaranteed ordering.

## JSON-lines protocol

The evaluator starts one persistent process in read-only `/submission`.
Only system software, that submission, public `/participant`, a trusted resource
supervisor, and private writable `/tmp` are mounted. `/participant/workspace` is
on `PYTHONPATH`. Hidden labels, Hamiltonians, and prior artifacts are unavailable.
The network and process namespaces are isolated.

Each message occupies one line. Flush stdout after each action; send diagnostics
only to stderr. The first message for each system is:

```
{"event":"start","nvirtual":8,"npairs":3,"family":"local",
 "orbital_energy":[...],"budget":160,
 "costs":{"3":1,"4":4,"5":16,"6":64},
 "values":[[0,0.0],[1,-0.001],...]}
```

`values` contains all masks of cardinality zero, one, and two. Site energies and
the stratum are public observations; hopping and density are not. An action is
exactly one of:

```
{"query":[7,11,13]}
{"estimate":-0.01015}
```

The query response is:

```
{"event":"result","remaining":157,"values":[[7,...],[11,...],[13,...]]}
```

Three/four/five/six-virtual queries cost 1/4/16/64 units. Already observed masks
are free on subsequent requests within the same system. Duplicate masks within
one request, noninteger or Boolean masks, masks outside `[0,255]`, queries above
six virtuals, budget overruns, nonfinite estimates, malformed messages, or more
than 200 actions before an estimate invalidate the run. Query lists contain
between 1 and 160 masks. Messages must not exceed 1 MiB.

After an estimate the evaluator sends `{"event":"accepted"}`, then another
start message or `{"event":"done"}`. Exit zero on done. Query budgets reset per
system; the process and aggregate resource budgets do not.

## Objective and resources

Overall and within-stratum RMSE are calculated in hartree, weighting systems
equally. Passing requires overall RMSE at most `0.000010`, every stratum's RMSE at
most `0.000025`, and all protocol/resource constraints satisfied.
`core_score=max(0,1-RMSE/0.0001)` and
`worst_family_score=max(0,1-worst_RMSE/0.00025)`. Query resource score is
`1-mean_cost/320`; saving queries cannot compensate for missed accuracy.

For all 120 systems together: 120 seconds aggregate CPU, **600 seconds wall**,
2 GiB memory, and at most 128 MiB in the submission. CPU/RSS accounting includes
descendants under a trusted PID-1 supervisor. The 600-second wall allowance is
declared for this generation before launch to reduce shared-host scheduling
noise; it does not relax CPU, query, memory, or accuracy limits. No network.

## Public assets and practice

`input/` contains the original 36 practice models, complete 256-energy tables,
and spectral diagnostics. `baseline/solution.py` is the original weak baseline.
From the participant directory, exercise the interface with:

```
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 workspace/practice.py --submission baseline
```

The practice runner exercises the protocol on public data; it is not the
isolated, aggregate-resource-accounted hidden evaluator. Any final submission
must satisfy the complete hidden-run limits above.
