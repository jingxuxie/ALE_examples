# File and CLI schema

## Hamiltonian and targets

For `L = n_sites`, `m = L/2`, use

`H = -sum_{i<j,spin} t_ij(c†_i c_j+c†_j c_i) + sum_i U_i n_i↑ n_i↓ + sum_i v_i(n_i↑+n_i↓)`.

The interaction is unshifted: no `(n_up-1/2)(n_down-1/2)` convention, no magnetic
field and no extra factor of two per edge. All energies use `t0=1`.
`E(a,b)` is the **lowest energy** in the sector `N_up=a, N_down=b`.

- `charge_gap = E(m+1,m) + E(m,m-1) - 2 E(m,m)`.
- `spin_gap = E(m+1,m-1) - E(m,m)`.

The spin output is a **fixed-Sz energy difference**, not a certified
singlet-to-triplet gap. It can vanish for a higher-spin ground multiplet;
the benchmark does not certify S². Energies and signed differences are neither
rounded nor clipped, including small negative numerical differences. These
finite-size observables do not assert a thermodynamic phase or bulk gap.

## Arrays and requests

All NPZ arrays are numeric and loadable with `numpy.load(..., allow_pickle=False)`.
For a batch of `B` rows:

| Key | Shape | dtype | Meaning |
|---|---|---|---|
| `hopping` | `(B,10,10)` | float64 | symmetric positive edge amplitudes; zero diagonal |
| `interaction` | `(B,10)` | float64 | repulsive unshifted onsite `U_i` |
| `potential` | `(B,10)` | float64 | mean-zero onsite energy `v_i` |
| `n_sites` | `(B,)` | int64 | 8 or 10; active prefix only |
| `family` | `(B,)` | int64 | physical family 0, 1, 2, or 3 |
| `gaps` | `(B,2)` | float64 | **labelled public archives only**: charge, then spin |

All inactive entries are zero. Never treat padding as noninteracting orbitals.
The family is physical metadata, not a per-instance ID. No eigenvalues, RDMs,
energies, latent random parameters, seeds or gap-correlated identifiers are supplied.

Request JSON has exactly these four fields:

```json
{"schema_version":1,"inputs":"/absolute/path/to/inputs.npz","n_instances":256,"target_order":["charge_gap","spin_gap"]}
```

The CLI is `python3 solver.py REQUEST_JSON PREDICTIONS_JSON`. The evaluator sets
the current directory to the submission and passes absolute request/output paths.
`make_request.py` writes an absolute input path. The static `example_request.json`
instead uses a participant-directory-relative path for a four-row example.

Output JSON must have exactly `schema_version` (integer 1) and `predictions`:

```json
{"schema_version":1,"predictions":[[1.2,0.3],[2.1,0.15]]}
```

This two-row illustration is syntax, not scientific reference data. Real output
has one two-number list per input row. JSON integers and floats are accepted;
booleans, strings, NaN/Infinity, duplicate keys, extra keys, missing rows, wrong
shapes, trailing data, and magnitudes exceeding `1e100` are invalid. File must be
regular, not a symlink/FIFO/hard link, and at most 131,072 bytes. Do not write NPZ
or pickle as predictions. Runtime exceptions/nonzero exit invalidate the batch.

The trusted evaluator shuffles the hidden batch before each invocation; ordering
has no scientific meaning and output must follow the received order. The batch
contains 64 instances per family. There are no interactive queries or callbacks.
