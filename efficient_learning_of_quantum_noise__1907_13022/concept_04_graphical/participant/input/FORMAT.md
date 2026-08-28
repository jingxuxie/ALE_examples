# NPZ contract, version 1

Run `python solver.py INPUT.npz OUTPUT.npz`. All arrays are numeric, and archives
must load with `allow_pickle=False`. No other files or network services are
available to a submission. NumPy and SciPy are installed. Write only the output
archive, with the exact path passed on the command line.

Each case runs in a fresh filesystem-restricted subprocess with 120 seconds of
wall time, a 120-second CPU budget, and 3 GiB of address space. Only the staged
submission, this case's input, a writable temporary directory and the Python
runtime are readable. The submission source must be at most 2 MiB; the output
must be at most 32 KiB. External processes and auxiliary submission files are
not needed. There is no access to private references or other cases.

## Model and local observations

There are `n` binary random variables, indexed `0,...,n-1`. A one denotes an
error in the supplied binary noise model, not a specified X/Y/Z Pauli label.
The strictly positive underlying distribution has the form

`p(x) = exp(sum_S theta[S] * product(x[v] for v in S)) / Z`.

Nonempty sets S have at most `max_order` elements. Neither the nonzero sets nor
their parameters are provided. The true interaction graph has treewidth at most
three. A generic sparse graph of bounded degree need not have this property;
this is an explicit promise of this task. Variable labels and local axis orders
are arbitrary, not a contraction order. Graphs can have cycles and irreducible
three-variable interactions. The local scopes are **observation envelopes**, not
factor scopes, and treating their marginal tables as independent factors is wrong.

| Key | dtype / shape | Meaning |
| --- | --- | --- |
| `version` | int64 scalar | 1 |
| `n` | int64 scalar | Number of variables, 8--120 |
| `max_order` | int64 scalar | 3 |
| `centers` | int64 `(n,)` | Each variable occurs once, in arbitrary row order |
| `scope_size` | int64 `(n,)` | Number of variables in each local table, at most 8 |
| `scope_nodes` | int64 `(n,8)` | Ordered variable IDs; unused entries are -1 |
| `local_ptr` | int64 `(n+1,)` | Offsets into `local_probs`, starting at zero |
| `local_probs` | float64 `(local_ptr[-1],)` | Concatenated normalized local distributions |

For row r, its scope contains `centers[r]` and a superset of that variable's
Markov neighbors: every nonzero interaction containing the center is fully
inside this scope. Additional variables are deliberate candidates, not known
neighbors. Candidates are symmetric across centers. Every table is the marginal
of the **same** underlying distribution at activity one. This pilot uses exact
synthetic marginals rounded to float64, not independent finite-shot histograms.
All entries are positive. No smoothing is necessary to fix missing observations.

Within a table, the first listed variable is the **least significant bit**:
entry `sum(2**j * x[scope_nodes[r,j]] for j in range(scope_size[r]))` is its
probability. Equivalently, reshape with `order='F'`. For scope `[7,2,5]`, index 5
means `x[7]=1, x[2]=0, x[5]=1`. A center need not occupy the first axis.
`local_ptr[r+1]-local_ptr[r]` equals `2**scope_size[r]`.

## Queries

For each row q, define the distribution

`p_q(x) = p(x) * exp(log_activity[q] * sum(x)) / E_p[exp(log_activity[q] * sum(x))]`.

The activity changes every variable's error fugacity, **not** just the variables
in the count mask. It is not a change to the local tables or a physical gate-time
parameter. The event is the intersection of the following constraints:

1. Every nonnegative entry in `fixed[q]` fixes the corresponding bit.
2. `weight_lo[q] <= sum(count_mask[q] * x) <= weight_hi[q]`, inclusive.
3. When `parity_value[q] != -1`, `sum(parity_mask[q] * x) % 2 == parity_value[q]`.

Fixed bits are part of the event, **not conditioning data**. Fixed ones still
count toward both the weight and parity constraints where their masks are one.
All unmentioned variables must be summed out, and the denominator is the global
normalizer at this query's activity, with no event constraints applied.

| Key | dtype / shape | Meaning |
| --- | --- | --- |
| `log_activity` | float64 `(Q,)` | Natural log of strictly positive activity, between -16 and 0 |
| `fixed` | int8 `(Q,n)` | -1 means free; otherwise 0 or 1 |
| `count_mask` | int8 `(Q,n)` | Binary mask of counted variables |
| `weight_lo`, `weight_hi` | int64 `(Q,)` | Inclusive weight bounds |
| `parity_mask` | int8 `(Q,n)` | Binary parity mask |
| `parity_value` | int8 `(Q,)` | -1 disables parity; otherwise 0 or 1 |
| `event_group` | int8 `(Q,)` | 0: weight event; 1: pinned burst; 2: weight/parity event |

There are at most 24 queries per case. Every requested event has positive
probability and excludes the all-zero pattern. Probabilities may be much smaller
than the smallest float64 number: return their finite logarithms, without flooring
probabilities. The example has fewer variables and queries, but the same semantics.

## Output and scoring

The output archive must contain exactly `log_event`, a float64 array of shape
`(Q,)`, with finite nonpositive natural-log event probabilities. No structural
labels, hidden factors, or reference answers are included in the input.

For query q the private reference is t, the independent-bit baseline is b, and
the prediction is a. The continuous query score is

`1 / (1 + 4 * abs(a-t) / (abs(b-t) + 0.1))`.

Thus an exact answer scores one, the weak baseline roughly 0.2, and improving
already accurate answers still improves the score; there is no tolerance plateau.
The baseline uses visible single-bit marginals and applies the same activity and
event definitions. Queries have equal weight within each event group; groups
have equal weight within each case. Cases have equal weight within each family,
and families have equal weight overall. Missing/malformed outputs, timeouts and
resource-limit failures score zero for that case. Reports include family and
case scores and subprocess wall time, but never reference arrays.
